#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del correo con video incrustado
"""

import sys
import os
from datetime import datetime

# Importar las funciones del sistema principal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transmistral2 import (
    enviar_correo_brevo, 
    cargar_brevo_config, 
    obtener_correos_activos,
    configurar_cloudinary,
    subir_video_cloudinary
)

def test_correo_con_video():
    """Test de correo con video real"""
    print("🎬 PROBANDO CORREO CON VIDEO INCRUSTADO")
    print("=" * 55)
    
    # Cargar configuración
    config = cargar_brevo_config()
    correos = obtener_correos_activos()
    
    print(f"👥 Enviando a {len(correos)} destinatarios:")
    for correo in correos:
        print(f"   📧 {correo}")
    
    # Buscar un video de coincidencia real
    video_path = None
    videos_procesados = "videos procesados"
    
    # Buscar clips de coincidencias
    for root, dirs, files in os.walk(videos_procesados):
        for file in files:
            if file.endswith('.mp4') and 'clip_' in root:
                video_path = os.path.join(root, file)
                break
        if video_path:
            break
    
    if not video_path:
        print("❌ No se encontraron videos de coincidencias para probar")
        print(f"   Buscando en: {videos_procesados}")
        return False
    
    print(f"🎬 Video encontrado: {video_path}")
    print(f"   Tamaño: {os.path.getsize(video_path) / (1024*1024):.1f} MB")
    
    # Probar Cloudinary primero
    print("\n☁️ PROBANDO CLOUDINARY...")
    try:
        configurado = configurar_cloudinary()
        print(f"   Configurado: {configurado}")
        
        if configurado:
            video_url, mensaje = subir_video_cloudinary(video_path, "PRUEBA")
            if video_url:
                print(f"   ✅ Video subido: {video_url}")
            else:
                print(f"   ❌ Error: {mensaje}")
        else:
            print("   ❌ Cloudinary no configurado")
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
    
    # Datos de prueba
    termino_encontrado = "PRUEBA_VIDEO"
    terminos_detectados = ["PRUEBA", "VIDEO", "CORREO"]
    info_medio = "Sistema de Pruebas - Video Real de Coincidencia"
    
    resumen_completo = f"""**PRUEBA DE CORREO CON VIDEO REAL**

**OBJETIVO:** Verificar que el correo incluya correctamente el video de coincidencia tanto incrustado como adjunto.

**VIDEO DE PRUEBA:**
- Archivo: {os.path.basename(video_path)}
- Ruta: {video_path}
- Tamaño: {os.path.getsize(video_path) / (1024*1024):.1f} MB
- Existe: {os.path.exists(video_path)}

**FUNCIONALIDADES A VERIFICAR:**
1. **Video en Cloudinary:** URL para player incrustado
2. **Video adjunto:** Archivo completo en el correo
3. **Player HTML:** Controles personalizados funcionando
4. **Información completa:** Resumen, medio, términos

**RESULTADO ESPERADO:**
- ✅ Correo con player HTML funcional
- ✅ Video descargable como adjunto
- ✅ Información completa de la coincidencia
- ✅ Diseño profesional y moderno

**FECHA DE PRUEBA:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        print(f"\n📤 ENVIANDO CORREO CON VIDEO...")
        print(f"   🎯 Término: {termino_encontrado}")
        print(f"   🎬 Video: {video_path}")
        print(f"   📧 Destinatarios: {len(correos)}")
        
        # Enviar correo usando el sistema principal
        exito, mensaje = enviar_correo_brevo(
            termino_encontrado,
            resumen_completo,
            os.path.basename(video_path),
            video_path,  # Esta es la clave - pasar el video_path
            info_medio,
            terminos_detectados
        )
        
        if exito:
            print("   ✅ CORREO ENVIADO EXITOSAMENTE")
            return True
        else:
            print(f"   ❌ ERROR: {mensaje}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    resultado = test_correo_con_video()
    
    print("\n" + "=" * 55)
    if resultado:
        print("🎉 ¡CORREO CON VIDEO ENVIADO!")
        print("=" * 55)
        print("📬 REVISA TUS CORREOS:")
        print("   📧 info@fgjmedios.com")
        print("   📧 autosemana@gmail.com")
        print("\n🎬 VERIFICA EN EL CORREO:")
        print("   ✅ Player de video incrustado funcionando")
        print("   ✅ Video adjunto descargable")
        print("   ✅ Información completa de la coincidencia")
        print("   ✅ Diseño profesional del correo")
        print("\n📧 BUSCA EL CORREO CON ASUNTO:")
        print("   '🎯 Coincidencia: PRUEBA_VIDEO'")
        print("\n🚀 ¡El sistema de correos con video está funcionando!")
    else:
        print("❌ ERROR EN EL ENVÍO")
        print("🔧 Revisa los logs para más detalles")
    
    print(f"\n🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
