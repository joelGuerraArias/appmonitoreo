#!/usr/bin/env python3
"""
Script simple para probar las funciones de extracción de información
"""

import re
import os
from datetime import datetime

def extraer_info_del_nombre_archivo(nombre_archivo):
    """
    Extrae información del medio, fecha y hora del nombre del archivo
    """
    # Limpiar nombre del archivo (quitar extensión)
    nombre_limpio = os.path.splitext(nombre_archivo)[0]
    
    # Patrones para extraer información
    patrones_fecha_hora = [
        # Patrón: YYYY-MM-DD_HH-MM-SS
        r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})',
        # Patrón: YYYYMMDD_HHMMSS
        r'(\d{8})_(\d{6})',
        # Patrón: DD-MM-YYYY_HH-MM-SS
        r'(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{2})',
    ]
    
    # Buscar fecha y hora
    fecha_programa = None
    hora_programa = None
    
    for patron in patrones_fecha_hora:
        match = re.search(patron, nombre_limpio)
        if match:
            try:
                if patron == patrones_fecha_hora[0]:  # YYYY-MM-DD_HH-MM-SS
                    fecha_str = match.group(1)
                    hora_str = match.group(2).replace('-', ':')
                    fecha_programa = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    hora_programa = datetime.strptime(hora_str, '%H:%M:%S').time()
                elif patron == patrones_fecha_hora[1]:  # YYYYMMDD_HHMMSS
                    fecha_str = match.group(1)
                    hora_str = match.group(2)
                    fecha_programa = datetime.strptime(fecha_str, '%Y%m%d').date()
                    hora_programa = datetime.strptime(hora_str, '%H%M%S').time()
                elif patron == patrones_fecha_hora[2]:  # DD-MM-YYYY_HH-MM-SS
                    fecha_str = match.group(1)
                    hora_str = match.group(2).replace('-', ':')
                    fecha_programa = datetime.strptime(fecha_str, '%d-%m-%Y').date()
                    hora_programa = datetime.strptime(hora_str, '%H:%M:%S').time()
                break
            except ValueError:
                continue
    
    # Extraer nombre del medio
    nombre_medio = "Medio de Comunicación"  # Valor por defecto
    
    # Buscar patrones conocidos de medios
    medios_conocidos = [
        "Parnorama TV", "CDN CANAL 37", "Show del Mediodia", "Politikal", 
        "Canal 4", "Teleantillas", "Telesistema", "Color Vision",
        "CNN", "Fox News", "BBC", "Al Jazeera", "RT", "France 24"
    ]
    
    for medio in medios_conocidos:
        if medio.lower() in nombre_limpio.lower():
            nombre_medio = medio
            break
    else:
        # Si no encuentra un medio conocido, usar la primera parte del nombre
        partes = re.split(r'[_\-\.]', nombre_limpio)
        if partes:
            nombre_medio = partes[0].strip()
    
    return nombre_medio, fecha_programa, hora_programa

def crear_fecha_detencion(fecha_programa, hora_programa):
    """
    Crea la fecha_detencion combinando fecha_programa y hora_programa,
    o usa la hora actual si no están disponibles
    """
    from datetime import datetime, date, time
    
    try:
        if fecha_programa and hora_programa:
            # Combinar fecha y hora del programa
            fecha_detencion = datetime.combine(fecha_programa, hora_programa)
            return fecha_detencion.isoformat()
        elif fecha_programa:
            # Solo fecha del programa, usar hora actual
            ahora = datetime.now()
            fecha_detencion = datetime.combine(fecha_programa, ahora.time())
            return fecha_detencion.isoformat()
        else:
            # No hay información del programa, usar hora actual
            return datetime.now().isoformat()
    except Exception as e:
        # En caso de error, usar hora actual
        return datetime.now().isoformat()

def test_extraer_info():
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

if __name__ == "__main__":
    print("🧪 PRUEBAS DE EXTRACCIÓN DE INFORMACIÓN")
    print("=" * 60)
    test_extraer_info()
    print("\n" + "=" * 60)
    print("🎉 ¡Pruebas completadas!")