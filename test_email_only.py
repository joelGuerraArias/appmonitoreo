import sys
import os
import json
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from videoAnalizerv2 import (
    cargar_clientes,
    enviar_brevo_cliente
)

# Mock Streamlit
class MockSt:
    def markdown(self, *args, **kwargs): pass
    def spinner(self, *args, **kwargs):
        class Spinner:
            def __enter__(self): pass
            def __exit__(self, *args): pass
        return Spinner()
    def success(self, msg): print(f"✅ ST SUCCESS: {msg}")
    def warning(self, msg): print(f"⚠️ ST WARNING: {msg}")
    def error(self, msg): print(f"❌ ST ERROR: {msg}")
    def info(self, msg): print(f"ℹ️ ST INFO: {msg}")

import videoAnalizerv2
videoAnalizerv2.st = MockSt()

def test_email_only():
    print("📧 Starting Targeted Email Test...")
    
    # 1. Load clients
    clientes = cargar_clientes()
    if not clientes:
        print("❌ Could not load client configuration.")
        return
    
    client_id = "default" 
    cliente = next((c for c in clientes if c['id'] == client_id), clientes[0])
    
    print(f"👤 Testing client: {cliente['nombre']} (ID: {cliente['id']})")
    
    # 2. Prepare mock data
    termino = "TEST_EMAIL_AUDIT"
    resumen = "**RESUMEN EJECUTIVO:**\nEste es un resumen de prueba para auditar el correo.\n\n**TRANSCRIPCIÓN DEL CONTENIDO:**\nEsta es la transcripción de prueba."
    nombre_video = "test_video.mp4"
    video_url = "https://res.cloudinary.com/demo/video/upload/v1234567/sample.mp4"
    
    # 3. Trigger email dispatch
    print(f"📤 Sending email to {cliente['brevo']['correos_destinatarios']}...")
    success, msg = enviar_brevo_cliente(
        cliente, 
        termino, 
        resumen, 
        nombre_video, 
        info_medio="Canal de Prueba", 
        terminos_detectados=[termino], 
        video_url=video_url,
        transcripcion_segmento="transcripción de prueba"
    )
    
    if success:
        print(f"✅ EMAIL SUCCESS: {msg}")
    else:
        print(f"❌ EMAIL FAILURE: {msg}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_email_only()
