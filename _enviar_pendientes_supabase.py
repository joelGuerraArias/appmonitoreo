# -*- coding: utf-8 -*-
"""Envía a Supabase las coincidencias recientes parseadas desde Analisishoy_*.md."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

BASE = Path(__file__).resolve().parent
INFORMES = Path.home() / "Desktop" / "informes"
TABLA = "alertas_medios"

CLIENTE_POR_TERMINO = {
    "milton morrison": "Intrant",
    "morrison": "Intrant",
    "intrant": "Intrant",
    "apagones": "Sistema Principal (EDESUR)",
    "edenorte": "Sistema Principal (EDESUR)",
    "edesur": "Sistema Principal (EDESUR)",
    "punta catalina": "Sistema Principal (EDESUR)",
}


def _cliente_para(termino: str) -> str:
    t = (termino or "").strip().lower()
    for k, v in CLIENTE_POR_TERMINO.items():
        if k in t or t in k:
            return v
    return "Sistema Principal (EDESUR)"


def parsear_analisishoy(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    texto = ruta.read_text(encoding="utf-8")
    bloques = re.split(r"(?=# 📊 ANÁLISIS COMPLETO:)", texto)
    out: list[dict] = []
    for bloque in bloques:
        if "ANÁLISIS COMPLETO" not in bloque:
            continue
        m_arch = re.search(r"ANÁLISIS COMPLETO:\s*`([^`]+)`", bloque)
        m_fecha = re.search(r"Fecha de análisis:\*\*\s*([0-9\-: ]+)", bloque)
        m_medio = re.search(r"\*\*Medio:\*\*\s*(.+)", bloque)
        m_term = re.search(r"\*\*Término detectado:\*\*\s*\*\*([^*]+)\*\*", bloque)
        m_cloud = re.search(
            r"\*\*Video Cloudinary:\*\*\s*\[(https://res\.cloudinary\.com/[^\]]+)\]",
            bloque,
        )
        m_r2 = re.search(
            r"\*\*Video Cloudflare R2:\*\*\s*\[(https://[^\]]+)\]",
            bloque,
        )
        if not m_cloud:
            continue
        resumen = ""
        m_body = re.search(
            r"\*\*Video Cloudflare R2:\*\*.*?\n\n(.*?)\n\n---",
            bloque,
            re.DOTALL,
        )
        if m_body:
            resumen = m_body.group(1).strip()[:1000]
        termino = (m_term.group(1).strip() if m_term else "desconocido")
        archivo = m_arch.group(1).strip() if m_arch else ""
        fecha_analisis = (m_fecha.group(1).strip() if m_fecha else datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        medio_txt = (m_medio.group(1).strip() if m_medio else "")
        cliente = _cliente_para(termino)
        try:
            dt = datetime.strptime(fecha_analisis, "%Y-%m-%d %H:%M:%S")
            fecha_iso = dt.isoformat()
            fecha_prog = dt.date().isoformat()
            hora_prog = dt.time().isoformat()
        except ValueError:
            dt = datetime.now()
            fecha_iso = dt.isoformat()
            fecha_prog = dt.date().isoformat()
            hora_prog = dt.time().isoformat()
        out.append(
            {
                "termino_detectado": termino,
                "nombre_archivo": archivo,
                "contexto": (medio_txt + "\n\n" + resumen[:480]).strip()[:500] if resumen else medio_txt[:500],
                "resumen_ejecutivo": resumen[:1000] if resumen else f"Coincidencia {termino}",
                "fecha_detencion": fecha_iso,
                "fecha_programa": fecha_prog,
                "hora_programa": hora_prog,
                "url_video": m_cloud.group(1).strip(),
                "enlace_directo": (m_r2.group(1).strip() if m_r2 else m_cloud.group(1).strip()),
                "nombre_medio": cliente,
                "transcripcion": resumen[:2000] if resumen else "",
                "relevancia": "Alta",
            }
        )
    return out


def main():
    load_dotenv(BASE / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise SystemExit("Faltan SUPABASE_URL / SUPABASE_ANON_KEY en .env")

    sb = create_client(url, key)

    rutas = sorted(INFORMES.glob("Analisishoy_202607*.md"), reverse=True)
    if not rutas:
        rutas = sorted((BASE / "videos procesados").glob("Analisishoy_202607*.md"), reverse=True)
    if not rutas:
        raise SystemExit("No hay Analisishoy_202607*.md")

    items: list[dict] = []
    for ruta in rutas[:3]:
        items.extend(parsear_analisishoy(ruta))

    # Únicas por URL Cloudinary (más reciente primero)
    vistos: set[str] = set()
    unicos: list[dict] = []
    for it in sorted(items, key=lambda x: x.get("fecha_detencion", ""), reverse=True):
        u = it.get("url_video") or ""
        if not u or u in vistos:
            continue
        vistos.add(u)
        unicos.append(it)

    print(f"Archivos MD: {[p.name for p in rutas[:3]]}")
    print(f"Coincidencias con video: {len(unicos)}")

    insertadas = 0
    ya_existen = 0
    errores: list[str] = []

    for it in unicos:
        url_vid = it["url_video"]
        try:
            ex = sb.table(TABLA).select("id").eq("url_video", url_vid).limit(1).execute()
            if ex.data:
                ya_existen += 1
                print(f"  SKIP (ya existe): {it['termino_detectado']} | {url_vid[-50:]}")
                continue
            sb.table(TABLA).insert(it).execute()
            insertadas += 1
            print(f"  OK: {it['termino_detectado']} | {it['nombre_medio']} | {it['nombre_archivo']}")
        except Exception as e:
            errores.append(f"{it['termino_detectado']}: {e}")
            print(f"  ERR: {it['termino_detectado']} -> {e}")

    # Últimos 5 en tabla
    try:
        ult = (
            sb.table(TABLA)
            .select("id, termino_detectado, nombre_medio, fecha_detencion, url_video")
            .order("id", desc=True)
            .limit(5)
            .execute()
        )
        print("\nÚltimos 5 en Supabase:")
        for row in ult.data or []:
            print(f"  id={row.get('id')} | {row.get('fecha_detencion')} | {row.get('termino_detectado')} | {row.get('nombre_medio')}")
    except Exception as e:
        print(f"No se pudo leer últimos registros: {e}")

    print(f"\nResumen: insertadas={insertadas}, ya_existían={ya_existen}, errores={len(errores)}")
    if errores:
        for err in errores:
            print(f"  - {err}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
