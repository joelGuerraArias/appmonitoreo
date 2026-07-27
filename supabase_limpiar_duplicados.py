# -*- coding: utf-8 -*-
"""
Limpieza de duplicados en alertas_medios (Supabase).

Criterios (toda la tabla):
  1. Misma url_video o enlace_directo normalizada (si no vacía)
  2. Mismo (termino_detectado, nombre_archivo, medio)

Conserva el registro más reciente (mayor id) y elimina el resto.

Contador persistente: cada INTERVALO_LIMPIEZA inserciones exitosas dispara limpieza.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_DIR_SCRIPT = Path(__file__).parent.resolve()
_CARPETA_PROCESADOS = os.getenv(
    "CARPETA_PROCESADOS", str(_DIR_SCRIPT / "videos procesados")
)
SUPABASE_INSERT_COUNTER_JSON = os.path.join(
    _CARPETA_PROCESADOS, "supabase_insert_counter.json"
)
INTERVALO_LIMPIEZA = 5
PAGE_SIZE = 500

CAMPOS_SELECT = (
    "id,termino_detectado,nombre_archivo,nombre_medio,"
    "url_video,enlace_directo,fecha_detencion"
)

logger = logging.getLogger(__name__)


def _normalizar_url(url: str) -> str:
    """Normaliza URL para comparación (trim, sin fragmento, sin query opcional)."""
    if not url:
        return ""
    url = str(url).strip()
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # Conservar path; quitar query/fragment para agrupar variantes del mismo asset
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        return urlunparse((parsed.scheme.lower(), netloc, path, "", "", ""))
    except Exception:
        return url.strip().lower()


def _medio_registro(reg: dict) -> str:
    return (reg.get("nombre_medio") or reg.get("cliente") or "").strip()


def _clave_termino_archivo(reg: dict) -> tuple:
    return (
        (reg.get("termino_detectado") or "").strip().lower(),
        (reg.get("nombre_archivo") or "").strip(),
        _medio_registro(reg).lower(),
    )


def _keeper_id(grupo: list) -> int:
    """Id del registro más reciente del grupo."""
    def sort_key(r):
        rid = r.get("id")
        if rid is None:
            rid = 0
        fecha = r.get("fecha_detencion") or ""
        return (rid, fecha)

    return max(grupo, key=sort_key)["id"]


def _ids_duplicados_en_grupos(grupos: dict) -> set:
    """Para cada grupo con >1 fila, marca todos menos el keeper."""
    eliminar = set()
    for _clave, grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        keeper = _keeper_id(grupo)
        for reg in grupo:
            rid = reg.get("id")
            if rid is not None and rid != keeper:
                eliminar.add(rid)
    return eliminar


def _fetch_registros(sb_client, tabla: str) -> list:
    """Obtiene registros paginados ordenados por id."""
    rows = []
    offset = 0
    while True:
        res = (
            sb_client.table(tabla)
            .select(CAMPOS_SELECT)
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        chunk = res.data or []
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def _agrupar_duplicados(registros: list) -> tuple[set, int]:
    """
    Identifica ids a eliminar con dos pasadas de agrupación.
    Returns (ids_eliminar, num_grupos_duplicados).
    """
    grupos_url: dict = defaultdict(list)
    grupos_clave: dict = defaultdict(list)

    for reg in registros:
        url = _normalizar_url(reg.get("url_video") or "") or _normalizar_url(
            reg.get("enlace_directo") or ""
        )
        if url:
            grupos_url[url].append(reg)
        clave = _clave_termino_archivo(reg)
        if clave[0] and clave[1]:
            grupos_clave[clave].append(reg)

    ids_url = _ids_duplicados_en_grupos(grupos_url)
    ids_clave = _ids_duplicados_en_grupos(grupos_clave)
    ids_eliminar = ids_url | ids_clave

    grupos_dup = sum(1 for g in grupos_url.values() if len(g) > 1)
    grupos_dup += sum(1 for g in grupos_clave.values() if len(g) > 1)

    return ids_eliminar, grupos_dup


def limpiar_duplicados_alertas_medios(
    sb_client,
    tabla: str = "alertas_medios",
    dry_run: bool = False,
) -> dict:
    """
    Elimina duplicados en la tabla, conservando el registro más reciente por grupo.

    Returns:
        dict con keys: grupos, eliminados, ids_eliminados, dry_run, duracion_s
    """
    t0 = time.monotonic()
    registros = _fetch_registros(sb_client, tabla)
    ids_eliminar, grupos_dup = _agrupar_duplicados(registros)

    ids_list = sorted(ids_eliminar)
    eliminados = 0

    if not dry_run and ids_list:
        for rid in ids_list:
            try:
                sb_client.table(tabla).delete().eq("id", rid).execute()
                eliminados += 1
            except Exception as e:
                logger.warning("Error eliminando id=%s: %s", rid, e)

    duracion = time.monotonic() - t0
    resultado = {
        "grupos": grupos_dup,
        "eliminados": eliminados if not dry_run else len(ids_list),
        "ids_eliminados": ids_list if dry_run else ids_list[:eliminados],
        "dry_run": dry_run,
        "duracion_s": round(duracion, 2),
        "total_registros": len(registros),
    }

    if dry_run:
        logger.info(
            "Dry-run %s: %s duplicados en %s grupos (%s registros, %.2fs)",
            tabla,
            len(ids_list),
            grupos_dup,
            len(registros),
            duracion,
        )
    else:
        logger.info(
            "Limpieza %s: %s eliminados, %s grupos (%s registros, %.2fs)",
            tabla,
            eliminados,
            grupos_dup,
            len(registros),
            duracion,
        )
        if duracion > 2:
            logger.warning(
                "Limpieza Supabase tardó %.2fs (>2s)", duracion
            )

    return resultado


def _cargar_contador() -> dict:
    try:
        if os.path.isfile(SUPABASE_INSERT_COUNTER_JSON):
            with open(SUPABASE_INSERT_COUNTER_JSON, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("No se pudo leer contador Supabase: %s", e)
    return {"count": 0}


def _guardar_contador(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(SUPABASE_INSERT_COUNTER_JSON), exist_ok=True)
        with open(SUPABASE_INSERT_COUNTER_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("No se pudo guardar contador Supabase: %s", e)


def registrar_insercion_supabase_y_limpiar_si_toca(
    sb_client,
    tabla: str = "alertas_medios",
) -> dict:
    """
    Incrementa contador tras insert exitoso; cada INTERVALO_LIMPIEZA inserts ejecuta limpieza.

    Returns:
        {insert_count, cleanup_ran, eliminados, grupos, ...}
    """
    if sb_client is None:
        return {"insert_count": 0, "cleanup_ran": False, "eliminados": 0}

    data = _cargar_contador()
    data["count"] = int(data.get("count") or 0) + 1
    insert_count = data["count"]

    resultado = {
        "insert_count": insert_count,
        "cleanup_ran": False,
        "eliminados": 0,
        "grupos": 0,
    }

    if insert_count % INTERVALO_LIMPIEZA == 0:
        cleanup = limpiar_duplicados_alertas_medios(sb_client, tabla=tabla, dry_run=False)
        data["last_cleanup_at"] = datetime.now().isoformat()
        data["last_eliminados"] = cleanup.get("eliminados", 0)
        data["last_grupos"] = cleanup.get("grupos", 0)
        resultado.update(
            {
                "cleanup_ran": True,
                "eliminados": cleanup.get("eliminados", 0),
                "grupos": cleanup.get("grupos", 0),
                "ids_eliminados": cleanup.get("ids_eliminados", []),
                "duracion_s": cleanup.get("duracion_s", 0),
            }
        )

    _guardar_contador(data)
    return resultado


def crear_cliente_desde_env():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("Configura SUPABASE_URL y SUPABASE_ANON_KEY en .env")
    return create_client(url, key)


def main():
    parser = argparse.ArgumentParser(
        description="Elimina duplicados en alertas_medios (conserva el más reciente)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo reporta ids que se borrarían, sin eliminar.",
    )
    parser.add_argument(
        "--tabla",
        default="alertas_medios",
        help="Nombre de tabla Supabase (default: alertas_medios).",
    )
    args = parser.parse_args()

    sb = crear_cliente_desde_env()
    res = limpiar_duplicados_alertas_medios(
        sb, tabla=args.tabla, dry_run=args.dry_run
    )

    modo = "DRY-RUN" if args.dry_run else "EJECUCIÓN"
    print(f"\n[{modo}] Tabla: {args.tabla}")
    print(f"  Registros leídos: {res['total_registros']}")
    print(f"  Grupos duplicados: {res['grupos']}")
    print(f"  A eliminar: {res['eliminados']}")
    if res.get("ids_eliminados"):
        preview = res["ids_eliminados"][:20]
        print(f"  IDs: {preview}{'...' if len(res['ids_eliminados']) > 20 else ''}")
    print(f"  Duración: {res['duracion_s']}s")


if __name__ == "__main__":
    main()
