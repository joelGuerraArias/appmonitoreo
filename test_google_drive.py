#!/usr/bin/env python3
"""
Script de prueba para verificar el estado de Google Drive
y las alertas en el sistema de análisis de videos
"""

import os
import sys
import json
from datetime import datetime

# Agregar el directorio actual al path para importar transmistral2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from transmistral2 import (
        test_google_drive_connection,
        crear_servicio_google_drive,
        subir_texto_google_drive,
        GOOGLE_DRIVE_FOLDER_ID,
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        GOOGLE_REFRESH_TOKEN
    )
    print("✅ Módulos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

def verificar_configuracion():
    """Verifica que las credenciales estén configuradas"""
    print("\n🔍 VERIFICANDO CONFIGURACIÓN DE GOOGLE DRIVE")
    print("=" * 50)
    
    configs = {
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "GOOGLE_REFRESH_TOKEN": GOOGLE_REFRESH_TOKEN,
        "GOOGLE_DRIVE_FOLDER_ID": GOOGLE_DRIVE_FOLDER_ID
    }
    
    for key, value in configs.items():
        if value and value != "None":
            print(f"✅ {key}: Configurado")
        else:
            print(f"❌ {key}: No configurado")
    
    return all(value and value != "None" for value in configs.values())

def probar_conexion():
    """Prueba la conexión con Google Drive"""
    print("\n🌐 PROBANDO CONEXIÓN CON GOOGLE DRIVE")
    print("=" * 50)
    
    try:
        exito, mensaje = test_google_drive_connection()
        if exito:
            print(f"✅ {mensaje}")
            return True
        else:
            print(f"❌ {mensaje}")
            return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def probar_subida_archivo():
    """Prueba subiendo un archivo de texto simple"""
    print("\n📤 PROBANDO SUBIDA DE ARCHIVO")
    print("=" * 50)
    
    try:
        # Crear archivo de prueba
        contenido_prueba = f"""
# Prueba de Google Drive - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Este es un archivo de prueba para verificar que la subida a Google Drive funciona correctamente.

## Detalles de la prueba:
- Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- Sistema: Análisis de Videos Edesur
- Estado: Prueba de conectividad
"""
        
        nombre_archivo = f"prueba_gdrive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        print(f"📝 Creando archivo de prueba: {nombre_archivo}")
        resultado, mensaje = subir_texto_google_drive(
            contenido_prueba, 
            nombre_archivo, 
            'text/plain'
        )
        
        if resultado:
            print(f"✅ Archivo subido exitosamente: {resultado.get('name')}")
            print(f"🔗 ID: {resultado.get('id')}")
            print(f"🌐 URL: {resultado.get('webViewLink', 'No disponible')}")
            return True
        else:
            print(f"❌ Error subiendo archivo: {mensaje}")
            return False
            
    except Exception as e:
        print(f"❌ Error inesperado en subida: {e}")
        return False

def verificar_logs():
    """Verifica si hay logs de errores recientes"""
    print("\n📋 VERIFICANDO LOGS DE ERRORES")
    print("=" * 50)
    
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        print("⚠️ Directorio de logs no encontrado")
        return
    
    archivos_log = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
    archivos_log.sort(reverse=True)
    
    print(f"📁 Encontrados {len(archivos_log)} archivos de log")
    
    # Revisar los 3 logs más recientes
    for i, archivo in enumerate(archivos_log[:3]):
        ruta_log = os.path.join(logs_dir, archivo)
        print(f"\n📄 {archivo}:")
        
        try:
            with open(ruta_log, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
                # Buscar errores relacionados con Google Drive
                errores_gdrive = [linea for linea in lineas if 'google' in linea.lower() and 'error' in linea.lower()]
                
                if errores_gdrive:
                    print(f"   ⚠️ {len(errores_gdrive)} errores relacionados con Google Drive encontrados")
                    for error in errores_gdrive[-3:]:  # Mostrar los últimos 3 errores
                        print(f"      {error.strip()}")
                else:
                    print("   ✅ No se encontraron errores relacionados con Google Drive")
                    
        except Exception as e:
            print(f"   ❌ Error leyendo log: {e}")

def main():
    """Función principal de prueba"""
    print("🧪 PRUEBA COMPLETA DE GOOGLE DRIVE")
    print("=" * 60)
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Verificar configuración
    config_ok = verificar_configuracion()
    
    if not config_ok:
        print("\n❌ CONFIGURACIÓN INCOMPLETA - No se puede continuar")
        return False
    
    # 2. Probar conexión
    conexion_ok = probar_conexion()
    
    if not conexion_ok:
        print("\n❌ CONEXIÓN FALLIDA - Revisar credenciales")
        return False
    
    # 3. Probar subida de archivo
    subida_ok = probar_subida_archivo()
    
    # 4. Verificar logs
    verificar_logs()
    
    # Resumen final
    print("\n📊 RESUMEN DE PRUEBAS")
    print("=" * 50)
    print(f"✅ Configuración: {'OK' if config_ok else 'FALLO'}")
    print(f"✅ Conexión: {'OK' if conexion_ok else 'FALLO'}")
    print(f"✅ Subida: {'OK' if subida_ok else 'FALLO'}")
    
    if config_ok and conexion_ok and subida_ok:
        print("\n🎉 TODAS LAS PRUEBAS EXITOSAS - Google Drive funcionando correctamente")
        return True
    else:
        print("\n⚠️ ALGUNAS PRUEBAS FALLARON - Revisar configuración y logs")
        return False

if __name__ == "__main__":
    try:
        resultado = main()
        sys.exit(0 if resultado else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Prueba interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

