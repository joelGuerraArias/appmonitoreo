# -*- coding: utf-8 -*-
"""
Intro de logo + voz (Mistral TTS) para prefijar clips de coincidencia.
"""
from __future__ import annotations

import base64
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

_DIR_SCRIPT = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _env_str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


# Lectura en import (tras load_dotenv); prefijar_intro relee INTRO_CLIP_ENABLED si hace falta
LOGOS_CANAL_DIR = Path(_env_str("LOGOS_CANAL_DIR", str(_DIR_SCRIPT / "logos"))).resolve()
INTRO_CLIP_ENABLED = _env_bool("INTRO_CLIP_ENABLED", True)
MISTRAL_TTS_VOICE_ID = _env_str("MISTRAL_TTS_VOICE_ID", "mi voz")
MISTRAL_TTS_MODEL = _env_str("MISTRAL_TTS_MODEL", "voxtral-mini-tts-2603")
MISTRAL_TTS_API_URL = _env_str("MISTRAL_TTS_API_URL", "https://api.mistral.ai/v1/audio/speech")
INTRO_AUDIO_PADDING_SEC = float(_env_str("INTRO_AUDIO_PADDING_SEC", "0.35") or "0.35")

_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _subprocess_no_window_kw():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def _resolve_ffprobe() -> str:
    directo = os.getenv("FFPROBE_PATH", "").strip()
    if directo and os.path.isfile(directo):
        return directo
    fb = os.getenv("FFMPEG_BIN", "").strip()
    if fb:
        for name in ("ffprobe.exe", "ffprobe"):
            p = os.path.join(fb, name)
            if os.path.isfile(p):
                return p
    return shutil.which("ffprobe") or shutil.which("ffprobe.exe") or ""


def _resolve_ffmpeg() -> str:
    directo = os.getenv("FFMPEG_PATH", "").strip()
    if directo and os.path.isfile(directo):
        return directo
    fb = os.getenv("FFMPEG_BIN", "").strip()
    if fb:
        for name in ("ffmpeg.exe", "ffmpeg"):
            p = os.path.join(fb, name)
            if os.path.isfile(p):
                return p
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or ""


def extraer_slug_canal_desde_archivo(nombre_archivo: str) -> str:
    """Prefijo del canal antes de fecha YYYY-MM-DD_HH-MM-SS (misma idea que extraer_info_medio_hora)."""
    nombre_sin_ext = os.path.splitext(os.path.basename(nombre_archivo or ""))[0]
    patron = r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})"
    match = re.search(patron, nombre_sin_ext)
    if match:
        slug = nombre_sin_ext[: match.start()].strip("_").strip()
    else:
        slug = nombre_sin_ext.split("_")[0] if "_" in nombre_sin_ext else nombre_sin_ext
    slug = re.sub(r"_\d+p$", "", slug, flags=re.IGNORECASE).strip()
    slug = re.sub(r"\s+\d+p\s*$", "", slug, flags=re.IGNORECASE).strip()
    return slug or "CANAL"


def extraer_medio_y_hora_legible(nombre_archivo: str) -> Tuple[str, str]:
    """Devuelve (nombre_medio, frase_hora) para el guion TTS."""
    nombre_sin_ext = os.path.splitext(os.path.basename(nombre_archivo or ""))[0]
    patron = r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})"
    match = re.search(patron, nombre_sin_ext)
    if not match:
        medio = nombre_sin_ext.replace("_", " ").strip() or "medio desconocido"
        return medio, "hora no disponible en el nombre del archivo"

    año, mes, dia, hora, minuto, _seg = match.groups()
    meses_es = (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    )
    nombre_mes = meses_es[int(mes) - 1] if 1 <= int(mes) <= 12 else mes
    hora_int = int(hora)
    if hora_int == 0:
        hora_12, am_pm = "12", "de la mañana"
    elif hora_int < 12:
        hora_12, am_pm = str(hora_int), "de la mañana"
    elif hora_int == 12:
        hora_12, am_pm = "12", "de la tarde"
    else:
        hora_12, am_pm = str(hora_int - 12), "de la tarde"

    nombre_medio = nombre_sin_ext[: match.start()].replace("_", " ").strip()
    nombre_medio = re.sub(r"\s+\d+p\s*$", "", nombre_medio, flags=re.IGNORECASE).strip()
    nombre_medio = " ".join(w.capitalize() for w in nombre_medio.split()) or "Medio"

    frase_hora = f"a las {hora_12}:{minuto} {am_pm} del {int(dia)} de {nombre_mes} de {año}"
    return nombre_medio, frase_hora


def construir_texto_intro(termino: str, nombre_archivo: str) -> str:
    medio, frase_hora = extraer_medio_y_hora_legible(nombre_archivo)
    term = (termino or "").strip() or "término"
    return (
        f"Coincidencia: {term}. "
        f"Medio: {medio}. "
        f"{frase_hora}."
    )


def resolver_logo_canal(nombre_archivo: str, logos_dir: Optional[Path] = None) -> Optional[str]:
    """Ruta al logo del canal o None si no existe."""
    base_dir = Path(logos_dir) if logos_dir else LOGOS_CANAL_DIR
    if not base_dir.is_dir():
        return None

    slug = extraer_slug_canal_desde_archivo(nombre_archivo)
    candidatos = [
        slug,
        slug.upper(),
        slug.lower(),
        slug.replace(" ", "_"),
        slug.replace(" ", "_").upper(),
    ]
    visto = set()
    for nombre in candidatos:
        if not nombre or nombre in visto:
            continue
        visto.add(nombre)
        for ext in _LOGO_EXTENSIONS:
            p = base_dir / f"{nombre}{ext}"
            if p.is_file():
                return str(p)
    return None


def generar_audio_intro_mistral(
    texto: str,
    api_key: str,
    destino_mp3: str,
    voice_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[bool, str]:
    if not api_key:
        return False, "MISTRAL_API_KEY vacía"
    if not (texto or "").strip():
        return False, "Texto TTS vacío"

    payload = {
        "model": model or _env_str("MISTRAL_TTS_MODEL", MISTRAL_TTS_MODEL),
        "input": texto.strip(),
        "voice_id": (voice_id or _env_str("MISTRAL_TTS_VOICE_ID", MISTRAL_TTS_VOICE_ID)) or None,
        "response_format": "mp3",
    }
    if not payload["voice_id"]:
        del payload["voice_id"]

    try:
        resp = requests.post(
            MISTRAL_TTS_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        if resp.status_code != 200:
            return False, f"TTS HTTP {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        b64 = data.get("audio_data")
        if not b64:
            return False, "Respuesta TTS sin audio_data"
        os.makedirs(os.path.dirname(os.path.abspath(destino_mp3)) or ".", exist_ok=True)
        with open(destino_mp3, "wb") as f:
            f.write(base64.b64decode(b64))
        return True, destino_mp3
    except Exception as e:
        return False, str(e)


def _probe_media(path: str, ffprobe: str) -> dict:
    out = {"width": 1280, "height": 720, "fps": 25.0, "duration": None}
    if not ffprobe or not os.path.isfile(path):
        return out

    def _run(args):
        return subprocess.run(
            [ffprobe, "-v", "error", *args, path],
            capture_output=True,
            text=True,
            **_subprocess_no_window_kw(),
        )

    r = _run(
        [
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-of",
            "csv=p=0:s=x",
        ]
    )
    if r.returncode == 0 and (r.stdout or "").strip():
        parts = (r.stdout.strip().splitlines()[0] or "").split("x")
        if len(parts) >= 2:
            try:
                out["width"] = max(2, int(parts[0]))
                out["height"] = max(2, int(parts[1]))
            except ValueError:
                pass
        if len(parts) >= 3 and parts[2]:
            fr = parts[2].strip()
            if "/" in fr:
                n, d = fr.split("/", 1)
                try:
                    out["fps"] = float(n) / float(d) if float(d) else 25.0
                except ValueError:
                    pass

    r2 = _run(["-show_entries", "format=duration", "-of", "csv=p=0"])
    if r2.returncode == 0 and (r2.stdout or "").strip():
        try:
            out["duration"] = float(r2.stdout.strip().splitlines()[0])
        except ValueError:
            pass
    return out


def _crear_video_intro_desde_logo(
    logo_path: str,
    audio_path: str,
    salida_mp4: str,
    width: int,
    height: int,
    fps: float,
    ffmpeg: str,
    ffprobe: str,
) -> Tuple[bool, str]:
    audio_info = _probe_media(audio_path, ffprobe)
    dur = (audio_info.get("duration") or 3.0) + INTRO_AUDIO_PADDING_SEC
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        logo_path,
        "-i",
        audio_path,
        "-t",
        str(dur),
        "-vf",
        vf,
        "-r",
        str(max(1, int(round(fps)))),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        salida_mp4,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **_subprocess_no_window_kw(),
        )
        return True, salida_mp4
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", errors="replace")[:400]
        return False, f"ffmpeg intro: {err}"


def _concatenar_videos(intro_mp4: str, clip_mp4: str, salida_mp4: str, ffmpeg: str) -> Tuple[bool, str]:
    """Concatena intro + clip re-codificando a h.264/aac unificado."""
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        intro_mp4,
        "-i",
        clip_mp4,
        "-filter_complex",
        "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[v][a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        salida_mp4,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **_subprocess_no_window_kw(),
        )
        return True, salida_mp4
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode("utf-8", errors="replace")[:400]
        return False, f"ffmpeg concat: {err}"


def prefijar_intro_coincidencia_si(
    clip_path: str,
    termino: str,
    nombre_archivo: str,
    *,
    mistral_api_key: str = "",
    enabled: Optional[bool] = None,
    logos_dir: Optional[Path] = None,
    log_fn: Optional[Callable[[str, str], None]] = None,
    ui_info: Optional[Callable[[str], None]] = None,
    ui_warning: Optional[Callable[[str], None]] = None,
) -> Tuple[str, bool, str]:
    """
    Si está habilitado y hay logo + TTS OK, antepone intro al clip y reemplaza el archivo.
    Devuelve (clip_path_final, ok_intro, mensaje).
  ok_intro False = se usó clip original sin intro (no es error fatal).
    """
    if enabled is None:
        enabled = _env_bool("INTRO_CLIP_ENABLED", INTRO_CLIP_ENABLED)
    if not enabled:
        return clip_path, False, "Intro desactivado (INTRO_CLIP_ENABLED)"

    if not clip_path or not os.path.isfile(clip_path):
        return clip_path, False, "Clip no existe"

    def _log(msg, level="info"):
        if log_fn:
            log_fn(msg, level)
        else:
            getattr(logger, level if level in ("info", "warning", "error") else "info")(msg)

    logo = resolver_logo_canal(nombre_archivo, logos_dir=logos_dir)
    if not logo:
        msg = f"Sin logo en {LOGOS_CANAL_DIR} para canal '{extraer_slug_canal_desde_archivo(nombre_archivo)}'"
        _log(msg, "warning")
        if ui_warning:
            ui_warning(f"⏭️ Intro omitida: {msg}")
        return clip_path, False, msg

    ffmpeg = _resolve_ffmpeg()
    ffprobe = _resolve_ffprobe()
    if not ffmpeg or not ffprobe:
        msg = "ffmpeg/ffprobe no disponibles para intro"
        _log(msg, "warning")
        if ui_warning:
            ui_warning(f"⏭️ Intro omitida: {msg}")
        return clip_path, False, msg

    texto = construir_texto_intro(termino, nombre_archivo)
    tmpdir = tempfile.mkdtemp(prefix="clip_intro_")
    audio_mp3 = os.path.join(tmpdir, "intro.mp3")
    intro_mp4 = os.path.join(tmpdir, "intro.mp4")
    merged_mp4 = os.path.join(tmpdir, "merged.mp4")

    try:
        ok_tts, msg_tts = generar_audio_intro_mistral(texto, mistral_api_key, audio_mp3)
        if not ok_tts:
            _log(f"TTS falló: {msg_tts}", "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (TTS): {msg_tts}")
            return clip_path, False, msg_tts

        meta = _probe_media(clip_path, ffprobe)
        w, h = meta["width"], meta["height"]
        fps = meta.get("fps") or 25.0

        ok_vid, msg_vid = _crear_video_intro_desde_logo(
            logo, audio_mp3, intro_mp4, w, h, fps, ffmpeg, ffprobe
        )
        if not ok_vid:
            _log(msg_vid, "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (video logo): {msg_vid}")
            return clip_path, False, msg_vid

        ok_cat, msg_cat = _concatenar_videos(intro_mp4, clip_path, merged_mp4, ffmpeg)
        if not ok_cat:
            _log(msg_cat, "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (concat): {msg_cat}")
            return clip_path, False, msg_cat

        backup = clip_path + ".sin_intro.bak"
        try:
            if os.path.exists(backup):
                os.remove(backup)
            os.replace(clip_path, backup)
            os.replace(merged_mp4, clip_path)
            if os.path.exists(backup):
                os.remove(backup)
        except OSError as e:
            if os.path.isfile(merged_mp4):
                shutil.copy2(merged_mp4, clip_path)
            return clip_path, False, f"No se pudo reemplazar clip: {e}"

        msg_ok = f"Intro añadida ({os.path.basename(logo)})"
        _log(msg_ok, "info")
        if ui_info:
            ui_info(f"🎬 {msg_ok}")
        return clip_path, True, msg_ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
