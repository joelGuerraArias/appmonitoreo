# -*- coding: utf-8 -*-
"""Prueba de prevideo obligatorio simulando una coincidencia Intrant (morrison / Telecentro)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from clip_intro import (
    MISTRAL_TTS_VOICE_ID,
    construir_texto_intro,
    prefijar_intro_coincidencia_obligatorio,
    _resolve_ffmpeg,
    _resolve_ffprobe,
)

# Coincidencia real de hoy (Intrant / morrison / Telecentro)
NOMBRE_EMISION = "tELECENTRO_480p_2026-05-19_07-19-19_seg000.mp4"
TERMINO = "morrison"
CLIENTE_ID = "intrant"
SALIDA_DIR = ROOT / "videos procesados" / "pruebas_prevideo"
SALIDA_MP4 = SALIDA_DIR / f"PRUEBA_prevideo_{TERMINO}_{NOMBRE_EMISION}"


def _crear_clip_prueba(destino: str, segundos: float = 5.0) -> bool:
    ff = _resolve_ffmpeg()
    if not ff:
        print("FAIL: ffmpeg no encontrado")
        return False
    subprocess.run(
        [
            ff,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1E88E5:s=1280x720:d={segundos}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={segundos}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            destino,
        ],
        check=True,
        capture_output=True,
    )
    return True


def _duracion(path: str) -> float:
    fp = _resolve_ffprobe()
    if not fp:
        return 0.0
    r = subprocess.run(
        [fp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
    )
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def main() -> int:
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        print("FAIL: MISTRAL_API_KEY no configurada en .env")
        return 1

    texto = construir_texto_intro(TERMINO, NOMBRE_EMISION)
    print("=== Guion TTS ===")
    print(texto)
    print(f"Voz: {MISTRAL_TTS_VOICE_ID}")
    print()

    tmp = tempfile.mkdtemp(prefix="prueba_previo_")
    clip_src = os.path.join(tmp, "clip_sin_intro.mp4")
    try:
        if not _crear_clip_prueba(clip_src):
            return 1
        dur_antes = _duracion(clip_src)
        print(f"Clip prueba (sin intro): {dur_antes:.1f}s")

        out_path, ok, msg = prefijar_intro_coincidencia_obligatorio(
            clip_src,
            TERMINO,
            NOMBRE_EMISION,
            mistral_api_key=api_key,
            cliente_id=CLIENTE_ID,
        )
        print(f"Resultado: ok={ok} msg={msg}")

        if not ok:
            print("FAIL: previo obligatorio no se aplicó")
            return 1

        dur_despues = _duracion(out_path)
        print(f"Clip con previo: {dur_despues:.1f}s (debe ser > {dur_antes:.1f}s)")

        SALIDA_DIR.mkdir(parents=True, exist_ok=True)
        dest_final = str(SALIDA_MP4)
        if dest_final.endswith(".mp4"):
            pass
        else:
            dest_final += ".mp4"
        shutil.copy2(out_path, dest_final)
        print()
        print("PASS: prevideo de coincidencia generado correctamente")
        print(f"Archivo: {dest_final}")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
