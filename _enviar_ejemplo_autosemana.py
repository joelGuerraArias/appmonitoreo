# -*- coding: utf-8 -*-
"""Envía el ejemplo de coincidencia con previo a autosemana@gmail.com."""
from __future__ import annotations

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from clip_intro import construir_texto_intro

DESTINO = "autosemana@gmail.com"
VIDEO = ROOT / "videos procesados" / "pruebas_prevideo" / "EJEMPLO_coincidencia_Intrant_morrison.mp4"
NOMBRE_EMISION = "tELECENTRO_480p_2026-05-19_07-19-19_seg000.mp4"
TERMINO = "morrison"


def _cliente_intrant() -> dict:
    cfg = json.loads((ROOT / "clientes_config.json").read_text(encoding="utf-8"))
    for c in cfg.get("clientes", []):
        if c.get("id") == "intrant":
            return c
    raise RuntimeError("Cliente intrant no encontrado en clientes_config.json")


def _subir_cloudinary(video_path: Path, termino: str) -> str:
    brevo_cli = _cliente_intrant()
    cld = brevo_cli.get("cloudinary") or {}
    cloudinary.config(
        cloud_name=cld["cloud_name"],
        api_key=cld["api_key"],
        api_secret=cld["api_secret"],
        secure=True,
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = (cld.get("folder") or "video_analyzer_clips").strip("/")
    public_id = f"{folder}/ejemplo_previo_{termino}_{ts}"
    res = cloudinary.uploader.upload(
        str(video_path),
        resource_type="video",
        public_id=public_id,
        folder=folder,
        overwrite=True,
        invalidate=True,
    )
    return res["secure_url"]


def _enviar_correo(url_video: str, guion: str) -> tuple[bool, str]:
    cliente = _cliente_intrant()
    brevo = cliente.get("brevo") or {}
    api_key = brevo.get("api_key", "")
    sender_email = brevo.get("sender_email", "")
    sender_name = brevo.get("sender_name", "FGJ Medios")
    smtp_user = brevo.get("smtp_user", sender_email)
    smtp_server = brevo.get("smtp_server", "smtp-relay.brevo.com")
    smtp_port = int(brevo.get("smtp_port") or 587)

    if not api_key or not sender_email:
        return False, "Brevo incompleto en clientes_config.json"

    html = f"""
<html><body style="font-family:Arial,sans-serif;">
<h2>🎯 Ejemplo coincidencia Intrant — prevideo</h2>
<p><strong>Término:</strong> {TERMINO}</p>
<p><strong>Medio:</strong> Telecentro</p>
<p><strong>Guion del previo (voz):</strong><br>{guion}</p>
<p><a href="{url_video}" style="font-size:18px;">▶ Ver clip con previo (Cloudinary)</a></p>
<p style="color:#666;font-size:12px;">Prueba generada por Nora / App Monitoreo — {datetime.now():%Y-%m-%d %H:%M:%S}</p>
</body></html>
"""
    texto = (
        f"Ejemplo coincidencia Intrant — término: {TERMINO}\n\n"
        f"Guion previo: {guion}\n\n"
        f"Video: {url_video}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Ejemplo coincidencia: {TERMINO} (prevideo Intrant)"
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = DESTINO
    msg.attach(MIMEText(texto, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port, timeout=60) as server:
        server.starttls()
        server.login(smtp_user, api_key)
        server.send_message(msg)
    return True, f"Enviado a {DESTINO}"


def main() -> int:
    if not VIDEO.is_file():
        print(f"FAIL: no existe {VIDEO}")
        print("Ejecuta antes: python _test_prevideo_coincidencia.py")
        return 1

    guion = construir_texto_intro(TERMINO, NOMBRE_EMISION)
    print("Subiendo a Cloudinary...")
    url = _subir_cloudinary(VIDEO, TERMINO)
    print("URL:", url)
    print("Enviando correo a", DESTINO, "...")
    ok, msg = _enviar_correo(url, guion)
    print("OK" if ok else "FAIL", msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
