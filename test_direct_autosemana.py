import sys
import os
import json
import logging
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from videoAnalizerv2 import (
    cargar_clientes,
    crear_plantilla_email_html
)

def test_email_autosemana_direct():
    print("📧 Starting DIRECT Email Test for autosemana@gmail.com...")
    
    # 1. Load clients to get credentials
    clientes = cargar_clientes()
    cliente = next((c for c in clientes if c['id'] == 'default'), clientes[0])
    
    brevo_config = cliente.get('brevo', {})
    api_key = brevo_config.get('api_key', '')
    smtp_user = brevo_config.get('smtp_user', '')
    smtp_server = brevo_config.get('smtp_server', 'smtp-relay.brevo.com')
    smtp_port = brevo_config.get('smtp_port', 587)
    sender_email = brevo_config.get('sender_email', 'info@fgjmedios.com')
    sender_name = brevo_config.get('sender_name', 'FGJ Medios')
    
    recipient = "autosemana@gmail.com"
    print(f"👤 Target: {recipient}")
    
    # 2. Prepare mock data
    termino = "TEST_DIRECT_AUTOSEMANA"
    resumen = "Esta es una prueba directa para verificar la recepción del correo en autosemana@gmail.com."
    nombre_video = "audit_autosemana.mp4"
    video_url = "https://res.cloudinary.com/demo/video/upload/v1234567/sample.mp4"
    
    try:
        # Crear mensaje con TO EXPLÍCITO
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚀 PRUEBA DIRECTA: {termino}"
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = recipient
        
        html_content = crear_plantilla_email_html(
            termino, resumen, nombre_video, 
            "Canal Auditoría", [termino], video_url,
            transcripcion_segmento="Segmento de prueba para autosemana"
        )
        
        msg.attach(MIMEText(resumen, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        print(f"📤 Connecting to {smtp_server}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, api_key)
            server.send_message(msg)
        
        print(f"✅ SUCCESS: Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"❌ FAILURE: {e}")
        return False

if __name__ == "__main__":
    test_email_autosemana_direct()
