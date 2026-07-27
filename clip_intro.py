# -*- coding: utf-8 -*-
"""
Preroll visual (frame congelado + logo del medio + texto) + voz Mistral TTS
para prefijar clips de coincidencia.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
MISTRAL_TTS_VOICE_ID = _env_str(
    "MISTRAL_TTS_VOICE_ID", "929d7b7c-9df5-43d4-be6a-a66695523f6e"
)
MISTRAL_TTS_MODEL = _env_str("MISTRAL_TTS_MODEL", "voxtral-mini-tts-2603")
MISTRAL_TTS_API_URL = _env_str("MISTRAL_TTS_API_URL", "https://api.mistral.ai/v1/audio/speech")
INTRO_AUDIO_PADDING_SEC = float(_env_str("INTRO_AUDIO_PADDING_SEC", "0.35") or "0.35")
INTRO_FREEZE_LOGO_BOX_RATIO = float(_env_str("INTRO_FREEZE_LOGO_BOX_RATIO", "0.15") or "0.15")
INTRO_FREEZE_LOGO_BORDER = int(_env_str("INTRO_FREEZE_LOGO_BORDER", "3") or "3")

_LOGO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
_UUID_VOICE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_voice_id_cache: dict[str, str] = {}
_MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
_MESES_ES_RE = (
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)"
)
# Logo por entidad/cliente si no hay logo del canal en logos/
_CLIENTE_LOGO_FILES: dict[str, list[str]] = {
    "default": ["logo edesur.png", "logo edesur.jpg"],
    "intrant": ["LOGO INTRANT.PNG", "LOGO INTRANT.png"],
    "minerd": ["FGJ MEDIOS.png"],
}


def _norm_logo_key(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (texto or "").lower())


def _nombre_base_archivo_limpio(nombre_archivo: str) -> str:
    """Quita sufijos clip, YouTube id, fechas cola y deja prefijo de canal/emisión."""
    nombre = os.path.splitext(os.path.basename(nombre_archivo or ""))[0]
    nombre = re.sub(r"_clip_\d+$", "", nombre, flags=re.IGNORECASE)
    nombre = re.sub(r"\s*\[[^\]]+\]\s*", " ", nombre).strip()
    nombre = re.sub(r"_\d{4}-\d{2}-\d{2}$", "", nombre)
    nombre = re.sub(
        rf"(?:_-)?_?{_MESES_ES_RE}_\d{{1,2}}_\d{{4}}.*$",
        "",
        nombre,
        flags=re.IGNORECASE,
    )
    nombre = re.sub(r"_-\s*$", "", nombre)
    nombre = re.sub(r"[-_]+$", "", nombre)
    nombre = re.sub(r"_\d+p$", "", nombre, flags=re.IGNORECASE)
    return nombre.strip("_- ") or nombre


def _limpiar_nombre_medio(raw: str) -> str:
    medio = (raw or "").replace("_", " ").strip()
    medio = re.sub(r"^(?:en\s+vivo\s*[-–]\s*)", "", medio, flags=re.IGNORECASE).strip()
    medio = re.sub(r"\s+\d+p\s*$", "", medio, flags=re.IGNORECASE).strip()
    medio = re.sub(r"\s+clip\s+\d+\s*$", "", medio, flags=re.IGNORECASE).strip()
    medio = re.sub(r"\s+seg\d+\s*$", "", medio, flags=re.IGNORECASE).strip()
    medio = re.sub(r"\s+\d{4}-\d{2}-\d{2}\s*$", "", medio).strip()
    medio = re.sub(r"\s+", " ", medio).strip(" -_")
    if not medio:
        return "Medio"
    return " ".join(w.capitalize() for w in medio.split())


def _formatear_hora_tts(hora: int, minuto: int) -> str:
    if hora == 0:
        hora_12, am_pm = "12", "de la mañana"
    elif hora < 12:
        hora_12, am_pm = str(hora), "de la mañana"
    elif hora == 12:
        hora_12, am_pm = "12", "de la tarde"
    else:
        hora_12, am_pm = str(hora - 12), "de la tarde"
    return f"a las {hora_12}:{minuto:02d} {am_pm}"


def _formatear_fecha_tts(dia: int, mes: int, anio: int, hora: Optional[int] = None, minuto: Optional[int] = None) -> str:
    nombre_mes = _MESES_ES[mes - 1] if 1 <= mes <= 12 else str(mes)
    base = f"{dia} de {nombre_mes} de {anio}"
    if hora is not None and minuto is not None:
        return f"{base}, {_formatear_hora_tts(hora, minuto)}"
    return base


def _fuentes_texto_emision(nombre_archivo: str) -> list[str]:
    """Carpeta + archivo + ruta completa (prioriza carpeta emisión sobre clip_NN)."""
    ruta = (nombre_archivo or "").replace("\\", "/").strip()
    base = os.path.basename(ruta)
    carpeta = os.path.basename(os.path.dirname(ruta)) if "/" in ruta else ""
    fuentes = []
    if carpeta:
        fuentes.append(carpeta)
    if base:
        fuentes.append(os.path.splitext(base)[0])
    if ruta:
        fuentes.append(ruta)
    vistos = set()
    out = []
    for f in fuentes:
        f = f.strip()
        if f and f not in vistos:
            vistos.add(f)
            out.append(f)
    return out


def _intentar_patrones_fecha_hora(texto: str) -> list[dict]:
    """Devuelve candidatos {y,mo,d,h,mi,s,medio_raw,score} ordenados por score."""
    if not texto:
        return []
    patrones = [
        (
            100,
            re.compile(
                r"(?P<medio>.+?)_(?:\d+p)_"
                r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})_"
                r"(?P<h>\d{2})-(?P<mi>\d{2})-(?P<s>\d{2})",
                re.IGNORECASE,
            ),
        ),
        (
            90,
            re.compile(
                r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})_"
                r"(?P<h>\d{2})-(?P<mi>\d{2})-(?P<s>\d{2})"
            ),
        ),
        (
            85,
            re.compile(
                r"(?P<medio>.+?)\s+(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})\s+"
                r"(?P<h>\d{1,2})[_:\-](?P<mi>\d{2})(?:[_:\-](?P<s>\d{2}))?"
            ),
        ),
        (
            80,
            re.compile(
                r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})\s+"
                r"(?P<h>\d{1,2})[_:\-](?P<mi>\d{2})(?:[_:\-](?P<s>\d{2}))?"
            ),
        ),
        (
            70,
            re.compile(
                r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})[T\s_]"
                r"(?P<h>\d{1,2})[:\-_](?P<mi>\d{2})"
            ),
        ),
        (40, re.compile(r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})(?:_clip_|$|\s|_)")),
    ]
    candidatos = []
    for score_base, rx in patrones:
        for m in rx.finditer(texto):
            g = m.groupdict()
            try:
                y, mo, d = int(g["y"]), int(g["mo"]), int(g["d"])
                h = int(g["h"]) if g.get("h") else None
                mi = int(g["mi"]) if g.get("mi") else None
                s = int(g["s"]) if g.get("s") else 0
                if not (1 <= mo <= 12 and 1 <= d <= 31):
                    continue
                if h is not None and not (0 <= h <= 23 and 0 <= mi <= 59):
                    continue
                medio_raw = (g.get("medio") or texto[: m.start()]).strip(" -_")
                score = score_base + (10 if h is not None else 0)
                candidatos.append(
                    {
                        "y": y, "mo": mo, "d": d, "h": h, "mi": mi, "s": s,
                        "medio_raw": medio_raw, "score": score,
                    }
                )
            except (TypeError, ValueError):
                continue
    candidatos.sort(key=lambda c: (-c["score"], -(c["h"] or -1)))
    return candidatos


def _parsear_emision_llm(nombre_archivo: str, api_key: str) -> Optional[dict]:
    """Fallback: Mistral extrae medio/fecha/hora del nombre (formatos raros)."""
    if not api_key or not (nombre_archivo or "").strip():
        return None
    prompt = f"""Analiza este nombre de archivo de una grabación de TV/radio en República Dominicana.
Extrae el medio/canal, la fecha de emisión y la hora de inicio si aparecen en la ruta o el nombre.

Archivo: {nombre_archivo}

Responde ÚNICAMENTE JSON válido (sin markdown):
{{"medio":"nombre del canal","dia":31,"mes":5,"anio":2026,"hora":12,"minuto":16}}
- medio: texto legible en español (ej. Telesistema 11, Telecentro)
- mes: 1-12, hora/minuto en 24h; si no hay hora usa hora null y minuto null"""
    try:
        resp = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _env_str("INTRO_PARSE_LLM_MODEL", "mistral-small-latest"),
                "messages": [
                    {"role": "system", "content": "Respondes solo JSON válido."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=25,
        )
        if resp.status_code != 200:
            return None
        content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        y = int(data.get("anio") or data.get("año") or 0)
        mo = int(data.get("mes") or 0)
        d = int(data.get("dia") or 0)
        h = data.get("hora")
        mi = data.get("minuto")
        h = int(h) if h is not None else None
        mi = int(mi) if mi is not None else None
        if y < 2000 or not (1 <= mo <= 12 and 1 <= d <= 31):
            return None
        return {
            "medio": _limpiar_nombre_medio(str(data.get("medio") or "")),
            "y": y, "mo": mo, "d": d, "h": h, "mi": mi,
            "fecha_tts": _formatear_fecha_tts(d, mo, y, h, mi),
            "fuente": "llm",
        }
    except Exception:
        return None


def parsear_emision_desde_nombre_archivo(
    nombre_archivo: str,
    *,
    mistral_api_key: str = "",
    usar_llm_si_falta_hora: bool = True,
) -> dict:
    """
    Extrae medio, fecha y hora del nombre/ruta del archivo (multi-formato + LLM opcional).
    Ej.: Telesistema «En Vivo - Telesistema 11 2026-05-31 12_16» → 31 mayo 2026, 12:16.
    """
    mejor = None
    for fuente in _fuentes_texto_emision(nombre_archivo):
        for cand in _intentar_patrones_fecha_hora(fuente):
            if mejor is None or cand["score"] > mejor.get("_score", 0):
                medio = _limpiar_nombre_medio(cand.get("medio_raw") or fuente)
                if medio == "Medio" and fuente:
                    medio = _limpiar_nombre_medio(extraer_slug_canal_desde_archivo(fuente))
                mejor = {
                    "medio": medio,
                    "y": cand["y"], "mo": cand["mo"], "d": cand["d"],
                    "h": cand["h"], "mi": cand["mi"],
                    "fecha_tts": _formatear_fecha_tts(
                        cand["d"], cand["mo"], cand["y"], cand["h"], cand["mi"]
                    ),
                    "fuente": "heuristica",
                    "_score": cand["score"],
                }

    llm_on = _env_bool("INTRO_PARSE_LLM", False) or usar_llm_si_falta_hora
    api_key = mistral_api_key or _env_str("MISTRAL_API_KEY", "")
    if llm_on and api_key and (mejor is None or mejor.get("h") is None):
        parsed = _parsear_emision_llm(nombre_archivo, api_key)
        if parsed:
            if mejor and mejor.get("h") is None and parsed.get("h") is not None:
                parsed["medio"] = parsed.get("medio") or mejor.get("medio")
            if mejor is None or (parsed.get("h") is not None and mejor.get("h") is None):
                mejor = parsed

    if mejor:
        mejor.pop("_score", None)
        return mejor

    medio = _limpiar_nombre_medio(extraer_slug_canal_desde_archivo(nombre_archivo))
    return {
        "medio": medio,
        "y": None, "mo": None, "d": None, "h": None, "mi": None,
        "fecha_tts": "fecha no disponible en el nombre del archivo",
        "fuente": "fallback",
    }


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
    """Prefijo del canal (soporta nombres _YYYY-MM-DD_clip_NN y emisiones YouTube)."""
    nombre = _nombre_base_archivo_limpio(nombre_archivo)
    patron = r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})"
    match = re.search(patron, nombre)
    if match:
        slug = nombre[: match.start()].strip("_").strip()
    else:
        parts = [p for p in re.split(r"[_\s-]+", nombre) if p and not p.isdigit()]
        if len(parts) >= 2 and len(parts[0]) <= 3:
            slug = "_".join(parts[:2])
        elif parts:
            slug = parts[0]
        else:
            slug = nombre.split("_")[0] if "_" in nombre else nombre
    slug = re.sub(r"_\d+p$", "", slug, flags=re.IGNORECASE).strip()
    slug = re.sub(r"\s+\d+p\s*$", "", slug, flags=re.IGNORECASE).strip()
    return slug or "CANAL"


def extraer_medio_y_hora_legible(nombre_archivo: str) -> Tuple[str, str]:
    """Devuelve (nombre_medio, frase_hora) para el guion TTS."""
    meta = parsear_emision_desde_nombre_archivo(nombre_archivo, usar_llm_si_falta_hora=False)
    medio = meta.get("medio") or "Medio"
    if meta.get("h") is not None and meta.get("mi") is not None and meta.get("d"):
        nombre_mes = _MESES_ES[meta["mo"] - 1] if 1 <= meta["mo"] <= 12 else str(meta["mo"])
        frase = (
            f"{_formatear_hora_tts(meta['h'], meta['mi'])} "
            f"del {meta['d']} de {nombre_mes} de {meta['y']}"
        )
        return medio, frase
    return medio, meta.get("fecha_tts") or "hora no disponible en el nombre del archivo"


def extraer_fecha_emision_legible(nombre_archivo: str, mistral_api_key: str = "") -> str:
    """Fecha (y hora si está en el nombre) en español para el guion TTS."""
    meta = parsear_emision_desde_nombre_archivo(
        nombre_archivo, mistral_api_key=mistral_api_key, usar_llm_si_falta_hora=True
    )
    return meta.get("fecha_tts") or "fecha no disponible en el nombre del archivo"


def construir_texto_intro(termino: str, nombre_archivo: str, mistral_api_key: str = "") -> str:
    meta = parsear_emision_desde_nombre_archivo(
        nombre_archivo,
        mistral_api_key=mistral_api_key or _env_str("MISTRAL_API_KEY", ""),
        usar_llm_si_falta_hora=True,
    )
    medio = meta.get("medio") or "Medio"
    fecha = meta.get("fecha_tts") or "fecha no disponible en el nombre del archivo"
    term = (termino or "").strip() or "término"
    return (
        f"Coincidencia de video. "
        f"Término: {term}. "
        f"Medio: {medio}. "
        f"Fecha: {fecha}."
    )


def _variantes_slug_logo(slug: str) -> list[str]:
    """Variantes del slug para buscar logo (CDN_37_720p → CDN, cdn)."""
    out: list[str] = []
    s = (slug or "").strip()
    if not s:
        return out
    for candidato in (s, re.sub(r"_\d+p$", "", s, flags=re.IGNORECASE)):
        if candidato and candidato not in out:
            out.append(candidato)
    s2 = re.sub(r"_\d+p$", "", s, flags=re.IGNORECASE)
    s3 = re.sub(r"_\d+$", "", s2)
    for candidato in (s3, s3.split("_")[0] if "_" in s3 else ""):
        if candidato and candidato not in out:
            out.append(candidato)
    return out


def _resolver_logo_fuzzy(slug: str, base_dir: Path) -> Optional[str]:
    """Coincidencia parcial entre slug del archivo y nombre de archivo de logo."""
    sn = _norm_logo_key(slug)
    if len(sn) < 3:
        return None
    mejor: Optional[str] = None
    mejor_len = 0
    for f in base_dir.iterdir():
        if not f.is_file() or f.suffix.lower() not in _LOGO_EXTENSIONS:
            continue
        bn = _norm_logo_key(f.stem)
        if len(bn) < 3:
            continue
        if bn in sn or sn in bn or sn.startswith(bn):
            if len(bn) > mejor_len:
                mejor, mejor_len = str(f), len(bn)
    return mejor


def resolver_logo_cliente(
    cliente_id: Optional[str],
    logos_dir: Optional[Path] = None,
) -> Optional[str]:
    """Logo de la entidad (Edesur, Intrant, etc.) cuando no hay logo del canal."""
    if not cliente_id:
        return None
    base_dir = Path(logos_dir) if logos_dir else LOGOS_CANAL_DIR
    if not base_dir.is_dir():
        return None
    cid = str(cliente_id).strip().lower()
    for nombre in _CLIENTE_LOGO_FILES.get(cid, _CLIENTE_LOGO_FILES.get("default", [])):
        p = base_dir / nombre
        if p.is_file():
            return str(p)
    return None


def resolver_logo_canal(
    nombre_archivo: str,
    logos_dir: Optional[Path] = None,
    cliente_id: Optional[str] = None,
) -> Optional[str]:
    """Ruta al logo: canal → entidad/cliente → INTRO_FALLBACK_LOGO → fuzzy."""
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

    logo_cli = resolver_logo_cliente(cliente_id, logos_dir=base_dir)
    if logo_cli:
        return logo_cli

    fallback = _env_str("INTRO_FALLBACK_LOGO", "")
    if fallback:
        p = Path(fallback)
        if not p.is_file():
            p = base_dir / fallback
        if p.is_file():
            return str(p)

    return _resolver_logo_fuzzy(slug, base_dir) or _logo_fallback_cualquiera(base_dir)


def resolver_logo_medio(
    nombre_archivo: str,
    logos_dir: Optional[Path] = None,
) -> Optional[str]:
    """Logo del medio emisor del video (canal), sin fallback a entidad cliente."""
    base_dir = Path(logos_dir) if logos_dir else LOGOS_CANAL_DIR
    if not base_dir.is_dir():
        return None

    slug = extraer_slug_canal_desde_archivo(nombre_archivo)
    candidatos: list[str] = []
    for base in _variantes_slug_logo(slug):
        candidatos.extend([
            base,
            base.upper(),
            base.lower(),
            base.replace(" ", "_"),
            base.replace(" ", "_").upper(),
        ])
    visto = set()
    for nombre in candidatos:
        if not nombre or nombre in visto:
            continue
        visto.add(nombre)
        for ext in _LOGO_EXTENSIONS:
            p = base_dir / f"{nombre}{ext}"
            if p.is_file():
                return str(p)

    fallback = _env_str("INTRO_FALLBACK_LOGO", "")
    if fallback:
        p = Path(fallback)
        if not p.is_file():
            p = base_dir / fallback
        if p.is_file():
            return str(p)

    return _resolver_logo_fuzzy(slug, base_dir)


def _logo_fallback_cualquiera(base_dir: Path) -> Optional[str]:
    """Último recurso: cualquier logo en la carpeta para no omitir el prevideo."""
    if not base_dir.is_dir():
        return None
    for f in sorted(base_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in _LOGO_EXTENSIONS:
            return str(f)
    return None


def listar_voces_mistral_tts(api_key: str) -> Tuple[bool, list[dict] | str]:
    """GET /v1/audio/voices — voces preset y custom de la cuenta."""
    if not api_key:
        return False, "MISTRAL_API_KEY vacía"
    try:
        resp = requests.get(
            "https://api.mistral.ai/v1/audio/voices",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return False, f"voces HTTP {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else data
        return True, list(items or [])
    except Exception as e:
        return False, str(e)


def resolver_voice_id_mistral(api_key: str, voice_hint: Optional[str] = None) -> Tuple[bool, str]:
    """
    Mistral TTS exige voice_id UUID, no el nombre visible («mi voz»).
    Acepta UUID, nombre de voz (case-insensitive) o slug; si falla, primera voz de la cuenta.
    """
    hint = (voice_hint or _env_str("MISTRAL_TTS_VOICE_ID", MISTRAL_TTS_VOICE_ID) or "").strip()
    if not api_key:
        return False, "MISTRAL_API_KEY vacía"
    if not hint:
        return False, "MISTRAL_TTS_VOICE_ID vacío (pon el UUID de la voz en .env)"

    cache_key = f"{api_key[:8]}:{hint.lower()}"
    if cache_key in _voice_id_cache:
        return True, _voice_id_cache[cache_key]

    if _UUID_VOICE_RE.match(hint):
        _voice_id_cache[cache_key] = hint
        return True, hint

    ok, items_or_err = listar_voces_mistral_tts(api_key)
    if not ok:
        return False, str(items_or_err)

    items: list[dict] = items_or_err  # type: ignore[assignment]
    hint_low = hint.lower()

    for v in items:
        vid = (v.get("id") or "").strip()
        nombre = (v.get("name") or "").strip()
        slug = (v.get("slug") or "").strip()
        if vid and (
            vid.lower() == hint_low
            or nombre.lower() == hint_low
            or slug.lower() == hint_low
        ):
            _voice_id_cache[cache_key] = vid
            return True, vid

    for v in items:
        vid = (v.get("id") or "").strip()
        nombre = (v.get("name") or "").strip()
        if vid and hint_low in nombre.lower():
            _voice_id_cache[cache_key] = vid
            return True, vid

    if items:
        vid = (items[0].get("id") or "").strip()
        if vid:
            _voice_id_cache[cache_key] = vid
            return True, vid

    return False, (
        f"Voz Mistral «{hint}» no encontrada. Lista voces en .env como UUID "
        f"(GET /v1/audio/voices). Voces en cuenta: {len(items)}"
    )


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

    ok_voice, voice_res = resolver_voice_id_mistral(api_key, voice_id)
    if not ok_voice:
        return False, voice_res
    voice_uuid = voice_res

    payload = {
        "model": model or _env_str("MISTRAL_TTS_MODEL", MISTRAL_TTS_MODEL),
        "input": texto.strip(),
        "voice_id": voice_uuid,
        "response_format": "mp3",
    }

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


def _extraer_primer_frame(clip_path: str, salida_png: str, ffmpeg: str) -> Tuple[bool, str]:
    """Extrae el frame 0 del clip de coincidencia."""
    os.makedirs(os.path.dirname(os.path.abspath(salida_png)) or ".", exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        clip_path,
        "-vf",
        "select=eq(n\\,0)",
        "-vframes",
        "1",
        salida_png,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **_subprocess_no_window_kw(),
        )
        if os.path.isfile(salida_png) and os.path.getsize(salida_png) > 0:
            return True, salida_png
        return False, "No se generó PNG del primer frame"
    except subprocess.CalledProcessError as e:
        return False, f"ffmpeg frame: {_ffmpeg_stderr_resumen(e.stderr)}"


def _lineas_texto_preroll(
    termino: str,
    nombre_archivo: str,
    mistral_api_key: str = "",
) -> Tuple[str, str]:
    """Dos líneas para overlay: término arriba, medio abajo."""
    meta = parsear_emision_desde_nombre_archivo(
        nombre_archivo,
        mistral_api_key=mistral_api_key or _env_str("MISTRAL_API_KEY", ""),
        usar_llm_si_falta_hora=False,
    )
    linea_termino = (termino or "").strip() or "Término"
    linea_medio = meta.get("medio") or _limpiar_nombre_medio(
        extraer_slug_canal_desde_archivo(nombre_archivo)
    )
    return linea_termino, linea_medio


def _cargar_fuente_preroll(size: int, bold: bool = True):
    from PIL import ImageFont

    candidatos = []
    if bold:
        candidatos.extend(
            [
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/Arial Bold.ttf",
            ]
        )
    candidatos.extend(
        [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "arial.ttf",
            "Arial.ttf",
        ]
    )
    for path in candidatos:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _dibujar_texto_sombra(draw, xy, texto, font, fill=(255, 255, 255), sombra=(0, 0, 0)):
    x, y = xy
    for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2), (0, 3)):
        draw.text((x + dx, y + dy), texto, font=font, fill=sombra)
    draw.text((x, y), texto, font=font, fill=fill)


def _componer_frame_preroll(
    frame_png: str,
    logo_path: str,
    linea_termino: str,
    linea_medio: str,
    salida_png: str,
    width: int,
    height: int,
) -> Tuple[bool, str]:
    """Compone frame congelado + caja logo abajo-izq + texto centrado (PIL)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False, "Pillow no instalado"

    try:
        base = Image.open(frame_png).convert("RGBA")
        if base.size != (width, height):
            base = base.resize((width, height), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(base)
        w, h = width, height

        box_w = max(48, int(w * INTRO_FREEZE_LOGO_BOX_RATIO))
        margin_x = int(w * 0.03)
        margin_y = int(h * 0.12)
        box_h = box_w
        box_x = margin_x
        box_y = h - margin_y - box_h
        radius = max(6, int(box_w * 0.08))
        border = max(1, INTRO_FREEZE_LOGO_BORDER)

        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            radius=radius,
            fill=(255, 255, 255, 255),
            outline=(220, 20, 20, 255),
            width=border,
        )

        logo = Image.open(logo_path).convert("RGBA")
        pad = int(box_w * 0.12)
        inner = max(8, box_w - 2 * pad)
        logo.thumbnail((inner, inner), Image.Resampling.LANCZOS)
        lx = box_x + (box_w - logo.width) // 2
        ly = box_y + (box_h - logo.height) // 2
        base.paste(logo, (lx, ly), logo)

        fs1 = max(18, int(h * 0.065))
        fs2 = max(16, int(h * 0.055))
        font1 = _cargar_fuente_preroll(fs1, bold=True)
        font2 = _cargar_fuente_preroll(fs2, bold=True)

        gap = int(h * 0.02)
        tw1 = draw.textlength(linea_termino, font=font1)
        tw2 = draw.textlength(linea_medio, font=font2)
        block_h = fs1 + gap + fs2
        y0 = (h - block_h) // 2 - int(h * 0.05)
        x1 = (w - tw1) / 2
        x2 = (w - tw2) / 2
        _dibujar_texto_sombra(draw, (x1, y0), linea_termino, font1)
        _dibujar_texto_sombra(draw, (x2, y0 + fs1 + gap), linea_medio, font2)

        os.makedirs(os.path.dirname(os.path.abspath(salida_png)) or ".", exist_ok=True)
        base.convert("RGB").save(salida_png, format="PNG")
        return True, salida_png
    except Exception as e:
        return False, str(e)


def _componer_frame_preroll_ffmpeg(
    frame_png: str,
    logo_path: str,
    linea_termino: str,
    linea_medio: str,
    salida_png: str,
    width: int,
    height: int,
    ffmpeg: str,
) -> Tuple[bool, str]:
    """Fallback sin PIL: drawbox + overlay logo + drawtext."""
    box_w = max(48, int(width * INTRO_FREEZE_LOGO_BOX_RATIO))
    margin_x = int(width * 0.03)
    margin_y = int(height * 0.12)
    box_h = box_w
    box_x = margin_x
    box_y = height - margin_y - box_h
    fs1 = max(18, int(height * 0.065))
    fs2 = max(16, int(height * 0.055))
    gap = int(height * 0.02)
    y0 = (height - fs1 - gap - fs2) // 2 - int(height * 0.05)

    def _esc(text: str) -> str:
        return (
            (text or "")
            .replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
        )

    t1 = _esc(linea_termino)
    t2 = _esc(linea_medio)
    inner = max(8, box_w - int(box_w * 0.24))
    pad = int(box_w * 0.12)
    vf = (
        f"[0:v]scale={width}:{height}[bg];"
        f"[bg]drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:"
        f"color=white@1:t=fill[v1];"
        f"[1:v]scale={inner}:-1[lg];"
        f"[v1][lg]overlay={box_x + pad}:{box_y + pad}[v2];"
        f"[v2]drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:"
        f"color=red@1:t={max(1, INTRO_FREEZE_LOGO_BORDER)}[v3];"
        f"[v3]drawtext=text='{t1}':fontcolor=white:fontsize={fs1}:"
        f"x=(w-text_w)/2:y={y0}:shadowcolor=black:shadowx=2:shadowy=2[v4];"
        f"[v4]drawtext=text='{t2}':fontcolor=white:fontsize={fs2}:"
        f"x=(w-text_w)/2:y={y0 + fs1 + gap}:shadowcolor=black:shadowx=2:shadowy=2"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        frame_png,
        "-i",
        logo_path,
        "-filter_complex",
        vf,
        "-frames:v",
        "1",
        salida_png,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            **_subprocess_no_window_kw(),
        )
        if os.path.isfile(salida_png):
            return True, salida_png
        return False, "ffmpeg compose: sin salida PNG"
    except subprocess.CalledProcessError as e:
        return False, f"ffmpeg compose: {_ffmpeg_stderr_resumen(e.stderr)}"


def _crear_video_intro_desde_frame(
    frame_png: str,
    audio_path: str,
    salida_mp4: str,
    width: int,
    height: int,
    fps: float,
    ffmpeg: str,
    ffprobe: str,
) -> Tuple[bool, str]:
    """Video congelado desde frame compuesto + pista TTS."""
    audio_info = _probe_media(audio_path, ffprobe)
    dur = (audio_info.get("duration") or 3.0) + INTRO_AUDIO_PADDING_SEC
    vf = f"scale={width}:{height}:flags=lanczos,format=yuv420p"
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        frame_png,
        "-i",
        audio_path,
        "-t",
        str(dur),
        "-vf",
        vf,
        "-r",
        _fps_ffmpeg_val(fps),
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
        return False, f"ffmpeg intro frame: {_ffmpeg_stderr_resumen(e.stderr)}"


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
        _fps_ffmpeg_val(fps),
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
        return False, f"ffmpeg intro: {_ffmpeg_stderr_resumen(e.stderr)}"


def _ffmpeg_stderr_resumen(stderr_bytes, max_len: int = 700) -> str:
    """Últimas líneas útiles de stderr (el banner de versión no ayuda a diagnosticar)."""
    text = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
    if not text:
        return "sin stderr"
    lineas_utiles = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip()
        and not ln.strip().startswith("ffmpeg version")
        and "configuration:" not in ln
        and not ln.strip().startswith("built with")
        and not ln.strip().startswith("  lib")
    ]
    if lineas_utiles:
        res = "\n".join(lineas_utiles[-8:])
        return res[-max_len:] if len(res) > max_len else res
    return text[-max_len:] if len(text) > max_len else text


def _dim_par(n: int) -> int:
    return max(2, int(n) // 2 * 2)


def _fps_ffmpeg_val(fps: float) -> str:
    try:
        fps = float(fps or 25.0)
    except (TypeError, ValueError):
        fps = 25.0
    if fps <= 0:
        fps = 25.0
    if abs(fps - round(fps)) < 0.02:
        return str(int(round(fps)))
    return f"{fps:.3f}".rstrip("0").rstrip(".")


def _archivo_tiene_pista_audio(path: str, ffprobe: str) -> bool:
    if not ffprobe or not os.path.isfile(path):
        return False
    try:
        r = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                path,
            ],
            capture_output=True,
            text=True,
            **_subprocess_no_window_kw(),
        )
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except Exception:
        return False


def _asegurar_clip_con_audio(
    clip_mp4: str, salida_mp4: str, ffmpeg: str, ffprobe: str
) -> Tuple[bool, str]:
    """Si el clip no tiene audio, añade pista silenciosa para poder concatenar con la intro."""
    if _archivo_tiene_pista_audio(clip_mp4, ffprobe):
        try:
            shutil.copy2(clip_mp4, salida_mp4)
            return True, salida_mp4
        except OSError as e:
            return False, str(e)

    meta = _probe_media(clip_mp4, ffprobe)
    dur = meta.get("duration") or 90.0
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        clip_mp4,
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=channel_layout=stereo:sample_rate=48000:d={dur}",
        "-shortest",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
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
        return False, f"ffmpeg audio silencio: {_ffmpeg_stderr_resumen(e.stderr)}"


def _concatenar_videos(intro_mp4: str, clip_mp4: str, salida_mp4: str, ffmpeg: str, ffprobe: str = "") -> Tuple[bool, str]:
    """Concatena intro + clip normalizando resolución, fps y audio (evita fallos concat)."""
    ffprobe = ffprobe or _resolve_ffprobe()
    clip_prep = clip_mp4
    tmp_clip = None
    if not _archivo_tiene_pista_audio(clip_mp4, ffprobe):
        tmp_clip = clip_mp4 + ".con_audio_tmp.mp4"
        ok_prep, msg_prep = _asegurar_clip_con_audio(clip_mp4, tmp_clip, ffmpeg, ffprobe)
        if not ok_prep:
            return False, msg_prep
        clip_prep = tmp_clip

    meta_clip = _probe_media(clip_prep, ffprobe)
    w = _dim_par(meta_clip.get("width") or 1280)
    h = _dim_par(meta_clip.get("height") or 720)
    fps_s = _fps_ffmpeg_val(meta_clip.get("fps") or 25.0)
    vf = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps_s}[v0];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps_s}[v1];"
        f"[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        intro_mp4,
        "-i",
        clip_prep,
        "-filter_complex",
        vf,
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
        return False, f"ffmpeg concat: {_ffmpeg_stderr_resumen(e.stderr)}"
    finally:
        if tmp_clip and os.path.isfile(tmp_clip):
            try:
                os.remove(tmp_clip)
            except OSError:
                pass


def prefijar_intro_coincidencia_si(
    clip_path: str,
    termino: str,
    nombre_archivo: str,
    *,
    mistral_api_key: str = "",
    enabled: Optional[bool] = None,
    logos_dir: Optional[Path] = None,
    cliente_id: Optional[str] = None,
    log_fn: Optional[Callable[[str, str], None]] = None,
    ui_info: Optional[Callable[[str], None]] = None,
    ui_warning: Optional[Callable[[str], None]] = None,
) -> Tuple[str, bool, str]:
    """
    Si está habilitado y hay logo del medio + TTS OK, antepone preroll visual al clip.
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

    logo = resolver_logo_medio(nombre_archivo, logos_dir=logos_dir)
    if not logo:
        msg = (
            f"Sin logo del medio en {LOGOS_CANAL_DIR} para canal "
            f"'{extraer_slug_canal_desde_archivo(nombre_archivo)}'"
        )
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

    texto = construir_texto_intro(termino, nombre_archivo, mistral_api_key=mistral_api_key)
    tmpdir = tempfile.mkdtemp(prefix="clip_intro_")
    frame_raw_png = os.path.join(tmpdir, "frame_raw.png")
    frame_intro_png = os.path.join(tmpdir, "frame_intro.png")
    audio_mp3 = os.path.join(tmpdir, "intro.mp3")
    intro_mp4 = os.path.join(tmpdir, "intro.mp4")
    merged_mp4 = os.path.join(tmpdir, "merged.mp4")

    try:
        meta = _probe_media(clip_path, ffprobe)
        w, h = meta["width"], meta["height"]
        fps = meta.get("fps") or 25.0

        ok_frame, msg_frame = _extraer_primer_frame(clip_path, frame_raw_png, ffmpeg)
        if not ok_frame:
            _log(msg_frame, "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (frame): {msg_frame}")
            return clip_path, False, msg_frame

        linea_termino, linea_medio = _lineas_texto_preroll(
            termino, nombre_archivo, mistral_api_key=mistral_api_key
        )
        ok_comp, msg_comp = _componer_frame_preroll(
            frame_raw_png,
            logo,
            linea_termino,
            linea_medio,
            frame_intro_png,
            w,
            h,
        )
        if not ok_comp:
            ok_comp, msg_comp = _componer_frame_preroll_ffmpeg(
                frame_raw_png,
                logo,
                linea_termino,
                linea_medio,
                frame_intro_png,
                w,
                h,
                ffmpeg,
            )
        if not ok_comp:
            _log(msg_comp, "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (composición): {msg_comp}")
            return clip_path, False, msg_comp

        ok_tts, msg_tts = generar_audio_intro_mistral(texto, mistral_api_key, audio_mp3)
        if not ok_tts:
            _log(f"TTS falló: {msg_tts}", "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (TTS): {msg_tts}")
            return clip_path, False, msg_tts

        ok_vid, msg_vid = _crear_video_intro_desde_frame(
            frame_intro_png, audio_mp3, intro_mp4, w, h, fps, ffmpeg, ffprobe
        )
        if not ok_vid:
            _log(msg_vid, "warning")
            if ui_warning:
                ui_warning(f"⏭️ Intro omitida (video frame): {msg_vid}")
            return clip_path, False, msg_vid

        ok_cat, msg_cat = _concatenar_videos(intro_mp4, clip_path, merged_mp4, ffmpeg, ffprobe)
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

        msg_ok = f"Preroll añadido (frame + {os.path.basename(logo)})"
        _log(msg_ok, "info")
        if ui_info:
            ui_info(f"🎬 {msg_ok}")
        return clip_path, True, msg_ok
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def prefijar_intro_coincidencia_obligatorio(
    clip_path: str,
    termino: str,
    nombre_archivo: str,
    **kwargs,
) -> Tuple[str, bool, str]:
    """
    Intenta el prevideo en coincidencias (reintenta hasta INTRO_MAX_REINTENTOS, default 3).
    Si falla, el caller debe enviar la coincidencia con el clip original.
    """
    max_int = max(1, int(_env_str("INTRO_MAX_REINTENTOS", "3") or "3"))
    ultimo = ""
    path = clip_path
    for intento in range(1, max_int + 1):
        path, ok, msg = prefijar_intro_coincidencia_si(
            path,
            termino,
            nombre_archivo,
            enabled=True,
            **kwargs,
        )
        ultimo = msg
        if ok:
            return path, True, msg
        if intento < max_int:
            time.sleep(0.8)
    return path, False, f"Previo falló tras {max_int} intento(s): {ultimo}"
