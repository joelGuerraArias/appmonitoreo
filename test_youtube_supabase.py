#!/usr/bin/env python3
"""
Script para probar el envío de datos de videos de YouTube a Supabase
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from transmistral2 import extraer_info_del_nombre_archivo, crear_fecha_detencion, enviar_coincidencias_a_supabase

def test_extraer_info_archivo():
    """Prueba la extracción de información del nombre del archivo"""
    print("🧪 Probando extracción de información del nombre del archivo...")
    
    casos_prueba = [
        "Parnorama TV_720p_2025-09-26_13-55-11_seg049.mp4",
        "CDN CANAL 37_720p_2025-09-26_22-39-50_seg001.mp4",
        "Show_del_Mediodia_20250926_115901.mp4",
        "Politikal 26 Septiembre.mp4",
        "youtube_video_20250927.mp4",
        "CNN_News_20250927_143022.mp4"
    ]
    
    for archivo in casos_prueba:
        print(f"\n📁 Archivo: {archivo}")
        nombre_medio, fecha_programa, hora_programa = extraer_info_del_nombre_archivo(archivo)
        print(f"   Medio: {nombre_medio}")
        print(f"   Fecha programa: {fecha_programa}")
        print(f"   Hora programa: {hora_programa}")
        
        fecha_detencion = crear_fecha_detencion(fecha_programa, hora_programa)
        print(f"   Fecha detención: {fecha_detencion}")

def test_crear_fecha_detencion():
    """Prueba la creación de fecha_detencion"""
    print("\n🧪 Probando creación de fecha_detencion...")
    
    from datetime import date, time
    
    casos_prueba = [
        (date(2025, 9, 26), time(13, 55, 11)),  # Fecha y hora completas
        (date(2025, 9, 26), None),              # Solo fecha
        (None, time(13, 55, 11)),               # Solo hora
        (None, None)                            # Sin información
    ]
    
    for i, (fecha, hora) in enumerate(casos_prueba, 1):
        print(f"\n   Caso {i}: Fecha={fecha}, Hora={hora}")
        fecha_detencion = crear_fecha_detencion(fecha, hora)
        print(f"   Resultado: {fecha_detencion}")

def test_enviar_coincidencias_youtube():
    """Prueba el envío de coincidencias para un video de YouTube"""
    print("\n🧪 Probando envío de coincidencias para video de YouTube...")
    
    # Simular datos de coincidencia de YouTube
    coincidencias_items = [
        {
            'termino': 'edesur',
            'texto': 'Se reportan cortes de energía en diferentes zonas de la ciudad debido a problemas con EDESUR.'
        }
    ]
    
    nombre_archivo = "youtube_video_20250927.mp4"
    tipo_archivo = "video"
    resumen_archivo = "Video de YouTube descargado que contiene información sobre cortes de energía."
    transcripcion_completa = "Transcripción completa del video de YouTube sobre problemas eléctricos."
    url_video = "https://res.cloudinary.com/test/video/upload/test_video.mp4"
    enlace_directo = "https://drive.google.com/file/d/1234567890/view"
    
    print(f"📝 Datos de prueba:")
    print(f"   Archivo: {nombre_archivo}")
    print(f"   URL Cloudinary: {url_video}")
    print(f"   URL Drive: {enlace_directo}")
    print(f"   Coincidencias: {len(coincidencias_items)}")
    
    # Probar envío a Supabase
    try:
        success, message = enviar_coincidencias_a_supabase(
            coincidencias_items, nombre_archivo, tipo_archivo, 
            resumen_archivo, transcripcion_completa, url_video, enlace_directo
        )
        
        print(f"\n📤 Resultado del envío:")
        print(f"   Éxito: {success}")
        print(f"   Mensaje: {message}")
        
    except Exception as e:
        print(f"❌ Error en el envío: {str(e)}")

if __name__ == "__main__":
    print("🧪 PRUEBAS DE INTEGRACIÓN - VIDEOS DE YOUTUBE Y SUPABASE")
    print("=" * 80)
    
    # Ejecutar pruebas
    test_extraer_info_archivo()
    test_crear_fecha_detencion()
    test_enviar_coincidencias_youtube()
    
    print("\n" + "=" * 80)
    print("🎉 ¡Pruebas completadas!")


