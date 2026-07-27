#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba rápida de subida a Cloudflare R2 (mismas variables R2_* que la app)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import r2_storage  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Subir un archivo local a R2 e imprimir la URL de acceso.")
    p.add_argument("local_path", type=Path, help="Ruta al fichero local")
    p.add_argument(
        "--key",
        required=True,
        help="Clave de objeto en el bucket (ej. video_analyzer_clips/termino_20260101_clip.mp4)",
    )
    p.add_argument(
        "--object-url",
        action="store_true",
        help="Imprimir solo la URL (salida mínima para scripts)",
    )
    args = p.parse_args()
    path = args.local_path.resolve()
    if not path.is_file():
        print(f"No existe el fichero: {path}", file=sys.stderr)
        return 1
    if not r2_storage.r2_ready():
        miss = r2_storage.r2_missing_env_vars()
        if r2_storage.r2_global_disabled():
            print("R2 desactivado (R2_ENABLED).", file=sys.stderr)
        elif miss:
            print("Falta en .env: " + ", ".join(miss), file=sys.stderr)
        else:
            print("R2 no configurado.", file=sys.stderr)
        return 2
    try:
        url, key = r2_storage.upload_local_file(path, args.key)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 3
    if args.object_url:
        print(url)
    else:
        print(f"key={key}\nurl={url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
