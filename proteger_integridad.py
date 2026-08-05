#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Blindaje de arranque — Video Analyzer v5.7 Intrant
==================================================
Restaura archivos críticos si Cursor/disco los deja en 0 bytes o “válidos pero inútiles”
(p. ej. Intrant con Brevo/Telegram apagados y sin API key).

Se ejecuta desde el .bat ANTES de Streamlit y también al inicio de appMonitoreo.

Uso:
  python proteger_integridad.py
  python proteger_integridad.py --check-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKUPS = ROOT / "backups"
LOG_CAUSAS = ROOT / "logs" / "integridad_causas.log"

# (ruta relativa, mínimo bytes sanos, candidatos de backup en orden)
# clientes: preferir golden / pre-v5.5 (con credenciales) ANTES que latest (puede envenenarse)
CRITICOS = [
    (
        "appMonitoreo.py",
        50_000,
        [
            "backups/appMonitoreo_v55_backup.py",
            "backups/appMonitoreo_latest.py",
        ],
    ),
    (
        ".env",
        50,
        [
            "backups/env_latest.env",
        ],
    ),
    (
        "clientes_config.json",
        200,
        [
            "backups/clientes_config_intrant_golden.json",
            "clientes_config.bak_pre_v5.5_multiclient.json",
            "clientes_config.bak_before_repair_20260714_212903.json",
            "backups/clientes_config_latest.json",
        ],
    ),
    (
        "terminos_guardados.json",
        50,
        [
            "backups/terminos_guardados_latest.json",
            "terminos_guardados.bak_pre_v5.5.json",
        ],
    ),
]

# Solo .env en readonly: clientes_config debe poder guardarse desde la app
READONLY_DESPUES = {".env"}


def _size(p: Path) -> int:
    try:
        return p.stat().st_size if p.exists() else 0
    except OSError:
        return 0


def _quitar_readonly(p: Path) -> None:
    try:
        if p.exists():
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _poner_readonly(p: Path) -> None:
    try:
        if p.exists():
            os.chmod(p, stat.S_IREAD)
    except OSError:
        pass


def _log_causa(msg: str) -> None:
    try:
        LOG_CAUSAS.parent.mkdir(parents=True, exist_ok=True)
        line = f"{datetime.now().isoformat(timespec='seconds')} {msg}\n"
        with open(LOG_CAUSAS, "a", encoding="utf-8") as f:
            f.write(line)
        print(f"[CAUSA] {msg}")
    except Exception:
        print(f"[CAUSA] {msg}")


def _json_ok(p: Path) -> bool:
    try:
        raw = p.read_text(encoding="utf-8-sig")
        if not raw.strip():
            return False
        json.loads(raw)
        return True
    except Exception:
        return False


def _intrant_desde_data(data: dict) -> dict | None:
    for c in data.get("clientes") or []:
        if (c.get("id") or "").strip().lower() == "intrant":
            return c
    return None


def _intrant_canales_ok(intrant: dict | None) -> tuple[bool, str]:
    """
    Intrant es usable solo si los canales clave tienen credenciales y enabled.
    Un JSON 'válido' con enabled=false y api_key vacía NO es sano (causa Omitido en UI).
    """
    if not intrant:
        return False, "sin cliente Intrant"
    rotos = []
    b = intrant.get("brevo") or {}
    if not b.get("enabled"):
        rotos.append("brevo.enabled=false")
    if not (b.get("api_key") or "").strip():
        rotos.append("brevo.api_key vacío")
    if not (b.get("correos_destinatarios") or []):
        rotos.append("brevo.destinatarios vacío")
    tg = intrant.get("telegram") or {}
    if not tg.get("enabled"):
        rotos.append("telegram.enabled=false")
    if not (tg.get("bot_token") or "").strip():
        rotos.append("telegram.bot_token vacío")
    gd = intrant.get("google_drive") or {}
    if not gd.get("enabled"):
        rotos.append("google_drive.enabled=false")
    gs = intrant.get("google_sheets") or {}
    if not gs.get("enabled") or not (gs.get("spreadsheet_id") or "").strip():
        rotos.append("google_sheets apagado/sin id")
    if rotos:
        return False, "; ".join(rotos)
    return True, "ok"


def _forzar_canales_en_intrant(intrant: dict) -> None:
    b = intrant.setdefault("brevo", {})
    if (b.get("api_key") or "").strip() and (b.get("correos_destinatarios") or []):
        b["enabled"] = True
    tg = intrant.setdefault("telegram", {})
    if (tg.get("bot_token") or "").strip() and (tg.get("chat_id") or "").strip():
        tg["enabled"] = True
    gd = intrant.setdefault("google_drive", {})
    if (gd.get("folder_id") or "").strip():
        gd["enabled"] = True
    gs = intrant.setdefault("google_sheets", {})
    if (gs.get("spreadsheet_id") or "").strip():
        gs["enabled"] = True
    cl = intrant.setdefault("cloudinary", {})
    if (cl.get("cloud_name") or "").strip() and (cl.get("api_key") or "").strip():
        cl["enabled"] = True
    intrant.setdefault("r2", {})["enabled"] = True
    sb = intrant.setdefault("supabase", {})
    if (sb.get("url") or "").strip():
        sb["enabled"] = True
    intrant["activo"] = True
    intrant["incluir_en_analisis"] = True


def _es_sano(rel: str, minimo: int) -> bool:
    p = ROOT / rel
    if _size(p) < minimo:
        if _size(p) == 0 and p.exists():
            _log_causa(f"{rel}: archivo en 0 bytes (wipe Cursor/disco)")
        elif not p.exists():
            _log_causa(f"{rel}: no existe")
        else:
            _log_causa(f"{rel}: size={_size(p)} < minimo={minimo}")
        return False
    if rel.endswith(".json"):
        if not _json_ok(p):
            _log_causa(f"{rel}: JSON vacío/corrupto")
            return False
        if rel == "clientes_config.json":
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception as e:
                _log_causa(f"{rel}: no parsea ({e})")
                return False
            intrant = _intrant_desde_data(data)
            ok, motivo = _intrant_canales_ok(intrant)
            if not ok:
                _log_causa(
                    f"{rel}: JSON válido PERO Intrant inutilizable → {motivo}. "
                    "Esto es lo que produce 'Omitido — *.enabled es falso' en la UI."
                )
                return False
        return True
    if rel == ".env":
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "GOOGLE_REFRESH_TOKEN=" not in txt and "OPENAI_API_KEY=" not in txt:
            _log_causa(f"{rel}: falta GOOGLE_REFRESH_TOKEN/OPENAI_API_KEY")
            return False
        return True
    if rel == "appMonitoreo.py":
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "st.set_page_config" not in txt or "MODO_SOLO_INTRANT" not in txt:
            _log_causa(f"{rel}: contenido incompleto (falta set_page_config/MODO_SOLO_INTRANT)")
            return False
        return True
    return True


def _backup_intrant_utilizable(src: Path) -> tuple[bool, str]:
    try:
        data = json.loads(src.read_text(encoding="utf-8-sig"))
        ok, motivo = _intrant_canales_ok(_intrant_desde_data(data))
        return ok, motivo
    except Exception as e:
        return False, str(e)


def _restaurar(rel: str, candidatos: list[str]) -> bool:
    dest = ROOT / rel
    for cand in candidatos:
        src = ROOT / cand
        if not src.exists() or _size(src) < 50:
            continue
        if rel.endswith(".json") and not _json_ok(src):
            continue
        if rel == "appMonitoreo.py":
            t = src.read_text(encoding="utf-8", errors="ignore")
            if "st.set_page_config" not in t:
                continue
        try:
            _quitar_readonly(dest)
            if rel == "clientes_config.json":
                util, motivo = _backup_intrant_utilizable(src)
                if not util:
                    _log_causa(f"Omitiendo backup {cand}: Intrant inutilizable ({motivo})")
                    continue
                data = json.loads(src.read_text(encoding="utf-8-sig"))
                clientes = data.get("clientes") or []
                intrant = next(
                    (c for c in clientes if (c.get("id") or "").lower() == "intrant"),
                    None,
                )
                if not intrant:
                    continue
                intrant["id"] = "intrant"
                _forzar_canales_en_intrant(intrant)
                out = {
                    "clientes": [intrant],
                    "fecha_actualizacion": datetime.now().isoformat(),
                    "total_clientes": 1,
                    "modo": "solo_intrant",
                    "version": "5.5",
                }
                dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                shutil.copy2(src, dest)
            _log_causa(f"Restaurado {rel} desde {cand} ({_size(dest)} bytes)")
            print(f"[OK] Restaurado {rel} desde {cand} ({_size(dest)} bytes)")
            return True
        except Exception as e:
            print(f"[WARN] No se pudo restaurar {rel} desde {cand}: {e}")
            _log_causa(f"Fallo restaurando {rel} desde {cand}: {e}")
    print(f"[FAIL] Sin backup válido para {rel}")
    _log_causa(f"Sin backup válido utilizable para {rel}")
    return False


def _actualizar_backup(rel: str) -> None:
    """Si el archivo está sano Y utilizable, refresca latest (y golden para clientes)."""
    BACKUPS.mkdir(exist_ok=True)
    src = ROOT / rel
    mapa = {
        "appMonitoreo.py": BACKUPS / "appMonitoreo_latest.py",
        ".env": BACKUPS / "env_latest.env",
        "clientes_config.json": BACKUPS / "clientes_config_latest.json",
        "terminos_guardados.json": BACKUPS / "terminos_guardados_latest.json",
    }
    dest = mapa.get(rel)
    if not dest:
        return
    try:
        _quitar_readonly(dest)
        if rel == "clientes_config.json":
            data = json.loads(src.read_text(encoding="utf-8-sig"))
            intrant = _intrant_desde_data(data)
            ok, motivo = _intrant_canales_ok(intrant)
            if not ok:
                _log_causa(f"NO se actualiza clientes_config_latest (Intrant inutilizable: {motivo})")
                return
            _forzar_canales_en_intrant(intrant)
            out = {
                "clientes": [intrant],
                "fecha_actualizacion": datetime.now().isoformat(),
                "total_clientes": 1,
                "modo": "solo_intrant",
                "version": "5.5",
            }
            payload = json.dumps(out, indent=2, ensure_ascii=False)
            dest.write_text(payload, encoding="utf-8")
            # Golden: solo se escribe si Intrant está 100% usable; no se pisa con basura
            golden = BACKUPS / "clientes_config_intrant_golden.json"
            _quitar_readonly(golden)
            golden.write_text(payload, encoding="utf-8")
        else:
            shutil.copy2(src, dest)
        if rel in (".env", "appMonitoreo.py"):
            stamp = datetime.now().strftime("%Y%m%d")
            if rel == "appMonitoreo.py":
                extra = BACKUPS / f"appMonitoreo_daily_{stamp}.py"
            else:
                extra = BACKUPS / f"{Path(rel).stem}_daily_{stamp}{Path(rel).suffix or ''}"
            if not extra.exists():
                shutil.copy2(src, extra)
    except Exception as e:
        print(f"[WARN] Backup {rel}: {e}")
        _log_causa(f"Backup {rel} falló: {e}")


def proteger(check_only: bool = False) -> int:
    BACKUPS.mkdir(exist_ok=True)
    fallos = 0
    print(f"=== Blindaje integridad {datetime.now().isoformat(timespec='seconds')} ===")
    for rel, minimo, cands in CRITICOS:
        sano = _es_sano(rel, minimo)
        sz = _size(ROOT / rel)
        if sano:
            print(f"[OK] {rel} ({sz} bytes)")
            if not check_only:
                _actualizar_backup(rel)
                if rel in READONLY_DESPUES:
                    _poner_readonly(ROOT / rel)
            continue
        print(f"[BAD] {rel} size={sz} — restaurando...")
        if check_only:
            fallos += 1
            continue
        if _restaurar(rel, cands):
            if _es_sano(rel, minimo):
                _actualizar_backup(rel)
                if rel in READONLY_DESPUES:
                    _poner_readonly(ROOT / rel)
            else:
                fallos += 1
                _log_causa(f"{rel}: sigue BAD tras restaurar")
        else:
            fallos += 1
    try:
        man = BACKUPS / "INTEGRIDAD_MANIFEST.txt"
        lines = [
            f"fecha: {datetime.now().isoformat(timespec='seconds')}",
            f"fallos: {fallos}",
            "nota: Intrant con enabled=false ya NO cuenta como sano",
        ]
        for rel, minimo, _ in CRITICOS:
            lines.append(f"{rel}: size={_size(ROOT / rel)} sano={_es_sano(rel, minimo)}")
        man.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    print(f"=== Fin blindaje (fallos={fallos}) ===")
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    return proteger(check_only=args.check_only)


if __name__ == "__main__":
    sys.exit(main())
