import sys
import os
import json
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from videoAnalizerv2 import (
    cargar_clientes,
    enviar_coincidencia_a_cliente
)

# Mock Streamlit to avoid crashes outside Streamlit environment
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

def test_full_notification_cycle():
    print("🚀 Starting Full Notification Audit (Telegram, Email, Drive, Supabase)...")
    
    # 1. Load clients
    clientes = cargar_clientes()
    if not clientes:
        print("❌ Could not load client configuration.")
        return
    
    # Test with Intrant (usually has most channels active) or Default
    client_id = "default" # Let's test EDESUR as requested
    cliente = next((c for c in clientes if c['id'] == client_id), clientes[0])
    
    print(f"👤 Testing client: {cliente['nombre']} (ID: {cliente['id']})")
    
    # 2. Prepare mock data
    nombre_archivo = "test_audit_video.mp4"
    termino = "AUDITORIA_SISTEMA"
    contexto = "Este es un mensaje de prueba para auditar todos los canales de notificación: Telegram, Email, Drive y Supabase."
    tipo_archivo = "video"
    clip_path = "small_test_video.mp4" # Non-existent file is handled by functions
    transcripcion = "Esta es la transcripción completa de la prueba de auditoría. Verificando que el sistema envíe a todos los destinos."
    video_url = "https://res.cloudinary.com/demo/video/upload/v1234567/sample.mp4"
    transcripcion_segmento = "auditar todos los canales de notificación"
    
    # Create dummy clip if it doesn't exist to test file-based logic (Drive/Telegram)
    dummy_clip = "test_audit_clip.txt"
    with open(dummy_clip, "w") as f:
        f.write("Dummy clip content for audit.")
    
    try:
        # 3. Trigger dispatch
        print(f"📤 Dispatching notifications for '{termino}'...")
        # enviar_coincidencia_a_cliente(cliente, nombre_archivo, termino_encontrado, contexto_termino, tipo_archivo, clip_path=None, transcripcion_completa="", timestamp=None, idea_general=None, video_url=None, video_path=None, transcripcion_segmento="")
        
        # Note: videoAnalizerv2 uses streamlit 'st' occasionally, we might need to mock it if running bare
        # But most functions check if they are in streamlit.
        
        exito, resultados = enviar_coincidencia_a_cliente(
            cliente=cliente,
            nombre_archivo=nombre_archivo,
            termino_encontrado=termino,
            contexto_termino=contexto,
            tipo_archivo=tipo_archivo,
            clip_path=dummy_clip,
            transcripcion_completa=transcripcion,
            video_url=video_url,
            transcripcion_segmento=transcripcion_segmento
        )
        
        print("\n📊 --- NOTIFICATION RESULTS ---")
        # results in videoAnalizerv2.py are stored in 'resultados' dict if I saw correctly
        # Wait, the function might not return the dict, let's check its return value.
        
    finally:
        if os.path.exists(dummy_clip):
            os.remove(dummy_clip)

if __name__ == "__main__":
    # Setup basic logging to see what's happening
    logging.basicConfig(level=logging.INFO)
    test_full_notification_cycle()
