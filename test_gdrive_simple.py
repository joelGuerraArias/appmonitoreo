#!/usr/bin/env python3
"""
Script de prueba simple para verificar Google Drive sin dependencias de Streamlit
"""

import os
import sys
from datetime import datetime

# Configuración de Google Drive (copiada del transmistral2.py)
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
GOOGLE_REFRESH_TOKEN = "YOUR_GOOGLE_REFRESH_TOKEN"
GOOGLE_DRIVE_FOLDER_ID = "10wJNNTmE9aO1cI98N7oKGmE-vJAUFrjg"

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
        if value and value != "None" and not value.startswith("1091234567890"):
            print(f"✅ {key}: Configurado")
        else:
            print(f"❌ {key}: No configurado o valor por defecto")
    
    return all(value and value != "None" and not value.startswith("1091234567890") for value in configs.values())

def probar_conexion_google():
    """Prueba la conexión con Google Drive usando la API"""
    print("\n🌐 PROBANDO CONEXIÓN CON GOOGLE DRIVE")
    print("=" * 50)
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        # Crear credenciales
        creds = Credentials(
            None,  # No access token inicial
            refresh_token=GOOGLE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Refrescar el token si es necesario
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        
        # Crear servicio
        service = build('drive', 'v3', credentials=creds)
        
        # Intentar listar archivos en la carpeta
        results = service.files().list(
            pageSize=1,
            q=f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents",
            fields="files(id, name)"
        ).execute()
        
        archivos = results.get('files', [])
        print(f"✅ Conexión exitosa. Archivos en carpeta: {len(archivos)}")
        return True, f"Conexión exitosa. Archivos en carpeta: {len(archivos)}"
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)[:100]}"
        print(error_msg)
        return False, error_msg

def probar_subida_archivo():
    """Prueba subiendo un archivo de texto simple"""
    print("\n📤 PROBANDO SUBIDA DE ARCHIVO")
    print("=" * 50)
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        from google.auth.transport.requests import Request
        import io
        
        # Crear credenciales
        creds = Credentials(
            None,
            refresh_token=GOOGLE_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Refrescar el token si es necesario
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        
        # Crear servicio
        service = build('drive', 'v3', credentials=creds)
        
        # Crear contenido de prueba
        contenido_prueba = f"""
# Prueba de Google Drive - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Este es un archivo de prueba para verificar que la subida a Google Drive funciona correctamente.

## Detalles de la prueba:
- Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- Sistema: Análisis de Videos Edesur
- Estado: Prueba de conectividad
"""
        
        nombre_archivo = f"prueba_gdrive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Crear metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        # Crear media para subida
        media = MediaIoBaseUpload(
            io.BytesIO(contenido_prueba.encode('utf-8')),
            mimetype='text/plain',
            resumable=True
        )
        
        print(f"📝 Subiendo archivo: {nombre_archivo}")
        
        # Subir archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        print(f"✅ Archivo subido exitosamente: {file.get('name')}")
        print(f"🔗 ID: {file.get('id')}")
        print(f"🌐 URL: {file.get('webViewLink', 'No disponible')}")
        return True
        
    except Exception as e:
        error_msg = f"❌ Error subiendo archivo: {str(e)[:100]}"
        print(error_msg)
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
        print("💡 Necesitas configurar las credenciales de Google Drive en transmistral2.py")
        return False
    
    # 2. Probar conexión
    conexion_ok, mensaje_conexion = probar_conexion_google()
    
    if not conexion_ok:
        print(f"\n❌ CONEXIÓN FALLIDA - {mensaje_conexion}")
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

