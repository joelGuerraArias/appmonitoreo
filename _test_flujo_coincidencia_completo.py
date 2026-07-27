# -*- coding: utf-8 -*-
"""
Prueba E2E: preroll + subida real Cloudinary/R2 + envío Presidencia.
Ejecutar: python _test_flujo_coincidencia_completo.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Mock Streamlit antes de importar appMonitoreo
class _MockSt:
    def markdown(self, *a, **k):
        print(f"  [UI] {a[0][:120] if a else ''}")

    def caption(self, msg):
        print(f"  [cap] {msg}")

    def divider(self):
        pass

    def spinner(self, msg=""):
        class _S:
            def __enter__(self):
                print(f"  [spin] {msg}")
                return self

            def __exit__(self, *a):
                pass

        return _S()

    def success(self, msg):
        print(f"  ✅ {msg}")

    def warning(self, msg):
        print(f"  ⚠️ {msg}")

    def error(self, msg):
        print(f"  ❌ {msg}")

    def info(self, msg):
        print(f"  ℹ️ {msg}")

    def expander(self, label, expanded=False):
        class _E:
            def __enter__(self):
                print(f"  [exp] {label}")
                return self

            def __exit__(self, *a):
                pass

            def markdown(self, *a, **k):
                pass

            def caption(self, *a, **k):
                pass

        return _E()


import streamlit as st  # noqa: E402

class _SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


_mock = _MockSt()
st.markdown = _mock.markdown
st.caption = _mock.caption
st.divider = _mock.divider
st.spinner = _mock.spinner
st.success = _mock.success
st.warning = _mock.warning
st.error = _mock.error
st.info = _mock.info
st.expander = _mock.expander
st.set_page_config = lambda **kwargs: None
st.session_state = _SessionState()
st.session_state.coincidencias_enviadas_supabase = set()

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from clip_intro import _resolve_ffmpeg, prefijar_intro_coincidencia_obligatorio


def _make_clip(path: str, seconds: float = 8.0) -> bool:
    ff = _resolve_ffmpeg()
    if not ff:
        print("FAIL: sin ffmpeg")
        return False
    subprocess.run(
        [
            ff, "-y",
            "-f", "lavfi", "-i", f"color=c=0x224488:s=1280x720:d={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            path,
        ],
        check=True,
        capture_output=True,
    )
    return os.path.isfile(path) and os.path.getsize(path) > 5000


def main() -> int:
    print("=" * 60)
    print("PRUEBA FLUJO COMPLETO — coincidencia PRM / Presidencia")
    print("=" * 60)

    # Import pesado después del mock
    from appMonitoreo import (
        enviar_coincidencia_inmediata,
        obtener_cliente_por_id,
        _correos_destinatarios_cliente,
    )

    cliente = obtener_cliente_por_id("presidencia")
    if not cliente:
        clientes = cargar_clientes()
        cliente = next((c for c in clientes if c.get("id") == "presidencia"), None)
    if not cliente:
        print("FAIL: cliente Presidencia no encontrado en clientes_config.json")
        return 1

    print(f"Cliente: {cliente.get('nombre')}")
    print(f"Correos: {', '.join(_correos_destinatarios_cliente(cliente))}")
    print(f"Supabase: enabled={((cliente.get('supabase') or {}).get('enabled'))} "
          f"tabla={(cliente.get('supabase') or {}).get('tabla_nombre')}")
    print(f"Telegram: enabled={((cliente.get('telegram') or {}).get('enabled'))}")

    tmp = tempfile.mkdtemp(prefix="flujo_test_")
    nombre_emision = "CDN_37_720p_2026-06-22_16-48-47_seg002.mp4"
    clip = os.path.join(tmp, "20260622_test_prm_0m29s.mp4")
    termino = "prm"
    # Timestamp único para no chocar con dedupe de pruebas anteriores
    ts_unico = round(time.time() % 3600 + 29.7, 1)
    contexto = (
        f"PRUEBA FLUJO {datetime.now().strftime('%Y%m%d_%H%M%S')}: "
        "El PRM es presentado como partido unido que rechaza divisiones internas."
    )

    try:
        print("\n--- 1) Crear clip de prueba ---")
        if not _make_clip(clip, 15.0):
            return 1
        print(f"OK clip: {clip} ({os.path.getsize(clip)} bytes)")

        print("\n--- 2) Preroll (frame + logo CDN + TTS) ---")
        api_key = os.getenv("MISTRAL_API_KEY", "")
        clip_final, ok_intro, msg_intro = prefijar_intro_coincidencia_obligatorio(
            clip,
            termino,
            nombre_emision,
            mistral_api_key=api_key,
            cliente_id="presidencia",
            log_fn=lambda m, lvl="info": print(f"  [{lvl}] {m}"),
        )
        print(f"Preroll: ok={ok_intro} | {msg_intro}")
        if ok_intro:
            print(f"Clip con preroll: {os.path.getsize(clip_final)} bytes")

        print("\n--- 3) Subida real + envío (Cloudinary, R2, Telegram, correo, Supabase) ---")
        print("  (usa enviar_coincidencia_inmediata — igual que producción, sin URLs fake)")

        exito, mensaje, url_cloud, url_r2 = enviar_coincidencia_inmediata(
            nombre_archivo=nombre_emision,
            termino_encontrado=termino,
            contexto_termino=contexto,
            tipo_archivo="video",
            clip_path=clip_final,
            transcripcion_completa="Transcripción de prueba del segmento PRM para auditoría del flujo completo.",
            timestamp=ts_unico,
            idea_general=contexto,
            transcripcion_segmento=contexto,
        )

        print(f"\n--- URLs REALES ---")
        print(f"  Cloudinary: {url_cloud or '(no subió)'}")
        print(f"  R2:         {url_r2 or '(no subió)'}")
        print(f"\n--- ENVÍO ---")
        print(f"  {'✅' if exito else '❌'} {mensaje}")

        if url_cloud:
            import requests
            r = requests.head(url_cloud, timeout=15, allow_redirects=True)
            print(f"  Cloudinary HTTP: {r.status_code}")
        if url_r2:
            import requests
            r2 = requests.head(url_r2, timeout=15, allow_redirects=True)
            print(f"  R2 HTTP: {r2.status_code}")

        return 0 if exito else 3

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
