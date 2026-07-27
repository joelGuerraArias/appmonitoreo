import sys
import os
import json
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from videoAnalizerv2 import (
    cargar_clientes,
    enviar_supabase_cliente
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

def test_supabase_adaptive():
    print("🗄️ Starting Targeted Supabase Adaptive Test...")
    
    # 1. Load clients
    clientes = cargar_clientes()
    if not clientes:
        print("❌ Could not load client configuration.")
        return
    
    # Test with 'default' client (edesur)
    client_id = "default" 
    cliente = next((c for c in clientes if c['id'] == client_id), clientes[0])
    
    print(f"👤 Testing client: {cliente['nombre']} (ID: {cliente['id']})")
    print(f"🗄️ Target Table: {cliente.get('supabase', {}).get('tabla_nombre')}")
    
    # 2. Prepare mock data
    coincidencias_items = [
        {'termino': 'AUDITORIA_SUPABASE', 'contexto': 'Prueba de inserción adaptativa para auditoría.'}
    ]
    archivo_test = "test_audit_supabase.mp4"
    url_video = "https://res.cloudinary.com/demo/video/upload/v1234567/sample.mp4"
    enlace_directo = "https://drive.google.com/test_link_audit"
    
    # 3. Trigger Supabase dispatch
    print(f"📤 Inserting into Supabase...")
    success, msg = enviar_supabase_cliente(
        cliente, 
        coincidencias_items, 
        archivo_test, 
        "video", 
        "Resumen de auditoría Supabase", 
        "Transcripción de auditoría Supabase", 
        url_video, 
        enlace_directo
    )
    
    if success:
        print(f"✅ SUPABASE SUCCESS: {msg}")
    else:
        print(f"❌ SUPABASE FAILURE: {msg}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_supabase_adaptive()
