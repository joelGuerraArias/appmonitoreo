import sys
import os
import logging
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock Streamlit for videoAnalizerv2 imports
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

from videoAnalizerv2 import (
    cargar_brevo_config,
    enviar_correo_brevo
)

def test_autosemana():
    print("📧 Enviando correo de prueba a autosemana@gmail.com...")
    
    # 1. Verificar configuración
    config = cargar_brevo_config()
    print(f"⚙️ Configuración Brevo: Enabled={config['enabled']}, Sender={config['sender_email']}")
    
    # 2. Datos de prueba
    termino = "PRUEBA_SISTEMA"
    resumen = "**RESUMEN EJECUTIVO:**\\nEsta es una prueba directa tras corregir el error de 'msg' no definido.\\n\\n**TRANSCRIPCIÓN:**\\nConfirmando que el sistema de correos ahora funciona correctamente."
    nombre_video = "prueba_confirmacion.mp4"
    
    # IMPORTANTE: Forzar el destinatario autosemana@gmail.com
    # Necesitamos mockear 'obtener_correos_activos' para esta prueba
    original_obtener = videoAnalizerv2.obtener_correos_activos
    videoAnalizerv2.obtener_correos_activos = lambda: ["autosemana@gmail.com"]
    
    try:
        # 3. Disparar envío
        print(f"📤 Intentando enviar correo...")
        success, msg = enviar_correo_brevo(
            termino, 
            resumen, 
            nombre_video, 
            video_path=None, 
            info_medio="Prueba de Recuperación", 
            terminos_detectados=[termino]
        )
        
        if success:
            print(f"✅ ÉXITO: {msg}")
        else:
            print(f"❌ FALLO: {msg}")
    finally:
        # Restaurar función original
        videoAnalizerv2.obtener_correos_activos = original_obtener

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_autosemana()
