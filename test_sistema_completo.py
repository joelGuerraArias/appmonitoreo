#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del sistema completo: análisis de video con envío de correo
"""

import sys
import os
from datetime import datetime

# Importar las funciones del sistema principal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transmistral2 import enviar_coincidencia_inmediata, obtener_correos_activos

def test_sistema_completo():
    """Test del sistema completo con un video real"""
    print("🎬 TEST DEL SISTEMA COMPLETO")
    print("=" * 50)
    
    # Verificar configuración
    correos = obtener_correos_activos()
    print(f"👥 Correos configurados: {len(correos)}")
    for correo in correos:
        print(f"   📧 {correo}")
    
    # Buscar un video de coincidencia real para usar como ejemplo
    video_path = None
    for root, dirs, files in os.walk('videos procesados'):
        for file in files:
            if file.endswith('.mp4') and 'clip_' in root:
                video_path = os.path.join(root, file)
                break
        if video_path:
            break
    
    if not video_path:
        print("❌ No se encontraron videos de coincidencias")
        return False
    
    print(f"🎬 Video encontrado: {video_path}")
    print(f"   Tamaño: {os.path.getsize(video_path) / (1024*1024):.1f} MB")
    
    # Simular datos de coincidencia
    nombre_archivo = "LUNA TV_720p_2025-09-19_23-20-53_seg006.mp4"
    termino_encontrado = "parientes"
    contexto_termino = "Los parientes de la menor han solicitado una audiencia especial"
    tipo_archivo = "video"
    
    # Transcripción simulada (como si viniera del análisis real)
    transcripcion_completa = """En esta parte del programa se discute sobre los parientes de la menor y las implicaciones legales del caso. El presentador menciona que "los parientes de la menor han solicitado una audiencia especial" y continúa explicando los detalles del procedimiento judicial. 

El reportero explica que este tipo de casos requiere especial atención debido a la naturaleza sensible del asunto. Se menciona que los procedimientos legales deben seguir un protocolo específico cuando se trata de menores de edad.

La cobertura incluye declaraciones de expertos legales que explican los derechos tanto de la menor como de sus parientes en este tipo de procedimientos judiciales."""
    
    print(f"\n🎯 SIMULANDO COINCIDENCIA:")
    print(f"   Término: {termino_encontrado}")
    print(f"   Contexto: {contexto_termino}")
    print(f"   Transcripción: {len(transcripcion_completa)} caracteres")
    
    try:
        print(f"\n🚀 EJECUTANDO ENVÍO DE COINCIDENCIA...")
        
        # Llamar al sistema principal
        exito, mensaje = enviar_coincidencia_inmediata(
            nombre_archivo,
            termino_encontrado,
            contexto_termino,
            tipo_archivo,
            video_path,  # Video real de coincidencia
            transcripcion_completa  # Transcripción completa
        )
        
        if exito:
            print(f"✅ SISTEMA COMPLETO EXITOSO: {mensaje}")
            return True
        else:
            print(f"❌ ERROR EN EL SISTEMA: {mensaje}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    resultado = test_sistema_completo()
    
    print("\n" + "=" * 50)
    if resultado:
        print("🎉 ¡SISTEMA COMPLETO FUNCIONANDO!")
        print("=" * 50)
        print("📬 EL CORREO DEBE INCLUIR:")
        print("   ✅ Transcripción completa del contenido")
        print("   ✅ Resumen ejecutivo generado por IA")
        print("   ✅ Player de video incrustado (URL de Cloudinary)")
        print("   ✅ Video adjunto para descarga")
        print("   ✅ Información completa del medio")
        print("   ✅ Términos detectados destacados")
        print("\n📧 REVISA TUS CORREOS:")
        print("   📧 info@fgjmedios.com")
        print("   📧 autosemana@gmail.com")
        print("\n🔍 BUSCA EL CORREO CON ASUNTO:")
        print("   '🎯 Coincidencia: parientes'")
        print("\n🎬 EL VIDEO DEBE:")
        print("   ✅ Reproducirse en el player incrustado")
        print("   ✅ Estar disponible para descarga como adjunto")
        print("   ✅ Usar la misma URL que se envió a Telegram")
    else:
        print("❌ ERROR EN EL SISTEMA")
        print("🔧 Revisa la configuración")
    
    print(f"\n🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
