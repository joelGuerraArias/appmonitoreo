# -*- coding: utf-8 -*-
"""Prueba local de clip_intro (composición frame; TTS solo si hay API key)."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from clip_intro import (
    _componer_frame_preroll,
    _extraer_primer_frame,
    _lineas_texto_preroll,
    _probe_media,
    construir_texto_intro,
    extraer_slug_canal_desde_archivo,
    prefijar_intro_coincidencia_si,
    resolver_logo_medio,
    _resolve_ffmpeg,
    _resolve_ffprobe,
)


def _make_test_clip(path: str, seconds: float = 2.0):
    ff = _resolve_ffmpeg()
    if not ff:
        print("SKIP: sin ffmpeg")
        return False
    subprocess.run(
        [
            ff,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=blue:s=640x360:d={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            path,
        ],
        check=True,
        capture_output=True,
    )
    return True


def main():
    nombre = "TELEANTILLAS_720p_2025-09-15_07-37-25.mp4"
    slug = extraer_slug_canal_desde_archivo(nombre)
    texto = construir_texto_intro("INTRANT", nombre)
    l1, l2 = _lineas_texto_preroll("INTRANT", nombre)
    print("slug:", slug)
    print("texto TTS:", texto)
    print("líneas overlay:", l1, "|", l2)
    logo = resolver_logo_medio(nombre)
    print("logo medio:", logo or "(ninguno — coloca TELEANTILLAS.png en logos/)")

    if not _resolve_ffmpeg() or not _resolve_ffprobe():
        print("FAIL: ffmpeg/ffprobe requeridos")
        return 1

    tmp = tempfile.mkdtemp(prefix="smoke_intro_")
    clip = os.path.join(tmp, "clip_test.mp4")
    if not _make_test_clip(clip):
        return 1

    ff = _resolve_ffmpeg()
    fp = _resolve_ffprobe()
    frame_raw = os.path.join(tmp, "frame_raw.png")
    frame_intro = os.path.join(tmp, "frame_intro.png")

    ok_frame, msg_frame = _extraer_primer_frame(clip, frame_raw, ff)
    print("extraer frame:", ok_frame, msg_frame)
    if not ok_frame:
        print("FAIL: no se pudo extraer primer frame")
        return 1

    meta = _probe_media(clip, fp)
    w, h = meta["width"], meta["height"]

    if logo:
        ok_comp, msg_comp = _componer_frame_preroll(
            frame_raw, logo, l1, l2, frame_intro, w, h
        )
        print("componer frame:", ok_comp, msg_comp)
        if ok_comp and os.path.isfile(frame_intro):
            print("PASS: PNG preroll compuesto en", frame_intro)
        else:
            print("FAIL: composición de frame")
            return 1
    else:
        print("SKIP composición: sin logo del medio")

    api_key = os.getenv("MISTRAL_API_KEY", "")
    out, ok, msg = prefijar_intro_coincidencia_si(
        clip,
        "INTRANT",
        nombre,
        mistral_api_key=api_key,
        enabled=True,
    )
    print("prefijar intro:", ok, msg, "out:", out)
    if ok and os.path.isfile(out):
        dur_orig = meta.get("duration") or 0
        dur_new = (_probe_media(out, fp).get("duration") or 0)
        print(f"duración: {dur_orig:.2f}s -> {dur_new:.2f}s")
        print("PASS: clip con preroll generado")
        return 0
    if not logo:
        print("SKIP: sin logo del medio (esperado si no hay TELEANTILLAS.png)")
        return 0
    if not api_key:
        print("SKIP: sin MISTRAL_API_KEY (TTS no probado; intro omitida es esperado)")
        return 0
    print("WARN: intro no aplicada:", msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
