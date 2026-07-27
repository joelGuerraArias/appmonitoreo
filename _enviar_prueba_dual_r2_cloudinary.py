# -*- coding: utf-8 -*-
"""Sube un clip a Cloudinary y R2; envía correo con ambas URLs solo a autosemana@gmail.com."""
from __future__ import annotations

import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv()

import appMonitoreo as V  # noqa: E402

DESTINO = "autosemana@gmail.com"
CANDIDATOS = [
    os.path.join(ROOT, "_test_dual_cdn_clip.mp4"),
    os.path.join(ROOT, "ccAUDITORIA_SISTEMA_test_20260224_135112.mp4"),
]


def main() -> int:
    video = next((p for p in CANDIDATOS if os.path.isfile(p)), None)
    if not video:
        print("No hay vídeo de prueba. Genera _test_dual_cdn_clip.mp4 (ffmpeg) o coloca un .mp4 en la raíz.")
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    termino = "prueba_dual_cdn"

    print("Subiendo a Cloudinary...", video)
    url_c, msg_c = V.subir_video_cloudinary(video, termino, ts)
    if not url_c:
        print("Cloudinary:", msg_c)
        return 2
    print("Cloudinary OK:", url_c[:80] + "...")

    cld = V.cargar_cloudinary_config()
    r2_cfg = {"enabled": True, "folder": (cld.get("folder") or "video_analyzer_clips").strip()}
    print("Subiendo a R2...")
    url_r, msg_r = V.subir_video_r2(
        video, termino, r2_cfg, timestamp=ts, func_name="prueba_dual_r2_cld"
    )
    if not url_r:
        print("R2:", msg_r)
        return 3
    print("R2 OK:", url_r[:80] + "...")

    b = V.cargar_brevo_config()
    cliente = {
        "nombre": "Prueba R2 + Cloudinary",
        "brevo": {
            "enabled": bool(b.get("enabled")),
            "api_key": b.get("api_key", ""),
            "smtp_user": b.get("smtp_user") or b.get("sender_email", ""),
            "smtp_server": b.get("smtp_server", "smtp-relay.brevo.com"),
            "smtp_port": int(b.get("smtp_port", 587)),
            "sender_email": b.get("sender_email", ""),
            "sender_name": b.get("sender_name", "FGJ Medios"),
            "correos_destinatarios": [DESTINO],
        },
    }

    resumen = (
        "**RESUMEN EJECUTIVO:**\n"
        "Correo de prueba: el mismo clip está en Cloudinary (reproductor principal) "
        "y en Cloudflare R2 (copia).\n\n"
        "**TRANSCRIPCIÓN DEL CONTENIDO:**\n"
        "(No aplica — mensaje generado automáticamente.)\n"
    )

    print(f"Enviando correo a {DESTINO}...")
    ok, msg = V.enviar_brevo_cliente(
        cliente,
        termino,
        resumen,
        os.path.basename(video),
        video_path=None,
        info_medio="Prueba dual CDN (automático)",
        terminos_detectados=[termino, "R2", "Cloudinary"],
        video_url=url_c,
        transcripcion_segmento="",
        video_url_r2=url_r,
    )
    print("Correo:", "OK" if ok else "FALLO", msg)
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
