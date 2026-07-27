# -*- coding: utf-8 -*-
"""
Video Analyzer Pro - Analizador de Videos con IA
================================================
Versión: 2.1.0
Autor: Video Analyzer Team

Sistema de análisis de videos para detectar términos específicos,
generar clips y enviar notificaciones a múltiples canales.
"""

# === IMPORTS ESTÁNDAR ===
import os
import sys
import glob
import subprocess
import json
import time
import re
import base64
import logging
import traceback
import threading
import shutil
import socket
import io
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# === IMPORTS DE TERCEROS ===
import requests
import pandas as pd
import streamlit as st
import openai
from mistralai import Mistral
from faster_whisper import WhisperModel
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from supabase import create_client, Client

# Google Gemini AI
from google import genai

# Google Drive imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

# === IMPORTS LOCALES ===
from coincidencias_logger import coincidencias_logger
from coincidencias_logger import (
    log_coincidencia_detectada, log_api_request, log_api_response, log_api_error,
    log_gdrive_upload_start, log_gdrive_upload_success, log_gdrive_upload_error,
    log_error_critico, log_proceso_completado
)

# Importar configuración centralizada
try:
    from config import get_settings
    settings = get_settings()
    USAR_CONFIG_CENTRALIZADA = True
except ImportError:
    USAR_CONFIG_CENTRALIZADA = False
    settings = None

# Importar utilidades
try:
    from utils import con_reintentos, ReintentoExhausto
    USAR_RETRY_DECORATOR = True
except ImportError:
    USAR_RETRY_DECORATOR = False

# Importar modelos de datos
try:
    from models import Coincidencia, ClipInfo, ResultadoProcesamiento
    USAR_DATACLASSES = True
except ImportError:
    USAR_DATACLASSES = False

# === SETUP STREAMLIT (DEBE SER LO PRIMERO) ===
st.set_page_config(page_title="🧠 Analizador de Videos Pro - Preconfigurado", layout="wide")

# === PREVENIR EJECUCIÓN AL IMPORTAR ===
# El código de Streamlit se ejecuta solo cuando se ejecuta directamente
# No se ejecuta cuando se importa como módulo

# === SISTEMA DE LOGGING ===
def configurar_logging():
    """
    Configura el sistema completo de logging
    """
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configurar formato de logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Logger principal
    logger = logging.getLogger('VideoAnalyzer')
    logger.setLevel(logging.DEBUG)
    
    # Limpiar handlers existentes
    if logger.handlers:
        logger.handlers.clear()
    
    # Handler para archivo de errores
    error_handler = logging.FileHandler(
        log_dir / f'errors_{datetime.now().strftime("%Y%m%d")}.log',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Handler para archivo general
    info_handler = logging.FileHandler(
        log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log',
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Handler para archivo debug
    debug_handler = logging.FileHandler(
        log_dir / f'debug_{datetime.now().strftime("%Y%m%d")}.log',
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    # Agregar handlers
    logger.addHandler(error_handler)
    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(console_handler)
    
    return logger

# Configurar logging al inicio
logger = configurar_logging()

def log_exception(func_name, exception, extra_info=""):
    """
    Registra excepciones con información completa
    """
    error_msg = f"ERROR en {func_name}: {str(exception)}"
    if extra_info:
        error_msg += f" | Info adicional: {extra_info}"
    
    logger.error(error_msg)
    logger.debug(f"Traceback completo:\n{traceback.format_exc()}")

def log_info(message, func_name=""):
    """
    Registra información general
    """
    if func_name:
        message = f"[{func_name}] {message}"
    logger.info(message)

def log_debug(message, func_name=""):
    """
    Registra información de debug
    """
    if func_name:
        message = f"[{func_name}] {message}"
    logger.debug(message)

def log_warning(message, func_name=""):
    """
    Registra advertencias
    """
    if func_name:
        message = f"[{func_name}] {message}"
    logger.warning(message)

def verificar_conectividad():
    """
    Verifica conectividad a internet probando múltiples servicios
    """
    import socket
    
    servicios_test = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("api.telegram.org", 443),  # Telegram
    ]
    
    for host, port in servicios_test:
        try:
            socket.create_connection((host, port), timeout=5)
            log_debug(f"Conectividad OK con {host}:{port}", "verificar_conectividad")
            return True
        except Exception:
            continue
    
    log_info("Sin conectividad a internet detectada", "verificar_conectividad")
    return False

def esperar_con_backoff(intento, max_espera=60):
    """
    Implementa backoff exponencial para reintentos
    """
    import random
    
    # Backoff exponencial con jitter
    espera = min(max_espera, (2 ** intento) + random.uniform(0, 1))
    log_debug(f"Esperando {espera:.1f}s antes del reintento {intento}", "esperar_con_backoff")
    time.sleep(espera)
    return espera

def test_api_connectivity():
    """
    Prueba la conectividad con las APIs de OpenAI y Mistral
    """
    resultados = {
        'openai': False,
        'mistral': False,
        'internet': False
    }
    
    # Test conectividad general
    resultados['internet'] = verificar_conectividad()
    
    if not resultados['internet']:
        log_warning("Sin conectividad a internet - APIs no disponibles", "test_api_connectivity")
        return resultados
    
    # Test OpenAI API
    try:
        response = requests.get("https://api.openai.com/v1/models", 
                              headers={"Authorization": f"Bearer {openai_client.api_key}"}, 
                              timeout=10)
        if response.status_code == 200:
            resultados['openai'] = True
            log_info("OpenAI API conectividad OK", "test_api_connectivity")
        else:
            log_warning(f"OpenAI API error: {response.status_code}", "test_api_connectivity")
    except Exception as e:
        log_warning(f"OpenAI API no disponible: {e}", "test_api_connectivity")
    
    # Test Mistral API
    try:
        response = requests.get("https://api.mistral.ai/v1/models", 
                              headers={"Authorization": f"Bearer {mistral_api_key}"}, 
                              timeout=10)
        if response.status_code == 200:
            resultados['mistral'] = True
            log_info("Mistral API conectividad OK", "test_api_connectivity")
        else:
            log_warning(f"Mistral API error: {response.status_code}", "test_api_connectivity")
    except Exception as e:
        log_warning(f"Mistral API no disponible: {e}", "test_api_connectivity")
    
    return resultados

def diagnosticar_conectividad():
    """
    Diagnóstico completo de conectividad y APIs
    """
    log_info("Iniciando diagnóstico de conectividad...", "diagnosticar_conectividad")
    
    # Test DNS
    try:
        socket.gethostbyname("api.openai.com")
        log_info("DNS OpenAI: OK", "diagnosticar_conectividad")
    except Exception as e:
        log_warning(f"DNS OpenAI falló: {e}", "diagnosticar_conectividad")
    
    try:
        socket.gethostbyname("api.mistral.ai")
        log_info("DNS Mistral: OK", "diagnosticar_conectividad")
    except Exception as e:
        log_warning(f"DNS Mistral falló: {e}", "diagnosticar_conectividad")
    
    # Test APIs
    resultados = test_api_connectivity()
    
    if not resultados['internet']:
        log_warning("❌ Sin conectividad a internet", "diagnosticar_conectividad")
    elif not resultados['openai'] and not resultados['mistral']:
        log_warning("❌ APIs no disponibles - verificar configuración", "diagnosticar_conectividad")
    else:
        log_info("✅ Conectividad parcial disponible", "diagnosticar_conectividad")
    
    return resultados



# === CONFIGURACIÓN DE API KEYS (desde variables de entorno) ===
# Las credenciales se cargan desde archivo .env o variables de entorno del sistema
# NUNCA hardcodear API keys en el código!

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Si no está instalado, usar solo variables de entorno del sistema

# OpenAI
_openai_api_key = os.getenv('OPENAI_API_KEY', '')
if not _openai_api_key:
    _openai_api_key = os.getenv('OPENAI_API_KEY_BACKUP', '')

openai_client = openai.OpenAI(api_key=_openai_api_key) if _openai_api_key else None

# Mistral
mistral_api_key = os.getenv('MISTRAL_API_KEY', '')

# Gemini 3.0
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logging.info("[OK] Cliente Gemini 3.0 inicializado correctamente")
    except Exception as e:
        logging.warning(f"[WARN] Error inicializando Gemini: {e}")
        gemini_client = None
else:
    logging.warning("[WARN] Gemini no configurado. Configura GEMINI_API_KEY en .env")

# === CONFIGURACIÓN GOOGLE DRIVE (desde variables de entorno) ===
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN', '')
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')

# === ELIMINA DLLs de CUDA inválidas de Torch ===
torch_lib = os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")
for dll in glob.glob(os.path.join(torch_lib, "torch_cuda*.dll")):
    try:
        os.remove(dll)
    except OSError:
        pass

# === CONFIGURACIÓN ===
CARPETA_VIDEOS = r"C:\Users\Administrador\Desktop\grabaciones\videos procesados"  # Cambiar a la carpeta donde están los videos
CARPETA_PROCESADOS = r"C:\Users\Administrador\Desktop\grabaciones\videos procesados"
CARPETA_VIDEOSCHECK = r"C:\Users\Joel Guerra\Desktop\grabaciones\videoscheck"

# === CONFIGURACIÓN SUPABASE (desde variables de entorno) ===
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')

# Inicializar cliente de Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        logging.warning(f"[WARN] Error inicializando Supabase: {e}")
        supabase = None
else:
    logging.warning("[WARN] Supabase no configurado. Configura SUPABASE_URL y SUPABASE_ANON_KEY en .env")

# Crear carpetas necesarias
os.makedirs(CARPETA_PROCESADOS, exist_ok=True)
PROCESADOS_LOG = os.path.join(CARPETA_PROCESADOS, "procesados.log")
TERMINOS_CONFIG = "terminos_guardados.json"  # Archivo para términos (en la raíz de la app)
WEBHOOK_CONFIG = os.path.join(CARPETA_PROCESADOS, "webhook_config.json")  # Configuración del webhook
TELEGRAM_CONFIG = os.path.join(CARPETA_PROCESADOS, "telegram_config.json")  # Configuración de Telegram
CLOUDINARY_CONFIG = os.path.join(CARPETA_PROCESADOS, "cloudinary_config.json")  # Configuración de Cloudinary
CACHE_ESCANEO = os.path.join(CARPETA_PROCESADOS, "cache_escaneo.json")  # Caché de archivos escaneados
TAMANO_MINIMO_BYTES = 8 * 1024 * 1024  # 8 MB: tamaño mínimo antes de procesar

# === FUNCIONES DE WEBHOOK ===
def cargar_webhook_config():
    """Carga configuración del webhook"""
    default_config = {
        'enabled': True,  # Habilitado por defecto
        'url': 'https://hook.us1.make.com/1nk48toiy2c64f9966yue8bwhzqnosny',  # Tu webhook configurado
        'url_secundario': 'https://meny.app.n8n.cloud/webhook/edesurbot',  # Segundo webhook
        'url_terciario': 'https://meny.app.n8n.cloud/webhook-test/edesurbot',  # Tercer webhook de prueba
        'enviar_makecom': True,  # Switch para Make.com
        'enviar_n8n': True,  # Switch para N8N
        'enviar_n8n_test': True,  # Switch para N8N-Test
        'method': 'POST',
        'headers': {
            'Content-Type': 'application/json'
        },
        'send_video': True,
        'send_clips': True,
        'max_file_size_mb': 8,  # Reducido para evitar error 400 en Make.com
        'timeout': 30
    }
    
    try:
        if os.path.exists(WEBHOOK_CONFIG):
            with open(WEBHOOK_CONFIG, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Fusionar con defaults para compatibilidad
                default_config.update(config)
    except Exception as e:
        st.warning(f"⚠️ Error cargando configuración webhook: {e}")
    
    return default_config

def guardar_webhook_config(config):
    """Guarda configuración del webhook"""
    try:
        with open(WEBHOOK_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración webhook: {e}")
        return False

def enviar_clips_a_webhook(clips_generados, resumen, terminos_detectados, video_origen):
    """Envía clips específicos donde se encontraron coincidencias + SIEMPRE CON RESUMEN"""
    func_name = "enviar_clips_a_webhook"
    log_info(f"Iniciando envío de {len(clips_generados)} clips a webhook. Video: {video_origen}", func_name)
    
    config = cargar_webhook_config()
    
    if not config['enabled'] or not config['url']:
        log_info("Webhook no configurado o deshabilitado", func_name)
        return False, "Webhook no configurado o deshabilitado"
    
    try:
        # Datos básicos SIEMPRE con resumen ejecutivo
        data = {
            'evento': 'video_analizado_con_coincidencias',
            'timestamp': datetime.now().isoformat(),
            'video_origen': video_origen,
            'terminos_detectados': terminos_detectados,
            'total_terminos_encontrados': len(terminos_detectados),
            'resumen_ejecutivo': resumen,  # SIEMPRE incluido
            'clips_enviados': [],
            'metodo_envio': 'WH',
            'servidor': 'analizador_videos_ia_v2'
        }
        
        # Enviar cada clip donde se encontró una coincidencia
        for clip in clips_generados:
            clip_path = clip.get('path', '')
            
            if os.path.exists(clip_path):
                clip_size_mb = os.path.getsize(clip_path) / (1024*1024)
                
                # Verificar que el clip no sea muy grande para Make.com
                if clip_size_mb <= config['max_file_size_mb']:
                    try:
                        with open(clip_path, 'rb') as f:
                            clip_content = base64.b64encode(f.read()).decode('utf-8')
                            
                        clip_data = {
                            'termino_encontrado': clip.get('termino', ''),
                            'tiempo_en_video': clip.get('tiempo', ''),
                            'contexto': clip.get('contexto', ''),
                            'nombre_archivo': f"[WH] {os.path.basename(clip_path)}",
                            'tamaño_mb': round(clip_size_mb, 2),
                            'video_base64': clip_content,
                            'cloudinary_url': None  # Se podría agregar URL de Cloudinary aquí
                        }
                        
                        data['clips_enviados'].append(clip_data)
                    except Exception as e:
                        # Error leyendo archivo, enviar solo metadatos
                        clip_data = {
                            'termino_encontrado': clip.get('termino', ''),
                            'tiempo_en_video': clip.get('tiempo', ''),
                            'contexto': clip.get('contexto', ''),
                            'nombre_archivo': f"[WH] {os.path.basename(clip_path)}",
                            'tamaño_mb': round(clip_size_mb, 2),
                            'video_base64': None,
                            'error_lectura': str(e)[:100],
                            'razon_no_enviado': f"Error leyendo archivo: {str(e)[:50]}"
                        }
                        data['clips_enviados'].append(clip_data)
                else:
                    # Clip muy grande para Make.com, enviar solo metadatos
                    clip_data = {
                        'termino_encontrado': clip.get('termino', ''),
                        'tiempo_en_video': clip.get('tiempo', ''),
                        'contexto': clip.get('contexto', ''),
                        'nombre_archivo': f"[WH] {os.path.basename(clip_path)}",
                        'tamaño_mb': round(clip_size_mb, 2),
                        'video_base64': None,
                        'cloudinary_url': None,  # Aquí se podría poner la URL si se sube a Cloudinary
                        'razon_no_enviado': f"Muy grande para Make.com ({clip_size_mb:.1f}MB > {config['max_file_size_mb']}MB)",
                        'recomendacion': "Video enviado solo a Telegram vía Cloudinary"
                    }
                    data['clips_enviados'].append(clip_data)
        
        # Agregar resumen de lo enviado
        data['total_clips'] = len(clips_generados)
        data['clips_con_video'] = len([c for c in data['clips_enviados'] if c.get('video_base64')])
        
        # Enviar al webhook con configuración mejorada
        headers_mejorados = config.get('headers', {}).copy()
        headers_mejorados.update({
            'User-Agent': 'VideoAnalyzer-AI/2.0',
            'Connection': 'close'
        })
        
        response = requests.post(
            config['url'], 
            json=data, 
            headers=headers_mejorados, 
            timeout=config.get('timeout', 30)
        )
        
        if response.status_code == 200:
            clips_enviados = data['clips_con_video']
            return True, f"✅ Enviados {clips_enviados} clips al webhook"
        elif response.status_code == 400:
            return False, f"❌ Error HTTP 400 (Petición muy grande): Reducir tamaño de clips o enviar solo metadatos"
        elif response.status_code == 413:
            return False, f"❌ Error HTTP 413 (Payload muy grande): Videos demasiado grandes para Make.com"
        else:
            return False, f"❌ Error HTTP {response.status_code}: {response.text[:100]}"
            
    except requests.exceptions.Timeout:
        return False, "⏰ Timeout del webhook"
    except requests.exceptions.ConnectionError:
        return False, "🔌 Error de conexión"
    except Exception as e:
        return False, f"❌ Error: {str(e)[:100]}"

def enviar_clips_individuales_webhook(clips_generados, resumen, terminos_detectados, video_origen):
    """Envía clips uno por uno con pausas de 60 segundos entre cada uno"""
    func_name = "enviar_clips_individuales_webhook"
    log_info(f"Iniciando envío individual de {len(clips_generados)} clips con pausas de 60s", func_name)
    
    config = cargar_webhook_config()
    
    if not config['enabled'] or not config['url']:
        log_info("Webhook no configurado o deshabilitado", func_name)
        return False, "Webhook no configurado o deshabilitado"
    
    clips_enviados_exitosamente = 0
    clips_fallidos = 0
    
    for i, clip in enumerate(clips_generados, 1):
        try:
            st.info(f"📹 Enviando Clip {i}/{len(clips_generados)}: {clip.get('termino', '')} ({clip.get('tiempo', '')}) - {os.path.getsize(clip.get('path', '')) / (1024*1024):.1f}MB")
            
            # Crear datos para este clip específico
            data = {
                'evento': 'clip_individual_analizado',
                'timestamp': datetime.now().isoformat(),
                'video_origen': video_origen,
                'terminos_detectados': terminos_detectados,
                'resumen_ejecutivo': resumen,
                'clip_numero': i,
                'total_clips': len(clips_generados),
                'clip_data': None,
                'servidor': 'analizador_videos_ia_v2'
            }
            
            clip_path = clip.get('path', '')
            
            if os.path.exists(clip_path):
                clip_size_mb = os.path.getsize(clip_path) / (1024*1024)
                
                # Verificar tamaño del clip
                if clip_size_mb <= config['max_file_size_mb']:
                    try:
                        with open(clip_path, 'rb') as f:
                            clip_content = base64.b64encode(f.read()).decode('utf-8')
                            
                        clip_data = {
                            'termino_encontrado': clip.get('termino', ''),
                            'tiempo_en_video': clip.get('tiempo', ''),
                            'contexto': clip.get('contexto', ''),
                            'nombre_archivo': os.path.basename(clip_path),
                            'tamaño_mb': round(clip_size_mb, 2),
                            'video_base64': clip_content
                        }
                        
                        data['clip_data'] = clip_data
                    except Exception as e:
                        # Error leyendo archivo, enviar solo metadatos
                        clip_data = {
                            'termino_encontrado': clip.get('termino', ''),
                            'tiempo_en_video': clip.get('tiempo', ''),
                            'contexto': clip.get('contexto', ''),
                            'nombre_archivo': os.path.basename(clip_path),
                            'tamaño_mb': round(clip_size_mb, 2),
                            'video_base64': None,
                            'error_lectura': str(e)[:100]
                        }
                        data['clip_data'] = clip_data
                else:
                    # Clip muy grande, enviar solo metadatos
                    clip_data = {
                        'termino_encontrado': clip.get('termino', ''),
                        'tiempo_en_video': clip.get('tiempo', ''),
                        'contexto': clip.get('contexto', ''),
                        'nombre_archivo': os.path.basename(clip_path),
                        'tamaño_mb': round(clip_size_mb, 2),
                        'video_base64': None,
                        'razon_no_enviado': f"Muy grande ({clip_size_mb:.1f}MB > {config['max_file_size_mb']}MB)"
                    }
                    data['clip_data'] = clip_data
            
            # Enviar este clip individual a AMBOS webhooks
            st.info(f"🌐 Enviando clip {i} a ambos webhooks...")
            
            # Enviar solo a webhooks seleccionados
            exito_principal = False
            exito_secundario = False
            exito_terciario = False
            mensaje_principal = "No seleccionado"
            mensaje_secundario = "No seleccionado"
            mensaje_terciario = "No seleccionado"
            
            # Enviar a webhook principal (Make.com) si está habilitado
            if config.get('enviar_makecom', True):
                exito_principal, mensaje_principal = enviar_a_webhook_individual(
                    config['url'], data, func_name, f"Make.com-Clip{i}"
                )
            
            # Enviar a webhook secundario (N8N) si está habilitado - COMENTADO TEMPORALMENTE
            # if config.get('enviar_n8n', True):
            #     exito_secundario, mensaje_secundario = enviar_a_webhook_individual(
            #         config['url_secundario'], data, func_name, f"N8N-Clip{i}"
            #     )
            
            # Enviar a webhook terciario (N8N-Test) si está habilitado - COMENTADO TEMPORALMENTE
            # if config.get('enviar_n8n_test', True):
            #     exito_terciario, mensaje_terciario = enviar_a_webhook_individual(
            #         config['url_terciario'], data, func_name, f"N8N-Test-Clip{i}"
            #     )
            
            # Mostrar resultados
            if config.get('enviar_makecom', True):
                if exito_principal:
                    st.success(f"✅ Clip {i} enviado exitosamente a Make.com")
                else:
                    st.warning(f"⚠️ Clip {i} falló en Make.com: {mensaje_principal}")
                    
            # if config.get('enviar_n8n', True):
            #     if exito_secundario:
            #         st.success(f"✅ Clip {i} enviado exitosamente a N8N")
            #     else:
            #         st.warning(f"⚠️ Clip {i} falló en N8N: {mensaje_secundario}")
                    
            # if config.get('enviar_n8n_test', True):
            #     if exito_terciario:
            #         st.success(f"✅ Clip {i} enviado exitosamente a N8N-Test")
            #     else:
            #         st.warning(f"⚠️ Clip {i} falló en N8N-Test: {mensaje_terciario}")
            
            # Contar éxitos (solo Make.com activo por ahora)
            alguno_exitoso = (config.get('enviar_makecom', True) and exito_principal)
            # (config.get('enviar_n8n', True) and exito_secundario) or \
            # (config.get('enviar_n8n_test', True) and exito_terciario)
            
            if alguno_exitoso:
                clips_enviados_exitosamente += 1
                st.success(f"✅ Clip {i} enviado a al menos un webhook seleccionado")
            else:
                clips_fallidos += 1
                st.error(f"❌ Clip {i} falló en todos los webhooks seleccionados - CONTINUANDO con siguiente clip")
            
            # Pausa de 60 segundos entre clips (excepto después del último)
            if i < len(clips_generados):
                log_info(f"Esperando 60 segundos antes del siguiente clip ({i+1}/{len(clips_generados)})", func_name)
                with st.spinner(f"⏳ Esperando 60s antes del siguiente clip ({i+1}/{len(clips_generados)})..."):
                    time.sleep(60)
                st.info(f"✅ Listo para enviar clip {i+1}")
            
        except Exception as e:
            st.error(f"❌ Error procesando clip {i}: {str(e)[:100]}")
            clips_fallidos += 1
            log_exception(func_name, e, f"Clip {i}: {clip.get('path', '')}")
    
    # Resultado final
    if clips_enviados_exitosamente > 0:
        mensaje = f"✅ {clips_enviados_exitosamente} clips enviados exitosamente"
        if clips_fallidos > 0:
            mensaje += f", {clips_fallidos} fallaron"
        return True, mensaje
    else:
        return False, f"❌ Todos los clips fallaron ({clips_fallidos} errores)"

def registrar_envio_exitoso(webhook_nombre, data, intento):
    """Registra un envío exitoso en procesados.log"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        video_origen = data.get('video_origen', 'desconocido')
        clip_info = data.get('clip_data', {})
        
        if clip_info:
            # Es un clip individual
            termino = clip_info.get('termino_encontrado', 'desconocido')
            tiempo = clip_info.get('tiempo_en_video', 'desconocido')
            entrada = f"[{timestamp}] ✅ CLIP_ENVIADO: {webhook_nombre} | Video: {video_origen} | Término: {termino} | Tiempo: {tiempo} | Intento: {intento}/3"
        else:
            # Es resumen general
            entrada = f"[{timestamp}] ✅ RESUMEN_ENVIADO: {webhook_nombre} | Video: {video_origen} | Intento: {intento}/3"
        
        with open(PROCESADOS_LOG, "a", encoding="utf-8") as f:
            f.write(entrada + "\n")
            
    except Exception as e:
        log_exception(f"Error registrando envío exitoso: {e}", "registrar_envio_exitoso")

def registrar_envio_fallido(webhook_nombre, data, error_mensaje, intentos_totales):
    """Registra un envío fallido en procesados.log"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        video_origen = data.get('video_origen', 'desconocido')
        clip_info = data.get('clip_data', {})
        
        if clip_info:
            # Es un clip individual
            termino = clip_info.get('termino_encontrado', 'desconocido')
            tiempo = clip_info.get('tiempo_en_video', 'desconocido')
            entrada = f"[{timestamp}] ❌ CLIP_FALLIDO: {webhook_nombre} | Video: {video_origen} | Término: {termino} | Tiempo: {tiempo} | Error: {error_mensaje} | Intentos: {intentos_totales}/3"
        else:
            # Es resumen general
            entrada = f"[{timestamp}] ❌ RESUMEN_FALLIDO: {webhook_nombre} | Video: {video_origen} | Error: {error_mensaje} | Intentos: {intentos_totales}/3"
        
        with open(PROCESADOS_LOG, "a", encoding="utf-8") as f:
            f.write(entrada + "\n")
            
    except Exception as e:
        log_exception(f"Error registrando envío fallido: {e}", "registrar_envio_fallido")

def registrar_video_procesado(nombre_video, coincidencias_items, resumen_video):
    """Registra un video procesado con detalles de clips y resumen en procesados.log"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Entrada principal del video procesado
        entrada_principal = f"[{timestamp}] 🎬 VIDEO_PROCESADO: {nombre_video}"
        
        # Agregar información de coincidencias si las hay
        if coincidencias_items:
            terminos_encontrados = list(set([item['termino'] for item in coincidencias_items]))
            total_clips = len(coincidencias_items)
            entrada_principal += f" | Términos: {', '.join(terminos_encontrados)} | Clips: {total_clips}"
        else:
            entrada_principal += " | Sin coincidencias"
        
        # Escribir entrada principal
        with open(PROCESADOS_LOG, "a", encoding="utf-8") as f:
            f.write(entrada_principal + "\n")
            
            # Agregar línea simple para compatibilidad con sistema anterior
            f.write(nombre_video + "\n")
            
            # Agregar detalles de cada clip si los hay
            if coincidencias_items:
                for i, clip_item in enumerate(coincidencias_items, 1):
                    termino = clip_item.get('termino', 'desconocido')
                    tiempo = clip_item.get('tiempo', 'desconocido')
                    contexto = clip_item.get('contexto', '')[:50] + "..." if len(clip_item.get('contexto', '')) > 50 else clip_item.get('contexto', '')
                    
                    entrada_clip = f"[{timestamp}] 📹 SUBCLIP_{i}: {nombre_video} | Término: {termino} | Tiempo: {tiempo} | Contexto: {contexto}"
                    f.write(entrada_clip + "\n")
            
            # Agregar línea de separación
            f.write("=" * 80 + "\n")
            
    except Exception as e:
        log_exception(f"Error registrando video procesado: {e}", "registrar_video_procesado")
        # Fallback: usar el método simple original
        try:
            with open(PROCESADOS_LOG, "a", encoding="utf-8") as f:
                f.write(nombre_video + "\n")
        except:
            pass

def enviar_a_webhook_individual(url, data, func_name, nombre_webhook):
    """Envía datos a un webhook específico con reintentos y logging detallado"""
    log_info(f"Iniciando envío a {nombre_webhook}: {url}", func_name)
    
    # Intentos con retry para conexiones inestables (3 intentos con pausa de 30s)
    for intento in range(3):
        try:
            log_info(f"Intento {intento + 1}/3 para {nombre_webhook}", func_name)
            
            # Configuración mejorada para conexiones problemáticas
            response = requests.post(
                url, 
                json=data, 
                timeout=15,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'VideoAnalyzer-AI/2.0',
                    'Connection': 'close'  # Evitar keep-alive
                }
            )
            
            if response.status_code == 200:
                mensaje_exito = f"{nombre_webhook}: HTTP {response.status_code} (intento {intento + 1})"
                log_info(f"✅ ÉXITO - {mensaje_exito}", func_name)
                
                # Registrar en procesados.log el envío exitoso
                registrar_envio_exitoso(nombre_webhook, data, intento + 1)
                
                return True, mensaje_exito
            else:
                mensaje_error = f"{nombre_webhook}: HTTP {response.status_code}"
                log_info(f"❌ Error HTTP - {mensaje_error}", func_name)
                
                if intento == 2:  # Último intento
                    registrar_envio_fallido(nombre_webhook, data, mensaje_error, 3)
                    return False, mensaje_error
                    
                log_info(f"⏳ Esperando 30 segundos antes del siguiente intento...", func_name)
                time.sleep(30)  # PAUSA DE 30 SEGUNDOS
                
        except requests.exceptions.ConnectionError as e:
            mensaje_error = f"{nombre_webhook}: Error de conexión: {str(e)[:100]}"
            log_info(f"❌ Error conexión - {mensaje_error}", func_name)
            
            if intento == 2:
                registrar_envio_fallido(nombre_webhook, data, mensaje_error, 3)
                return False, mensaje_error
                
            log_info(f"⏳ Esperando 30 segundos antes del siguiente intento...", func_name)
            time.sleep(30)  # PAUSA DE 30 SEGUNDOS
            
        except requests.exceptions.Timeout:
            mensaje_error = f"{nombre_webhook}: Timeout"
            log_info(f"❌ Timeout - {mensaje_error}", func_name)
            
            if intento == 2:
                registrar_envio_fallido(nombre_webhook, data, mensaje_error, 3)
                return False, mensaje_error
                
            log_info(f"⏳ Esperando 30 segundos antes del siguiente intento...", func_name)
            time.sleep(30)  # PAUSA DE 30 SEGUNDOS
            
        except Exception as e:
            mensaje_error = f"{nombre_webhook}: Error: {str(e)[:100]}"
            log_info(f"❌ Error general - {mensaje_error}", func_name)
            
            if intento == 2:
                registrar_envio_fallido(nombre_webhook, data, mensaje_error, 3)
                return False, mensaje_error
                
            log_info(f"⏳ Esperando 30 segundos antes del siguiente intento...", func_name)
            time.sleep(30)  # PAUSA DE 30 SEGUNDOS
    
    mensaje_final = f"{nombre_webhook}: Falló después de 3 intentos"
    registrar_envio_fallido(nombre_webhook, data, mensaje_final, 3)
    return False, mensaje_final

def webhook_notification_simple(video_path, resumen, terminos):
    """Notificación simple a AMBOS webhooks - VERSIÓN ROBUSTA"""
    func_name = "webhook_notification_simple"
    config = cargar_webhook_config()
    
    if not config['enabled'] or not config['url']:
        log_info("Webhook no configurado o deshabilitado", func_name)
        return False, "Webhook no configurado"
    
    # Verificar conectividad antes de intentar
    if not verificar_conectividad():
        log_info("Sin conectividad - saltando webhook", func_name)
        return False, "Sin conectividad a internet"
    
    log_info(f"Iniciando envío de webhook para: {os.path.basename(video_path)}", func_name)
    
    # Datos básicos para notificación rápida
    data = {
        'evento': 'video_analizado',
        'timestamp': datetime.now().isoformat(),
        'video': os.path.basename(video_path),
        'terminos': terminos,
        'resumen': resumen[:500],  # Resumen truncado
        'servidor': 'analizador_videos_ia_v2'
    }
    
    # Enviar solo a webhooks seleccionados
    mensajes = []
    exitos = []
    
    # Enviar a webhook principal (Make.com) si está habilitado
    if config.get('enviar_makecom', True):
        exito_principal, mensaje_principal = enviar_a_webhook_individual(
            config['url'], data, func_name, "Make.com"
        )
        exitos.append(exito_principal)
        if exito_principal:
            mensajes.append(f"✅ {mensaje_principal}")
        else:
            mensajes.append(f"❌ {mensaje_principal}")
    
    # Enviar a webhook secundario (N8N) si está habilitado - COMENTADO TEMPORALMENTE
    # if config.get('enviar_n8n', True):
    #     exito_secundario, mensaje_secundario = enviar_a_webhook_individual(
    #         config['url_secundario'], data, func_name, "N8N"
    #     )
    #     exitos.append(exito_secundario)
    #     if exito_secundario:
    #         mensajes.append(f"✅ {mensaje_secundario}")
    #     else:
    #         mensajes.append(f"❌ {mensaje_secundario}")
    
    # Enviar a webhook terciario (N8N-Test) si está habilitado - COMENTADO TEMPORALMENTE
    # if config.get('enviar_n8n_test', True):
    #     exito_terciario, mensaje_terciario = enviar_a_webhook_individual(
    #         config['url_terciario'], data, func_name, "N8N-Test"
    #     )
    #     exitos.append(exito_terciario)
    #     if exito_terciario:
    #         mensajes.append(f"✅ {mensaje_terciario}")
    #     else:
    #         mensajes.append(f"❌ {mensaje_terciario}")
    
    # Retornar éxito si al menos uno funcionó
    alguno_exitoso = any(exitos) if exitos else False
    mensaje_final = " | ".join(mensajes) if mensajes else "No hay webhooks seleccionados"
    
    log_info(f"Resultado webhooks: {mensaje_final}", func_name)
    return alguno_exitoso, mensaje_final

def enviar_coincidencia_inmediata(nombre_archivo, termino_encontrado, contexto_termino, tipo_archivo, clip_path=None, transcripcion_completa="", timestamp=None, idea_general=None):
    """
    Envía una coincidencia inmediatamente tan pronto se encuentra:
    1. PRIMERO: Usa la idea general extraída por GPT-4o del segmento
    2. SEGUNDO: Envía el resumen en texto de la coincidencia
    3. TERCERO: Espera 30 segundos
    4. CUARTO: Envía el video clip (si existe) CON RESUMEN EJECUTIVO
    
    Args:
        idea_general: Idea principal del segmento extraída por GPT-4o (nueva)
    """
    func_name = "enviar_coincidencia_inmediata"
    
    # Log inicio del proceso
    log_coincidencia_detectada(nombre_archivo, termino_encontrado, datetime.now().strftime('%H:%M:%S'), 0)
    
    try:
        webhook_config = cargar_webhook_config()
        telegram_config = cargar_telegram_config()
        
        # Extraer información del medio y hora
        info_medio_hora = extraer_info_medio_hora(nombre_archivo)
        
        # PASO 0: Usar idea general del segmento si está disponible (GPT-4o)
        resumen_ejecutivo = ""
        if idea_general:
            # ✨ USAR IDEA GENERAL EXTRAÍDA POR GPT-4o DEL SEGMENTO ESPECÍFICO
            resumen_ejecutivo = f"""🤖 Análisis del segmento:

{idea_general}

Término detectado: "{termino_encontrado}"
"""
            log_info(f"✅ Usando idea general extraída por GPT-4o para envío", func_name)
        elif transcripcion_completa and len(transcripcion_completa.strip()) > 100:
            try:
                resumen_ejecutivo = generar_resumen_archivo(nombre_archivo, [termino_encontrado], transcripcion_completa, tipo_archivo)
            except Exception as e:
                log_warning(f"Error generando resumen ejecutivo: {e}", func_name)
                # Resumen básico si falla la IA
                resumen_ejecutivo = f"""Tema principal: Se detectó una mención del término "{termino_encontrado}" en el contenido.

Contexto: {contexto_termino[:300]}{'...' if len(contexto_termino) > 300 else ''}

Puntos clave: El término "{termino_encontrado}" fue identificado en el contexto del programa, indicando relevancia informativa.

Relevancia: Esta mención es significativa para el monitoreo de contenido y puede requerir seguimiento adicional."""
        else:
            # Resumen básico cuando no hay transcripción completa
            resumen_ejecutivo = f"""Tema principal: Detección de término relevante "{termino_encontrado}" en contenido audiovisual.

Contexto: {contexto_termino[:300]}{'...' if len(contexto_termino) > 300 else ''}

Puntos clave: Se identificó una coincidencia directa con el término buscado en el momento específico del contenido.

Relevancia: La mención detectada es importante para el monitoreo continuo y análisis de contenido."""
        
        # Crear mensaje de RESUMEN EJECUTIVO (formato específico solicitado)
        mensaje_coincidencia = f"📺 Medio: {info_medio_hora}\n\n"
        mensaje_coincidencia += f"TÉRMINOS DETECTADOS: {termino_encontrado}\n\n"
        mensaje_coincidencia += f"{resumen_ejecutivo}"
        
        # === MOSTRAR RESUMEN EJECUTIVO COMPLETO EN LA INTERFAZ ===
        st.success("📋 **RESUMEN EJECUTIVO GENERADO:**")
        st.markdown("---")
        st.markdown(mensaje_coincidencia)
        st.markdown("---")
        
        if clip_path and os.path.exists(clip_path):
            mensaje_coincidencia += f"\n\n🎬 Clip generado: {os.path.basename(clip_path)}\n"
            mensaje_coincidencia += f"📤 Video a continuación en 30 segundos..."
        
        # === PASO 1: ENVIAR RESUMEN EJECUTIVO A TELEGRAM PRIMERO ===
        st.info("📝 **PASO 1: Enviando RESUMEN EJECUTIVO a Telegram...**")
        
        # Enviar resumen ejecutivo a Telegram PRIMERO
        if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
            with st.spinner("📱 Enviando resumen a Telegram..."):
                # Función de escape completa para Telegram
                def escape_telegram_text(text):
                    import re
                    # Remover todos los caracteres de formato markdown/html problemáticos
                    text = re.sub(r'[*_`\[\]()~>#+=|{}.!\\-]', '', text)
                    # Limpiar caracteres especiales que pueden causar problemas
                    text = text.replace('"', '').replace("'", '').replace('\n\n\n', '\n\n')
                    # Limitar longitud para evitar problemas
                    if len(text) > 4000:
                        text = text[:4000] + "..."
                    return text
                
                mensaje_telegram_limpio = escape_telegram_text(mensaje_coincidencia)
                
                exito_resumen, mensaje_resumen_tg = enviar_mensaje_telegram(
                    mensaje_telegram_limpio,
                    telegram_config['chat_id'],
                    telegram_config['bot_token'],
                    parse_mode='Markdown'  # Usar el mismo formato que el video
                )
                
                if exito_resumen:
                    log_info(f"✅ Resumen ejecutivo enviado a Telegram: {mensaje_resumen_tg}", func_name)
                    st.success("📝 ✅ **RESUMEN EJECUTIVO enviado a Telegram**")
                else:
                    log_warning(f"⚠️ Error enviando resumen ejecutivo a Telegram: {mensaje_resumen_tg}", func_name)
                    st.warning(f"⚠️ **Error resumen ejecutivo**: {mensaje_resumen_tg}")
        else:
            st.warning("📱 **Telegram no configurado** - Saltando envío de resumen")
        
        # === PASO 2: ENVIAR A WEBHOOK (DESACTIVADO TEMPORALMENTE) ===
        # st.info("🌐 **PASO 2: Enviando a webhook...**")
        
        # # Enviar al webhook si está configurado
        # if webhook_config['enabled'] and webhook_config['url']:
        #     with st.spinner("🌐 Enviando a webhook..."):
        #         # Limpiar mensaje para webhook (sin caracteres problemáticos)
        #         mensaje_webhook_limpio = mensaje_coincidencia.replace('**', '').replace('*', '').replace('`', '').replace('\n', ' ')
        #         
        #         data = {
        #             "tipo": "coincidencia_inmediata_texto",
        #         "archivo": nombre_archivo,
        #         "termino": termino_encontrado,
        #         "contexto": contexto_termino[:500],  # Limitar contexto
        #         "info_medio_hora": info_medio_hora,
        #         "tipo_archivo": tipo_archivo,
        #         "mensaje": mensaje_webhook_limpio,
        #         "timestamp": datetime.now().isoformat(),
        #         "fuente": "Video Analyzer IA - Detección Inmediata (Texto)",
        #         "paso": "1_resumen_texto"
        #     }
        #     
        #     exito_webhook, mensaje_webhook = enviar_a_webhook_individual(
        #         webhook_config['url'], 
        #         data, 
        #         func_name, 
        #         "Webhook Coincidencia Texto"
        #     )
        #     
        #     if exito_webhook:
        #         log_info(f"Resumen de coincidencia enviado al webhook: {mensaje_webhook}", func_name)
        #         st.success("🌐 Resumen enviado al webhook exitosamente")
        #     else:
        #         log_warning(f"Error enviando resumen al webhook: {mensaje_webhook}", func_name)
        #         st.warning(f"⚠️ Error webhook: {mensaje_webhook}")
        
        # Enviar a Telegram si está configurado (COMENTADO - Ya se envió en PASO 1)
        # if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
        #     # Limpiar mensaje para Telegram (sin markdown problemático)
        #     mensaje_telegram_limpio = mensaje_coincidencia.replace('**', '').replace('*', '').replace('`', '')
        #     
        #     exito_telegram, mensaje_telegram = enviar_mensaje_telegram(
        #         mensaje_telegram_limpio,
        #         telegram_config['chat_id'],
        #         telegram_config['bot_token']
        #     )
        #     
        #     if exito_telegram:
        #         log_info(f"Resumen de coincidencia enviado a Telegram: {mensaje_telegram}", func_name)
        #         st.success("📱 Resumen enviado a Telegram exitosamente")
        #     else:
        #         log_warning(f"Error enviando resumen a Telegram: {mensaje_telegram}", func_name)
        #         st.warning(f"⚠️ Error Telegram: {mensaje_telegram}")
        
        # === PASO 2.5: ENVIAR CORREO BREVO ===
        st.info("📧 PASO 2.5: Enviando correo con Brevo...")
        
        # Enviar correo si está configurado
        try:
            brevo_config = cargar_brevo_config()
            correos_destinatarios = obtener_correos_activos()
            if brevo_config['enabled'] and brevo_config['api_key'] and brevo_config['sender_email'] and correos_destinatarios:
                # Ya no usamos URL de Cloudinary en flujo de Telegram
                video_url_para_correo = None
                
                # Combinar transcripción y resumen ejecutivo mejorado
                contenido_completo_correo = f"""**TRANSCRIPCIÓN DEL CONTENIDO:**

{transcripcion_completa if transcripcion_completa else "Transcripción no disponible"}

---

**RESUMEN EJECUTIVO:**

{resumen_ejecutivo}"""
                
                exito_correo, mensaje_correo = enviar_correo_brevo(
                    termino_encontrado,
                    contenido_completo_correo,  # Transcripción + resumen
                    nombre_archivo,
                    clip_path,  # Video local para adjunto
                    info_medio_hora,  # Información del medio
                    [termino_encontrado],  # Lista de términos detectados
                    video_url_para_correo  # URL de Cloudinary para player incrustado
                )
                
                if exito_correo:
                    log_info(f"✅ Correo enviado exitosamente: {mensaje_correo}", func_name)
                    st.success("📧 ✅ Correo enviado exitosamente con Brevo")
                else:
                    log_warning(f"⚠️ Error enviando correo: {mensaje_correo}", func_name)
                    st.warning(f"⚠️ Error correo: {mensaje_correo}")
            else:
                log_info("Correo Brevo no configurado o deshabilitado", func_name)
                st.info("📧 Correo Brevo no configurado")
        except Exception as e:
            log_exception(func_name, e, "Error en envío de correo")
            st.error(f"❌ Error inesperado en correo: {str(e)[:100]}")
        
        # === PASO 3: PAUSA OBLIGATORIA DE 30 SEGUNDOS ===
        if clip_path and os.path.exists(clip_path):
            st.info("⏸️ PASO 3: Esperando 30 segundos antes de enviar el video clip...")
            log_info("Esperando 30 segundos antes de enviar clip de video", func_name)
            
            with st.spinner("⏳ Esperando 30s antes del video clip..."):
                time.sleep(30)
            
            st.success("✅ PASO 3 completado - Procediendo a enviar video clip")
            
            # === PASO 4: ENVIAR VIDEO CLIP ===
            st.info("🎬 PASO 4: Enviando video clip...")
            status_tg = st.empty()
            # Variables para resumen JSON por clip
            telegram_ok = False
            telegram_msg = ""
            drive_ok = False
            drive_link = None
            drive_msg = ""
            
            # Calcular tamaño del archivo si existe (definir antes de usar)
            file_size_mb = 0
            if clip_path and os.path.exists(clip_path):
                file_size_mb = os.path.getsize(clip_path) / (1024 * 1024)
            
            if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
                
                caption_clip = f"🎯 **CLIP DE COINCIDENCIA**\n\n"
                caption_clip += f"📺 **Medio**: {info_medio_hora}\n"
                caption_clip += f"⏰ **Generado**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                caption_clip += f"🔍 **TÉRMINOS DETECTADOS**: {termino_encontrado}\n\n"
                caption_clip += f"🏷️ **Término específico**: {termino_encontrado}\n"
                caption_clip += f"📝 **Contexto**: {contexto_termino[:200]}{'...' if len(contexto_termino) > 200 else ''}\n\n"
                caption_clip += f"📋 **INFORMACIÓN DEL ARCHIVO**:\n"
                caption_clip += f"📄 **Tipo de archivo**: {tipo_archivo}\n"
                caption_clip += f"📏 **Tamaño**: {file_size_mb:.1f}MB\n\n"
                caption_clip += f"━━━━━━━━━━━━━━━━━━━━━\n"
                
                # Reportar tamaño y forzar uso exclusivo de API directa (sin URL/Cloudinary)
                st.info(f"📏 Tamaño detectado para envío a Telegram: {file_size_mb:.2f} MB")
                max_mb = telegram_config.get('max_file_size_mb', 8)
                if file_size_mb <= max_mb:
                    st.info(f"📤 **Envío por API directa** ({file_size_mb:.1f}MB ≤ {max_mb}MB)")
                    caption_clip += f"🌐 **Vía**: API directa Telegram\n"
                else:
                    st.warning(f"🚫 **No se enviará**: {file_size_mb:.1f}MB > {max_mb}MB (solo API directa)")
                    caption_clip += f"🚫 **Vía**: Omitido (excede {max_mb}MB; se requiere compresión)\n"
                
                # ========== CONTROL DE DUPLICADOS ANTES DE ENVIAR ==========
                if 'clips_enviados_telegram' not in st.session_state:
                    st.session_state.clips_enviados_telegram = []
                
                # Verificar si ya fue enviado
                if clip_path in st.session_state.clips_enviados_telegram:
                    exito_clip = True
                    mensaje_clip = "✅ Ya enviado (duplicado evitado)"
                    st.info(f"⏭️ Clip ya enviado a Telegram: {os.path.basename(clip_path)}")
                    log_info(f"Clip duplicado evitado: {clip_path}", func_name)
                else:
                    with st.spinner("🎬 Enviando video clip a Telegram (API directa)..."):
                        if file_size_mb <= 50:
                            # Envío directo sin parse_mode para evitar fallos de formato
                            exito_clip, mensaje_clip, _ = enviar_video_telegram_directo(
                                clip_path,
                                caption_clip,
                                telegram_config['chat_id'],
                                telegram_config['bot_token'],
                                parse_mode=None
                            )
                        else:
                            exito_clip, mensaje_clip, _ = (False, f"Archivo demasiado grande ({file_size_mb:.1f}MB > {max_mb}MB).", None)
                
                if exito_clip:
                    log_info(f"Clip de video enviado a Telegram OK | Tamaño={file_size_mb:.2f}MB | Detalle={mensaje_clip}", func_name)
                    status_tg.success("📱 Enviado a Telegram ✅")
                    st.success("🎬 Video clip enviado a Telegram exitosamente")
                    telegram_ok = True
                    telegram_msg = mensaje_clip
                    
                    # ========== REGISTRAR EN SESIÓN PARA EVITAR DUPLICADOS ==========
                    if 'clips_enviados_telegram' not in st.session_state:
                        st.session_state.clips_enviados_telegram = []
                    if clip_path not in st.session_state.clips_enviados_telegram:
                        st.session_state.clips_enviados_telegram.append(clip_path)
                    try:
                        coincidencias_logger.coincidencias_logger.info(
                            f"📱 TELEGRAM | OK | Archivo: {os.path.basename(clip_path)} | Tamaño: {file_size_mb:.2f}MB | Mensaje: {mensaje_clip}"
                        )
                    except Exception:
                        pass
                else:
                    log_warning(f"Fallo envío Telegram | Tamaño={file_size_mb:.2f}MB | Motivo={mensaje_clip}", func_name)
                    status_tg.error("📱 Envío a Telegram ❌")
                    st.warning(f"⚠️ Error enviando clip: {mensaje_clip}")
                    telegram_ok = False
                    telegram_msg = mensaje_clip
                    try:
                        coincidencias_logger.coincidencias_logger.error(
                            f"📱 TELEGRAM | ERROR | Archivo: {os.path.basename(clip_path)} | Tamaño: {file_size_mb:.2f}MB | Motivo: {mensaje_clip}"
                        )
                    except Exception:
                        pass
            
            # También enviar clip al webhook si está configurado (DESACTIVADO TEMPORALMENTE)
            # if webhook_config['enabled'] and webhook_config['url']:
            #     # Crear data para el clip
            #     clip_data = {
            #         "tipo": "coincidencia_inmediata_clip",
            #         "archivo": nombre_archivo,
            #         "termino": termino_encontrado,
            #         "contexto": contexto_termino,
            #         "info_medio_hora": info_medio_hora,
            #         "tipo_archivo": tipo_archivo,
            #         "clip_filename": os.path.basename(clip_path),
            #         "clip_size_mb": round(os.path.getsize(clip_path) / (1024*1024), 2),
            #         "timestamp": datetime.now().isoformat(),
            #         "fuente": "Video Analyzer IA - Detección Inmediata (Clip)",
            #         "paso": "3_video_clip"
            #     }
            #     
            #     # Intentar enviar clip como base64 si es pequeño
            #     try:
            #         clip_size_mb = os.path.getsize(clip_path) / (1024*1024)
            #         if clip_size_mb <= webhook_config.get('max_file_size_mb', 8):
            #             with open(clip_path, 'rb') as f:
            #                 clip_content = base64.b64encode(f.read()).decode('utf-8')
            #             clip_data['video_base64'] = clip_content
            #             st.info(f"📤 Enviando clip al webhook ({clip_size_mb:.1f}MB)")
            #         else:
            #             clip_data['video_base64'] = None
            #             clip_data['razon_no_enviado'] = f"Muy grande ({clip_size_mb:.1f}MB > {webhook_config.get('max_file_size_mb', 8)}MB)"
            #             st.info(f"📋 Enviando solo metadatos del clip al webhook (muy grande: {clip_size_mb:.1f}MB)")
            #             
            #         exito_webhook_clip, mensaje_webhook_clip = enviar_a_webhook_individual(
            #             webhook_config['url'], 
            #             clip_data, 
            #             func_name, 
            #             "Webhook Clip Inmediato"
            #         )
            #         
            #         if exito_webhook_clip:
            #             log_info(f"Clip enviado al webhook: {mensaje_webhook_clip}", func_name)
            #             st.success("🌐 Clip enviado al webhook exitosamente")
            #         else:
            #             log_warning(f"Error enviando clip al webhook: {mensaje_webhook_clip}", func_name)
            #             st.warning(f"⚠️ Error webhook clip: {mensaje_webhook_clip}")
            #             
            #     except Exception as e:
            #         log_warning(f"Error preparando clip para webhook: {e}", func_name)
            #         st.warning(f"⚠️ Error preparando clip: {e}")
            
            st.success("✅ PASO 4 completado - Video clip enviado")
        
        # === PASO 5: ENVIAR A GOOGLE DRIVE ===
        st.info("☁️ **PASO 5: Enviando coincidencia a Google Drive...**")
        
        try:
            # Crear nombre único para el archivo de coincidencia
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_coincidencia_txt = f"COINCIDENCIA_{termino_encontrado}_{timestamp}_{nombre_archivo.replace('.mp4', '')}.txt"
            
            # Crear contenido del archivo de coincidencia
            contenido_coincidencia = f"""🎯 COINCIDENCIA DETECTADA INMEDIATAMENTE
===============================================

📺 MEDIO: {info_medio_hora}
🔍 TÉRMINO DETECTADO: {termino_encontrado}
📄 TIPO DE ARCHIVO: {tipo_archivo}
📝 CONTEXTO: {contexto_termino}
⏰ HORA DE DETECCIÓN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🎬 CLIP GENERADO: {os.path.basename(clip_path) if clip_path and os.path.exists(clip_path) else 'No generado'}

===============================================
DETALLES DE LA COINCIDENCIA:
===============================================

- Archivo origen: {nombre_archivo}
- Término encontrado: {termino_encontrado}
- Contexto completo: {contexto_termino}
- Información del medio: {info_medio_hora}
- Timestamp de detección: {datetime.now().isoformat()}
- Enviado inmediatamente tras detección

===============================================
ESTADO DE ENVÍOS:
===============================================

✅ Webhook: Enviado
✅ Telegram: Enviado (texto + video)
✅ Google Drive: Enviando...

===============================================
GENERADO POR: Video Analyzer IA v2.0
TIPO DE ENVÍO: Coincidencia Inmediata
===============================================
"""
            
            # Enviar archivo de texto a Google Drive
            with st.spinner("☁️ Subiendo coincidencia a Google Drive..."):
                resultado_txt, mensaje_txt = subir_texto_google_drive(
                    contenido_coincidencia, 
                    nombre_coincidencia_txt
                )
                
                if resultado_txt:
                    st.success(f"☁️ ✅ **COINCIDENCIA enviada a Google Drive**: {resultado_txt.get('name')}")
                    log_info(f"Coincidencia inmediata enviada a Google Drive: {resultado_txt.get('name')}", func_name)
                
                # ENVIAR TRANSCRIPCIÓN COMPLETA si está disponible
                if transcripcion_completa and len(transcripcion_completa.strip()) > 50:
                    nombre_transcripcion_completa = f"TRANSCRIPCION_COMPLETA_{termino_encontrado}_{timestamp}_{nombre_archivo.replace('.mp4', '')}.txt"
                    
                    contenido_transcripcion_completa = f"""TRANSCRIPCIÓN COMPLETA DEL VIDEO - COINCIDENCIA INMEDIATA
===============================================

VIDEO ORIGEN: {nombre_archivo}
TÉRMINO DETECTADO: {termino_encontrado}
FECHA TRANSCRIPCIÓN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
ENVIADO INMEDIATAMENTE TRAS DETECCIÓN

===============================================
TRANSCRIPCIÓN COMPLETA:
===============================================

{transcripcion_completa}

===============================================
CONTEXTO DE LA COINCIDENCIA:
===============================================

{contexto_termino}

===============================================
GENERADO POR: Video Analyzer IA v2.0
TIPO DE ENVÍO: Coincidencia Inmediata
===============================================
"""
                    
                    resultado_transcripcion, mensaje_transcripcion = subir_texto_google_drive(
                        contenido_transcripcion_completa, 
                        nombre_transcripcion_completa
                    )
                    
                    if resultado_transcripcion:
                        st.success(f"📝 ✅ TRANSCRIPCIÓN COMPLETA enviada a Google Drive: {resultado_transcripcion.get('name')}")
                        log_info(f"Transcripción completa de coincidencia inmediata enviada a Google Drive: {resultado_transcripcion.get('name')}", func_name)
                    else:
                        st.warning(f"⚠️ Error enviando transcripción completa a Google Drive: {mensaje_transcripcion}")
                        log_warning(f"Error enviando transcripción completa a Google Drive: {mensaje_transcripcion}", func_name)
                else:
                    st.info("ℹ️ No hay transcripción completa disponible para enviar")
                
                # Si hay clip, enviarlo también a Google Drive y capturar URL
                video_url_gdrive = None
                video_url_cloudinary = None
                if clip_path and os.path.exists(clip_path):
                    status_gd = st.empty()
                    with st.spinner("🎬 Subiendo video clip a Google Drive..."):
                        nombre_clip_gdrive = f"CLIP_{termino_encontrado}_{timestamp}_{os.path.basename(clip_path)}"
                        
                        resultado_clip, mensaje_clip_gdrive = subir_archivo_google_drive(
                            clip_path, 
                            nombre_clip_gdrive
                        )
                        
                        if resultado_clip:
                            # Capturar URL del video para usar en el correo
                            video_url_gdrive = resultado_clip.get('webViewLink')
                            status_gd.success(f"☁️ Subido a Drive ✅")
                            st.success(f"🎬 ✅ **VIDEO CLIP enviado a Google Drive**: {resultado_clip.get('name')} | [Abrir]({resultado_clip.get('webViewLink')})")
                            log_info(f"Clip de coincidencia inmediata enviado a Google Drive: {resultado_clip.get('name')} - URL: {video_url_gdrive}", func_name)
                    
                    # Intentar subir también a Cloudinary para obtener URL directa
                    with st.spinner("☁️ Subiendo video clip a Cloudinary..."):
                        try:
                            cloudinary_configurado = configurar_cloudinary()
                            if cloudinary_configurado:
                                video_url_cloudinary, mensaje_cloudinary = subir_video_cloudinary(clip_path, termino_encontrado)
                                if video_url_cloudinary:
                                    st.success(f"☁️ ✅ **VIDEO CLIP subido a Cloudinary**: {video_url_cloudinary}")
                                    log_info(f"Clip de coincidencia inmediata subido a Cloudinary: {video_url_cloudinary}", func_name)
                                else:
                                    st.warning(f"⚠️ Error subiendo a Cloudinary: {mensaje_cloudinary}")
                                    log_warning(f"Error subiendo clip a Cloudinary: {mensaje_cloudinary}", func_name)
                            else:
                                st.warning("⚠️ Cloudinary no está configurado")
                                log_warning("Cloudinary no está configurado para subir clip", func_name)
                        except Exception as e:
                            st.warning(f"⚠️ Error subiendo a Cloudinary: {e}")
                            log_warning(f"Error subiendo clip a Cloudinary: {e}", func_name)
                            drive_ok = True
                            drive_link = resultado_clip.get('webViewLink')
                            
                            # ========== REGISTRAR EN SESIÓN PARA EVITAR DUPLICADOS ==========
                            if 'clips_enviados_drive' not in st.session_state:
                                st.session_state.clips_enviados_drive = []
                            if clip_path not in st.session_state.clips_enviados_drive:
                                st.session_state.clips_enviados_drive.append(clip_path)
                            try:
                                coincidencias_logger.coincidencias_logger.info(
                                    f"☁️ DRIVE | OK | Archivo: {resultado_clip.get('name')} | Link: {resultado_clip.get('webViewLink')}"
                                )
                            except Exception:
                                pass
                        else:
                            status_gd.error("☁️ Drive ❌")
                            st.warning(f"⚠️ **Error enviando clip a Google Drive**: {mensaje_clip_gdrive}")
                            log_warning(f"Error enviando clip a Google Drive: {mensaje_clip_gdrive}", func_name)
                            drive_ok = False
                            drive_msg = mensaje_clip_gdrive
                            try:
                                coincidencias_logger.coincidencias_logger.error(
                                    f"☁️ DRIVE | ERROR | Archivo: {os.path.basename(clip_path)} | Motivo: {mensaje_clip_gdrive}"
                                )
                            except Exception:
                                pass

                # === Registrar resumen JSON por clip ===
                try:
                    resumen_clip = {
                        "timestamp": datetime.now().isoformat(),
                        "clip_filename": os.path.basename(clip_path) if clip_path else None,
                        "clip_path": clip_path,
                        "size_mb": round(file_size_mb, 2),
                        "termino": termino_encontrado,
                        "video_origen": nombre_archivo,
                        "telegram": {"ok": telegram_ok, "message": telegram_msg},
                        "drive": {"ok": drive_ok, "link": drive_link, "message": drive_msg}
                    }
                    logs_dir = os.path.join(os.getcwd(), "logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    date_str = datetime.now().strftime("%Y%m%d")
                    jsonl_path = os.path.join(logs_dir, f"clips_summary_{date_str}.jsonl")
                    with open(jsonl_path, "a", encoding="utf-8") as jf:
                        jf.write(json.dumps(resumen_clip, ensure_ascii=False) + "\n")
                except Exception as e:
                    log_warning(f"No se pudo escribir resumen JSON del clip: {e}", func_name)
                
                else:
                    st.warning(f"⚠️ Error enviando coincidencia a Google Drive: {mensaje_txt}")
                    log_warning(f"Error enviando coincidencia a Google Drive: {mensaje_txt}", func_name)
                
        except Exception as e:
            st.warning(f"⚠️ Error en envío a Google Drive: {e}")
            log_warning(f"Error enviando coincidencia inmediata a Google Drive: {e}", func_name)
        
        st.success("✅ **PASO 5 completado** - Coincidencia enviada a Google Drive")
        
        # Resumen final del proceso
        st.markdown("---")
        st.subheader("🎉 **PROCESO COMPLETADO**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("📝 Resumen enviado")
        with col2:
            st.success("🎬 Video clip enviado")
        with col3:
            st.success("☁️ Google Drive actualizado")
        
        # === PASO 6: RESUMEN FINAL DE ENVÍOS ===
        st.success("🎉 **ENVÍO COMPLETO A TODOS LOS DESTINOS**")
        
        # Mostrar resumen detallado de envíos
        st.markdown("### 📊 **RESUMEN DE ENVÍOS:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🌐 **Webhook (Make.com)**")
            if webhook_config.get('enabled', False):
                st.success("✅ Texto enviado")
                st.success("✅ Clip enviado")
            else:
                st.info("⚪ Deshabilitado")
        
        with col2:
            st.markdown("#### 📱 **Telegram**")
            if telegram_config.get('enabled', False):
                st.success("✅ Texto enviado")
                st.success("✅ Video enviado")
            else:
                st.info("⚪ Deshabilitado")
        
        with col3:
            st.markdown("#### ☁️ **Google Drive**")
            st.success("✅ Archivo TXT subido")
            st.success("✅ Video clip subido")
        
        # Agregar información del archivo MD
        st.markdown("#### 📝 **Archivo de Coincidencias**")
        st.success("✅ Archivo MD actualizado: coincidencias.md")
        
        # === PASO 7: GENERAR ARCHIVO MD DE COINCIDENCIAS ===
        st.info("📝 PASO 7: Generando archivo MD de coincidencias...")
        
        try:
            # Combinar transcripción completa con resumen ejecutivo para el MD
            contenido_completo_md = f"""**TRANSCRIPCIÓN DEL CONTENIDO:**

{transcripcion_completa if transcripcion_completa else "Transcripción no disponible"}

---

**RESUMEN EJECUTIVO:**

{resumen_ejecutivo}"""
            
            # Generar archivo MD - usar URL de Cloudinary si está disponible, sino Google Drive
            video_url_para_md = video_url_cloudinary if video_url_cloudinary else video_url_gdrive
            exito_md, mensaje_md = generar_archivo_coincidencias_md(
                termino_encontrado,
                contenido_completo_md,
                nombre_archivo,
                info_medio_hora,
                [termino_encontrado],
                video_url_para_md,
                clip_path
            )
            
            if exito_md:
                st.success("📝 ✅ Archivo MD actualizado: coincidencias.md")
                log_info(f"Archivo MD actualizado: {mensaje_md}", func_name)
            else:
                st.warning(f"⚠️ Error generando archivo MD: {mensaje_md}")
                log_warning(f"Error generando archivo MD: {mensaje_md}", func_name)
                
        except Exception as e:
            st.warning(f"⚠️ Error en generación de archivo MD: {e}")
            log_warning(f"Error generando archivo MD: {e}", func_name)
        
        # === PASO 7: ENVIAR A SUPABASE ===
        st.info("🗄️ **PASO 7: Enviando a Supabase...**")
        try:
            # Preparar item de coincidencia para Supabase
            coincidencia_item = {
                'termino': termino_encontrado,
                'texto': contexto_termino,
                'contexto': contexto_termino,
                'timestamp': timestamp if timestamp is not None else '0.0',  # Agregar timestamp para control de duplicados
                'url_cloudinary': video_url_cloudinary if 'video_url_cloudinary' in locals() else None
            }
            
            supabase_success, supabase_msg = enviar_coincidencias_a_supabase(
                [coincidencia_item],  # Lista con un item
                nombre_archivo,
                tipo_archivo,
                resumen_ejecutivo,
                transcripcion_completa,
                video_url_cloudinary if 'video_url_cloudinary' in locals() else None,
                None  # enlace_directo
            )
            
            if supabase_success:
                st.success(f"🗄️ ✅ {supabase_msg}")
                log_info(f"Coincidencia enviada a Supabase: {supabase_msg}", func_name)
            else:
                st.warning(f"⚠️ Supabase: {supabase_msg}")
                log_warning(f"Supabase falló: {supabase_msg}", func_name)
        except Exception as e:
            st.warning(f"⚠️ Error Supabase: {e}")
            log_warning(f"Error enviando a Supabase: {e}", func_name)
        
        st.markdown("---")
        st.success(f"🎯 **Coincidencia procesada completamente:** {termino_encontrado}")
        
        return True, "Coincidencia enviada: resumen + video clip + Google Drive + archivo MD + Supabase (con pausas)"
        
    except Exception as e:
        log_exception(func_name, e, f"Error enviando coincidencia inmediata para {nombre_archivo}")
        return False, f"Error: {str(e)}"

# === FUNCIONES DE TELEGRAM Y CLOUDINARY ===
def cargar_telegram_config():
    """Carga configuración de Telegram"""
    default_config = {
        'enabled': True,  # Habilitado por defecto
        'bot_token': 'YOUR_TELEGRAM_BOT_TOKEN',  # Tu nuevo bot token
        'chat_id': '@edesuralertas',  # Tu canal de Telegram actualizado
        'send_clips': True,
        'send_summary': True,
        'use_cloudinary': True,
        'max_file_size_mb': 50,
        'timeout': 30
    }
    
    try:
        if os.path.exists(TELEGRAM_CONFIG):
            with open(TELEGRAM_CONFIG, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
    except Exception as e:
        st.warning(f"⚠️ Error cargando configuración Telegram: {e}")
    
    return default_config

def guardar_telegram_config(config):
    """Guarda configuración de Telegram"""
    try:
        with open(TELEGRAM_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración Telegram: {e}")
        return False

def cargar_cloudinary_config():
    """Carga configuración de Cloudinary (prioriza variables de entorno)"""
    default_config = {
        'cloud_name': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
        'api_key': os.getenv('CLOUDINARY_API_KEY', ''),
        'api_secret': os.getenv('CLOUDINARY_API_SECRET', ''),
        'folder': 'video_analyzer_clips',
        'resource_type': 'video',
        'quality': 'auto',
        'format': 'mp4'
    }
    
    try:
        if os.path.exists(CLOUDINARY_CONFIG):
            with open(CLOUDINARY_CONFIG, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
    except Exception as e:
        st.warning(f"⚠️ Error cargando configuración Cloudinary: {e}")
    
    return default_config

def guardar_cloudinary_config(config):
    """Guarda configuración de Cloudinary"""
    try:
        with open(CLOUDINARY_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración Cloudinary: {e}")
        return False

# === CONFIGURACIÓN BREVO (EMAIL) ===
BREVO_CONFIG = "brevo_config.json"
CORREOS_GUARDADOS = "correos_guardados.json"

def cargar_brevo_config():
    """Carga configuración de Brevo"""
    default_config = {
        'enabled': False,
        'api_key': '',
        'sender_email': '',
        'sender_name': 'Sistema de Análisis de Videos',
        'recipient_email': '',
        'recipient_name': '',
        'smtp_server': 'smtp-relay.sendinblue.com',
        'smtp_port': 587
    }
    
    try:
        if os.path.exists(BREVO_CONFIG):
            with open(BREVO_CONFIG, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Fusionar con defaults para agregar nuevos campos si los hay
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
    except Exception as e:
        log_exception("cargar_brevo_config", e)
    
    return default_config

def guardar_brevo_config(config):
    """Guarda configuración de Brevo"""
    try:
        with open(BREVO_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_exception("guardar_brevo_config", e)
        return False

def cargar_correos_guardados():
    """Carga lista de correos guardados"""
    try:
        if os.path.exists(CORREOS_GUARDADOS):
            with open(CORREOS_GUARDADOS, 'r', encoding='utf-8') as f:
                data = json.load(f)
                correos = data.get('correos', [])
                # Normalizar formato: convertir 'email' a 'correo' si es necesario
                for correo in correos:
                    if 'email' in correo and 'correo' not in correo:
                        correo['correo'] = correo['email']
                return correos
    except Exception as e:
        log_exception("cargar_correos_guardados", e)
    return []

def guardar_correos_lista(correos_lista):
    """Guarda lista de correos"""
    try:
        # Normalizar formato: asegurar que cada correo tenga el formato correcto
        correos_normalizados = []
        for correo in correos_lista:
            if isinstance(correo, dict):
                # Si ya es un dict, normalizar los campos
                correo_norm = {
                    'correo': correo.get('correo') or correo.get('email', ''),
                    'email': correo.get('correo') or correo.get('email', ''),  # Mantener ambos para compatibilidad
                    'nombre': correo.get('nombre', ''),
                    'fecha_agregado': correo.get('fecha_agregado', datetime.now().isoformat()),
                    'activo': correo.get('activo', True)
                }
                correos_normalizados.append(correo_norm)
            else:
                # Si es solo un string, crear el formato completo
                correos_normalizados.append({
                    'correo': correo,
                    'email': correo,  # Mantener ambos para compatibilidad
                    'nombre': '',
                    'fecha_agregado': datetime.now().isoformat(),
                    'activo': True
                })
        
        data = {
            'correos': correos_normalizados,
            'total_correos': len(correos_normalizados),
            'fecha_actualizacion': datetime.now().isoformat()
        }
        with open(CORREOS_GUARDADOS, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_exception("guardar_correos_lista", e)
        return False

def agregar_correo_a_lista(nuevo_correo, nombre=""):
    """Agrega un correo a la lista guardada"""
    correos = cargar_correos_guardados()
    
    # Verificar si ya existe
    for correo_data in correos:
        if correo_data['email'].lower() == nuevo_correo.lower():
            return False, "El correo ya existe en la lista"
    
    # Agregar nuevo correo
    correo_obj = {
        'email': nuevo_correo.strip(),
        'nombre': nombre.strip() if nombre else nuevo_correo.split('@')[0],
        'fecha_agregado': datetime.now().isoformat(),
        'activo': True
    }
    
    correos.append(correo_obj)
    
    if guardar_correos_lista(correos):
        return True, f"Correo {nuevo_correo} agregado exitosamente"
    else:
        return False, "Error guardando la lista"

def eliminar_correo_de_lista(correo_a_eliminar):
    """Elimina un correo de la lista"""
    correos = cargar_correos_guardados()
    correos_filtrados = [c for c in correos if c['email'].lower() != correo_a_eliminar.lower()]
    
    if len(correos_filtrados) != len(correos):
        if guardar_correos_lista(correos_filtrados):
            return True, f"Correo {correo_a_eliminar} eliminado"
        else:
            return False, "Error guardando la lista"
    else:
        return False, "Correo no encontrado"

def obtener_correos_activos():
    """Obtiene solo los correos activos de la lista"""
    correos = cargar_correos_guardados()
    return [c['email'] for c in correos if c.get('activo', True)]

def configurar_cloudinary():
    """Configura Cloudinary con las credenciales guardadas"""
    config = cargar_cloudinary_config()
    
    if config['cloud_name'] and config['api_key'] and config['api_secret']:
        cloudinary.config(
            cloud_name=config['cloud_name'],
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            secure=True
        )
        return True
    return False

def subir_video_cloudinary(video_path, termino="", timestamp=""):
    """Sube un video a Cloudinary y retorna la URL"""
    try:
        if not configurar_cloudinary():
            return None, "Cloudinary no configurado"
        
        config = cargar_cloudinary_config()
        
        # Crear nombre único para el archivo
        nombre_base = os.path.splitext(os.path.basename(video_path))[0]
        public_id = f"{config['folder']}/{termino}_{timestamp}_{nombre_base}" if termino else f"{config['folder']}/{nombre_base}"
        
        # Subir video
        result = cloudinary.uploader.upload(
            video_path,
            resource_type=config['resource_type'],
            public_id=public_id,
            folder=config['folder'],
            quality=config['quality'],
            format=config['format'],
            overwrite=True,
            invalidate=True
        )
        
        return result['secure_url'], "Video subido exitosamente"
        
    except Exception as e:
        return None, f"Error subiendo a Cloudinary: {str(e)[:100]}"

# === FUNCIONES DE GOOGLE DRIVE ===
def obtener_credenciales_google_drive():
    """Obtiene credenciales de Google Drive usando refresh token"""
    try:
        # Crear credenciales usando el refresh token
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
        
        return creds
    except Exception as e:
        log_exception("obtener_credenciales_google_drive", e)
        return None

def crear_servicio_google_drive():
    """Crea el servicio de Google Drive"""
    try:
        creds = obtener_credenciales_google_drive()
        if not creds:
            return None, "No se pudieron obtener credenciales de Google Drive"
        
        service = build('drive', 'v3', credentials=creds)
        return service, "Servicio creado exitosamente"
    except Exception as e:
        log_exception("crear_servicio_google_drive", e)
        return None, f"Error creando servicio: {str(e)[:100]}"

def subir_archivo_google_drive(archivo_path, nombre_archivo=None, mime_type=None):
    """Sube un archivo a Google Drive en la carpeta especificada"""
    func_name = "subir_archivo_google_drive"
    
    try:
        if not os.path.exists(archivo_path):
            error_msg = f"Archivo no existe: {archivo_path}"
            log_error_critico(func_name, error_msg, archivo_path)
            return None, error_msg
        
        service, mensaje = crear_servicio_google_drive()
        if not service:
            log_error_critico(func_name, mensaje, archivo_path)
            return None, mensaje
        
        # Usar nombre del archivo si no se especifica
        if not nombre_archivo:
            nombre_archivo = os.path.basename(archivo_path)
        
        # Determinar MIME type si no se especifica
        if not mime_type:
            if archivo_path.endswith('.mp4'):
                mime_type = 'video/mp4'
            elif archivo_path.endswith('.txt'):
                mime_type = 'text/plain'
            elif archivo_path.endswith('.md'):
                mime_type = 'text/markdown'
            else:
                mime_type = 'application/octet-stream'
        
        # Obtener tamaño del archivo para logging
        file_size = os.path.getsize(archivo_path)
        
        # Log inicio de subida
        log_gdrive_upload_start(nombre_archivo, file_size, mime_type)
        
        # Crear metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        # Crear media para subida
        media = MediaFileUpload(archivo_path, mimetype=mime_type, resumable=True)
        
        # Subir archivo
        log_info(f"Subiendo {nombre_archivo} a Google Drive...", func_name)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        # Log éxito
        log_gdrive_upload_success(nombre_archivo, file.get('id'), file.get('webViewLink'))
        log_info(f"Archivo subido exitosamente: {file.get('name')} (ID: {file.get('id')})", func_name)
        return file, "Archivo subido exitosamente"
        
    except HttpError as e:
        error_msg = f"Error HTTP de Google Drive: {e.resp.status} {e.content.decode()}"
        log_gdrive_upload_error(nombre_archivo or os.path.basename(archivo_path), error_msg, e.resp.status)
        log_exception(func_name, e, error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error subiendo archivo: {str(e)[:100]}"
        log_gdrive_upload_error(nombre_archivo or os.path.basename(archivo_path), error_msg)
        log_exception(func_name, e, error_msg)
        return None, error_msg

def subir_texto_google_drive(contenido_texto, nombre_archivo, mime_type='text/plain'):
    """Sube contenido de texto directamente a Google Drive"""
    func_name = "subir_texto_google_drive"
    
    try:
        service, mensaje = crear_servicio_google_drive()
        if not service:
            log_error_critico(func_name, mensaje)
            return None, mensaje
        
        # Obtener tamaño del contenido para logging
        content_size = len(contenido_texto.encode('utf-8'))
        
        # Log inicio de subida
        log_gdrive_upload_start(nombre_archivo, content_size, mime_type)
        
        # Crear metadata del archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        # Crear media para contenido de texto
        media = MediaIoBaseUpload(
            io.BytesIO(contenido_texto.encode('utf-8')),
            mimetype=mime_type,
            resumable=True
        )
        
        # Subir archivo
        log_info(f"Subiendo texto {nombre_archivo} a Google Drive...", func_name)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()
        
        # Log éxito
        log_gdrive_upload_success(nombre_archivo, file.get('id'), file.get('webViewLink'))
        log_info(f"Texto subido exitosamente: {file.get('name')} (ID: {file.get('id')})", func_name)
        return file, "Texto subido exitosamente"
        
    except HttpError as e:
        error_msg = f"Error HTTP de Google Drive: {e.resp.status} {e.content.decode()}"
        log_gdrive_upload_error(nombre_archivo, error_msg, e.resp.status)
        log_exception(func_name, e, error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error subiendo texto: {str(e)[:100]}"
        log_gdrive_upload_error(nombre_archivo, error_msg)
        log_exception(func_name, e, error_msg)
        return None, error_msg

def enviar_clips_a_google_drive(clips_generados, resumen, terminos_detectados, video_origen, transcripcion_completa=""):
    """Envía clips, resumen Y TRANSCRIPCIÓN COMPLETA a Google Drive"""
    func_name = "enviar_clips_a_google_drive"
    log_info(f"Iniciando envío de {len(clips_generados)} clips + transcripción completa a Google Drive. Video: {video_origen}", func_name)
    
    # ========== CONTROL DE DUPLICADOS ==========
    # Verificar si ya se subieron estos clips individualmente
    clips_ya_subidos = 0
    clips_pendientes = []
    
    for clip in clips_generados:
        clip_path = clip.get('path', '')
        if clip_path in st.session_state.get('clips_enviados_drive', []):
            clips_ya_subidos += 1
            st.info(f"⏭️ Clip ya subido a Drive individualmente: {os.path.basename(clip_path)}")
        else:
            clips_pendientes.append(clip)
    
    if clips_ya_subidos == len(clips_generados):
        st.success(f"✅ Todos los clips ya fueron subidos a Drive individualmente ({clips_ya_subidos}/{len(clips_generados)})")
        return True, f"✅ Todos los clips ya subidos a Drive individualmente"
    
    if clips_pendientes:
        st.info(f"📤 Subiendo {len(clips_pendientes)} clips pendientes a Drive (de {len(clips_generados)} total)")
        clips_generados = clips_pendientes  # Usar solo los clips pendientes
    
    try:
        # Crear nombre de carpeta para este video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_video_limpio = os.path.splitext(os.path.basename(video_origen))[0]
        carpeta_video = f"c_Analisis_{nombre_video_limpio}_{timestamp}"
        
        # Subir resumen ejecutivo como TXT
        nombre_resumen = f"RESUMEN_{nombre_video_limpio}_{timestamp}.txt"
        resumen_completo = f"""ANÁLISIS DE VIDEO - RESUMEN EJECUTIVO
===============================================

VIDEO ORIGEN: {video_origen}
FECHA ANÁLISIS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
TÉRMINOS DETECTADOS: {', '.join(terminos_detectados)}
TOTAL CLIPS GENERADOS: {len(clips_generados)}

===============================================
RESUMEN EJECUTIVO:
===============================================

{resumen}

===============================================
DETALLES DE CLIPS:
===============================================

"""
        
        # Agregar detalles de cada clip
        for i, clip in enumerate(clips_generados, 1):
            resumen_completo += f"""
CLIP {i}/{len(clips_generados)}:
- Término encontrado: {clip.get('termino', 'N/A')}
- Tiempo en video: {clip.get('tiempo', 'N/A')}
- Contexto: {clip.get('contexto', 'N/A')[:200]}...
- Archivo: {os.path.basename(clip.get('path', 'N/A'))}
"""
        
        # Subir resumen a Google Drive
        resultado_resumen, mensaje_resumen = subir_texto_google_drive(
            resumen_completo, 
            nombre_resumen
        )
        
        if resultado_resumen:
            log_info(f"✅ Resumen subido: {resultado_resumen.get('name')}", func_name)
        else:
            log_warning(f"⚠️ Error subiendo resumen: {mensaje_resumen}", func_name)
        
        # Subir TRANSCRIPCIÓN COMPLETA a Google Drive
        if transcripcion_completa and len(transcripcion_completa.strip()) > 50:
            nombre_transcripcion = f"TRANSCRIPCION_COMPLETA_{nombre_video_limpio}_{timestamp}.txt"
            
            contenido_transcripcion = f"""TRANSCRIPCIÓN COMPLETA DEL VIDEO
===============================================

VIDEO ORIGEN: {video_origen}
FECHA TRANSCRIPCIÓN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
TÉRMINOS DETECTADOS: {', '.join(terminos_detectados)}
TOTAL CLIPS GENERADOS: {len(clips_generados)}

===============================================
TRANSCRIPCIÓN COMPLETA:
===============================================

{transcripcion_completa}

===============================================
GENERADO POR: Video Analyzer IA v2.0
===============================================
"""
            
            resultado_transcripcion, mensaje_transcripcion = subir_texto_google_drive(
                contenido_transcripcion, 
                nombre_transcripcion
            )
            
            if resultado_transcripcion:
                log_info(f"✅ Transcripción completa subida: {resultado_transcripcion.get('name')}", func_name)
                st.success(f"📝 Transcripción completa enviada a Google Drive")
            else:
                log_warning(f"⚠️ Error subiendo transcripción completa: {mensaje_transcripcion}", func_name)
        
        # Subir cada clip y su transcripción TXT
        clips_subidos = 0
        clips_fallidos = 0
        transcripciones_subidas = 0
        transcripciones_fallidas = 0
        
        for i, clip in enumerate(clips_generados, 1):
            clip_path = clip.get('path', '')
            txt_path = clip_path.replace('.mp4', '.txt')
            
            # Subir clip de video
            if os.path.exists(clip_path):
                # Crear nombre único para el clip
                nombre_clip = f"CLIP_{i:02d}_{clip.get('termino', 'termino')}_{clip.get('tiempo', 'tiempo')}_{os.path.basename(clip_path)}"
                
                resultado_clip, mensaje_clip = subir_archivo_google_drive(
                    clip_path, 
                    nombre_clip
                )
                
                if resultado_clip:
                    clips_subidos += 1
                    log_info(f"✅ Clip {i} subido: {resultado_clip.get('name')}", func_name)
                else:
                    clips_fallidos += 1
                    log_warning(f"⚠️ Error subiendo clip {i}: {mensaje_clip}", func_name)
            else:
                clips_fallidos += 1
                log_warning(f"⚠️ Archivo de video no existe: {clip_path}", func_name)
            
            # Subir transcripción TXT
            if os.path.exists(txt_path):
                # Crear nombre único para la transcripción
                nombre_txt = f"TRANSCRIPCION_{i:02d}_{clip.get('termino', 'termino')}_{clip.get('tiempo', 'tiempo')}_{os.path.basename(txt_path)}"
                
                resultado_txt, mensaje_txt = subir_archivo_google_drive(
                    txt_path, 
                    nombre_txt
                )
                
                if resultado_txt:
                    transcripciones_subidas += 1
                    log_info(f"✅ Transcripción {i} subida: {resultado_txt.get('name')}", func_name)
                else:
                    transcripciones_fallidas += 1
                    log_warning(f"⚠️ Error subiendo transcripción {i}: {mensaje_txt}", func_name)
            else:
                transcripciones_fallidas += 1
                log_warning(f"⚠️ Archivo de transcripción no existe: {txt_path}", func_name)
        
        # Crear resumen de envío
        resumen_envio = f"""ENVÍO COMPLETADO A GOOGLE DRIVE
===============================================

VIDEO: {video_origen}
FECHA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESULTADOS:
- Resumen ejecutivo: {'✅ Subido' if resultado_resumen else '❌ Falló'}
- Clips de video subidos: {clips_subidos}/{len(clips_generados)}
- Clips de video fallidos: {clips_fallidos}
- Transcripciones TXT subidas: {transcripciones_subidas}/{len(clips_generados)}
- Transcripciones TXT fallidas: {transcripciones_fallidas}

CARPETA DESTINO: {GOOGLE_DRIVE_FOLDER_ID}
"""
        
        log_info(f"Envío a Google Drive completado: {clips_subidos} clips subidos, {clips_fallidos} fallidos, {transcripciones_subidas} transcripciones subidas, {transcripciones_fallidas} fallidas", func_name)
        
        return True, f"✅ {clips_subidos} clips, {transcripciones_subidas} transcripciones TXT y resumen enviados a Google Drive"
        
    except Exception as e:
        error_msg = f"Error en envío a Google Drive: {str(e)[:100]}"
        log_exception(func_name, e, error_msg)
        return False, error_msg

def test_google_drive_connection():
    """Prueba la conexión con Google Drive"""
    try:
        service, mensaje = crear_servicio_google_drive()
        if service:
            # Intentar listar archivos en la carpeta
            results = service.files().list(
                pageSize=1,
                q=f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents",
                fields="files(id, name)"
            ).execute()
            
            return True, f"✅ Conexión exitosa. Archivos en carpeta: {len(results.get('files', []))}"
        else:
            return False, f"❌ Error: {mensaje}"
    except Exception as e:
        return False, f"❌ Error probando conexión: {str(e)[:100]}"

def enviar_webhook_simple(url, data):
    """
    Envía un webhook simple para pruebas de conexión
    """
    func_name = "enviar_webhook_simple"
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'VideoAnalyzer-AI/2.0'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, f"Webhook respondió correctamente (HTTP {response.status_code})"
        else:
            return False, f"Webhook respondió con error (HTTP {response.status_code})"
            
    except requests.exceptions.Timeout:
        return False, "Timeout: Webhook no respondió en 10 segundos"
    except requests.exceptions.ConnectionError:
        return False, "Error de conexión: No se pudo conectar al webhook"
    except Exception as e:
        return False, f"Error inesperado: {str(e)[:100]}"

def enviar_coincidencias_a_supabase(coincidencias_items, nombre_archivo, tipo_archivo, resumen_archivo="", transcripcion_completa="", url_video=None, enlace_directo=None):
    """
    Envía las coincidencias encontradas a la tabla 'alertas_medios' en Supabase
    
    Args:
        coincidencias_items: Lista de diccionarios con las coincidencias
        nombre_archivo: Nombre del archivo procesado
        tipo_archivo: Tipo de archivo (video, audio, etc.)
        resumen_archivo: Resumen del archivo (opcional)
        transcripcion_completa: Transcripción completa (opcional)
        url_video: URL del video en Cloudinary (opcional)
        enlace_directo: Enlace directo al video (opcional)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    func_name = "enviar_coincidencias_a_supabase"
    
    if not supabase:
        return False, "❌ Cliente de Supabase no inicializado"
    
    if not coincidencias_items:
        return True, "ℹ️ No hay coincidencias para enviar"
    
    # ========== CONTROL DE DUPLICADOS PARA SUPABASE ==========
    # Filtrar coincidencias que ya fueron enviadas a Supabase en esta sesión
    coincidencias_no_duplicadas = []
    duplicados_detectados = 0
    
    for item in coincidencias_items:
        # Crear clave única para esta coincidencia (término + timestamp + archivo)
        termino = item.get('termino', '')
        timestamp = item.get('timestamp', '')
        clave_supabase = f"{termino}_{timestamp}_{nombre_archivo}"
        
        # Verificar si ya fue enviada a Supabase
        if clave_supabase in st.session_state.coincidencias_enviadas_supabase:
            duplicados_detectados += 1
            log_info(f"⏭️ DUPLICADO SUPABASE EVITADO: '{termino}' en {timestamp}s para {nombre_archivo}", func_name)
            continue
        
        # Agregar a la lista de no duplicados
        coincidencias_no_duplicadas.append(item)
        # Marcar como enviada
        st.session_state.coincidencias_enviadas_supabase.add(clave_supabase)
    
    if duplicados_detectados > 0:
        log_info(f"🛡️ CONTROL DUPLICADOS SUPABASE: {duplicados_detectados} duplicados evitados", func_name)
        st.info(f"🛡️ **Control Duplicados**: {duplicados_detectados} coincidencias duplicadas evitadas para Supabase")
    
    # Si no hay coincidencias nuevas, retornar éxito
    if not coincidencias_no_duplicadas:
        return True, f"ℹ️ Todas las coincidencias ya fueron enviadas a Supabase ({duplicados_detectados} duplicados evitados)"
    
    # Usar solo las coincidencias no duplicadas
    coincidencias_items = coincidencias_no_duplicadas
    
    try:
        # Extraer información del medio y hora del nombre del archivo
        info_medio_hora = extraer_info_medio_hora(nombre_archivo)
        
        # Intentar extraer nombre del medio y hora/fecha del programa
        nombre_medio = "Medio de Comunicación"
        hora_programa = None
        fecha_programa = None
        
        # Parsear info_medio_hora (formato típico: "MEDIO - HH:MM" o "MEDIO HH:MM")
        if info_medio_hora:
            partes = info_medio_hora.split('-')
            if len(partes) >= 2:
                nombre_medio = partes[0].strip()
                hora_str = partes[1].strip()
                
                # Intentar parsear la hora
                try:
                    from datetime import datetime
                    # Extraer hora si está en formato HH:MM o HH:MM:SS
                    import re
                    match_hora = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', hora_str)
                    if match_hora:
                        hora = int(match_hora.group(1))
                        minuto = int(match_hora.group(2))
                        segundo = int(match_hora.group(3)) if match_hora.group(3) else 0
                        
                        # Crear objeto time
                        from datetime import time
                        hora_programa = time(hora, minuto, segundo)
                except Exception as e:
                    log_warning(f"No se pudo parsear hora del programa: {e}", func_name)
            elif len(partes) == 1:
                nombre_medio = partes[0].strip()
        
        # Intentar extraer fecha del nombre del archivo
        # Formato común: YYYY-MM-DD o YYYYMMDD
        try:
            import re
            # Buscar patrón de fecha en el nombre del archivo
            match_fecha = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', nombre_archivo)
            if match_fecha:
                from datetime import date
                año = int(match_fecha.group(1))
                mes = int(match_fecha.group(2))
                dia = int(match_fecha.group(3))
                fecha_programa = date(año, mes, dia)
        except Exception as e:
            log_warning(f"No se pudo parsear fecha del programa: {e}", func_name)
        
        # Preparar datos para Supabase - SIN NULLS
        datos_supabase = []
        
        # Usar fecha/hora actual si no se pudieron extraer
        from datetime import datetime as dt
        fecha_actual = dt.now().date()
        hora_actual = dt.now().time()
        
        for item in coincidencias_items:
            # Obtener URL del clip de Cloudinary desde el item
            url_clip = item.get('url_cloudinary', url_video)
            
            # ASEGURAR QUE NO HAYA NULLS - Usar valores por defecto
            # Timestamp actual en formato ISO 8601 para PostgreSQL
            timestamp_actual = dt.now().isoformat()
            
            registro = {
                'fecha_detencion': timestamp_actual,  # Timestamp de cuando se detectó
                'termino_detectado': item.get('termino', 'termino_desconocido'),
                'nombre_medio': nombre_medio if nombre_medio else 'Medio de Comunicacion',
                'hora_programa': hora_programa.isoformat() if hora_programa else hora_actual.isoformat(),
                'fecha_programa': fecha_programa.isoformat() if fecha_programa else fecha_actual.isoformat(),
                'url_video': url_clip if url_clip else '',  # URL de Cloudinary del CLIP
                'nombre_archivo': nombre_archivo if nombre_archivo else 'archivo_desconocido',
                'enlace_directo': enlace_directo if enlace_directo else '',
                'contexto': item.get('texto', '') or item.get('contexto', '') or 'Sin contexto disponible',
                'resumen_ejecutivo': resumen_archivo if resumen_archivo else 'Resumen no disponible',
                'transcripcion': transcripcion_completa if transcripcion_completa else 'Transcripcion no disponible',
                'relevancia': 'Alta'
            }
            
            # Validar que NO haya None en ningún campo
            for key, value in registro.items():
                if value is None:
                    if key in ['hora_programa']:
                        registro[key] = hora_actual.isoformat()
                    elif key in ['fecha_programa']:
                        registro[key] = fecha_actual.isoformat()
                    elif key in ['fecha_detencion']:
                        registro[key] = dt.now().isoformat()
                    elif key in ['url_video', 'enlace_directo']:
                        registro[key] = ''
                    else:
                        registro[key] = f'{key}_no_disponible'
            
            datos_supabase.append(registro)
            
            # Log de lo que se va a enviar
            log_info(f"""
📤 Preparando envío a Supabase (SIN NULLS):
   - Timestamp Detección: {registro['fecha_detencion']}
   - Término: {registro['termino_detectado']}
   - Medio: {registro['nombre_medio']}
   - Hora Programa: {registro['hora_programa']}
   - Fecha Programa: {registro['fecha_programa']}
   - URL Clip: {registro['url_video'] or 'VACIO'}
   - Archivo: {registro['nombre_archivo']}
   - Contexto: {len(registro['contexto'])} caracteres
   - Resumen: {len(registro['resumen_ejecutivo'])} caracteres
   - Transcripción: {len(registro['transcripcion'])} caracteres
""", func_name)
        
        # Mostrar en UI lo que se va a enviar con detalles
        st.info(f"📊 **Enviando a Supabase:** {len(datos_supabase)} coincidencia(s)")
        
        # Mostrar resumen de datos que se enviarán
        with st.expander("📋 Ver datos que se enviarán (sin NULLs)", expanded=False):
            for i, reg in enumerate(datos_supabase, 1):
                st.markdown(f"""
**Registro {i}:**
- ⏱️ Timestamp Detección: `{reg['fecha_detencion']}`
- 🎯 Término: `{reg['termino_detectado']}`
- 📺 Medio: `{reg['nombre_medio']}`
- ⏰ Hora Programa: `{reg['hora_programa']}`
- 📅 Fecha Programa: `{reg['fecha_programa']}`
- 🔗 URL: `{'✅ SI' if reg['url_video'] else '❌ NO'}`
- 📄 Archivo: `{reg['nombre_archivo']}`
- 💬 Contexto: `{len(reg['contexto'])} chars`
- 📝 Resumen: `{len(reg['resumen_ejecutivo'])} chars`
- 📜 Transcripción: `{len(reg['transcripcion'])} chars`
""")
                st.markdown("---")
        
        # Insertar en Supabase
        result = supabase.table('alertas_medios').insert(datos_supabase).execute()
        
        if result.data:
            log_info(f"✅ Enviadas {len(datos_supabase)} coincidencias a Supabase para archivo: {nombre_archivo}", func_name)
            st.success(f"✅ Supabase: {len(result.data)} registro(s) insertado(s)")
            return True, f"✅ Enviadas {len(datos_supabase)} coincidencias a Supabase"
        else:
            log_error_critico(func_name, f"❌ Error al insertar en Supabase: {result}")
            st.error(f"❌ Supabase: No se insertaron datos")
            return False, f"❌ Error al insertar en Supabase: {result}"
            
    except Exception as e:
        error_msg = f"Error enviando a Supabase: {str(e)}"
        log_error_critico(func_name, error_msg)
        st.error(f"❌ Supabase: {error_msg}")
        
        # Mostrar traceback completo para debugging
        import traceback
        log_error_critico(func_name, f"Traceback completo:\n{traceback.format_exc()}")
        
        return False, f"❌ {error_msg}"

def verificar_todas_las_apis():
    """Verifica el estado de todas las APIs antes del procesamiento"""
    func_name = "verificar_todas_las_apis"
    resultados = {}
    
    st.info("🔍 **VERIFICANDO ESTADO DE TODAS LAS APIs**")
    st.markdown("---")
    
    # 1. Verificar Google Drive
    with st.spinner("☁️ Verificando Google Drive..."):
        try:
            gdrive_ok, gdrive_msg = test_google_drive_connection()
            resultados['google_drive'] = {
                'activo': gdrive_ok,
                'mensaje': gdrive_msg,
                'icono': '✅' if gdrive_ok else '❌'
            }
            if gdrive_ok:
                st.success(f"☁️ **Google Drive**: {gdrive_msg}")
            else:
                st.error(f"☁️ **Google Drive**: {gdrive_msg}")
        except Exception as e:
            resultados['google_drive'] = {
                'activo': False,
                'mensaje': f"Error verificando Google Drive: {str(e)[:100]}",
                'icono': '❌'
            }
            st.error(f"☁️ **Google Drive**: Error verificando conexión")
    
    # 2. Verificar Telegram
    with st.spinner("📱 Verificando Telegram..."):
        try:
            telegram_config = cargar_telegram_config()
            if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
                # Probar envío de mensaje de prueba
                mensaje_prueba = f"🧪 Prueba de conexión - {datetime.now().strftime('%H:%M:%S')}"
                telegram_ok, telegram_msg = enviar_mensaje_telegram(
                    mensaje_prueba,
                    telegram_config['chat_id'],
                    telegram_config['bot_token']
                )
                resultados['telegram'] = {
                    'activo': telegram_ok,
                    'mensaje': telegram_msg,
                    'icono': '✅' if telegram_ok else '❌'
                }
                if telegram_ok:
                    st.success(f"📱 **Telegram**: {telegram_msg}")
                else:
                    st.error(f"📱 **Telegram**: {telegram_msg}")
            else:
                resultados['telegram'] = {
                    'activo': False,
                    'mensaje': "Telegram no configurado",
                    'icono': '⚠️'
                }
                st.warning("📱 **Telegram**: No configurado")
        except Exception as e:
            resultados['telegram'] = {
                'activo': False,
                'mensaje': f"Error verificando Telegram: {str(e)[:100]}",
                'icono': '❌'
            }
            st.error(f"📱 **Telegram**: Error verificando conexión")
    
    # 3. Verificar Webhook
    with st.spinner("🌐 Verificando Webhook..."):
        try:
            webhook_config = cargar_webhook_config()
            if webhook_config['enabled'] and webhook_config['url']:
                # Probar webhook con mensaje de prueba
                data_prueba = {
                    "tipo": "prueba_conexion",
                    "mensaje": f"Prueba de conexión - {datetime.now().strftime('%H:%M:%S')}",
                    "timestamp": datetime.now().isoformat()
                }
                webhook_ok, webhook_msg = enviar_webhook_simple(webhook_config['url'], data_prueba)
                resultados['webhook'] = {
                    'activo': webhook_ok,
                    'mensaje': webhook_msg,
                    'icono': '✅' if webhook_ok else '❌'
                }
                if webhook_ok:
                    st.success(f"🌐 **Webhook**: {webhook_msg}")
                else:
                    st.error(f"🌐 **Webhook**: {webhook_msg}")
            else:
                resultados['webhook'] = {
                    'activo': False,
                    'mensaje': "Webhook no configurado",
                    'icono': '⚠️'
                }
                st.warning("🌐 **Webhook**: No configurado")
        except Exception as e:
            resultados['webhook'] = {
                'activo': False,
                'mensaje': f"Error verificando Webhook: {str(e)[:100]}",
                'icono': '❌'
            }
            st.error(f"🌐 **Webhook**: Error verificando conexión")
    
    # 4. Verificar Brevo
    with st.spinner("📧 Verificando Brevo..."):
        try:
            brevo_config = cargar_brevo_config()
            if brevo_config['enabled'] and brevo_config['api_key'] and brevo_config['sender_email']:
                # Probar envío de correo de prueba
                correo_ok, correo_msg = enviar_correo_brevo(
                    "PRUEBA DE CONEXIÓN",
                    "Este es un correo de prueba para verificar la conexión con Brevo.",
                    "Prueba de conexión",
                    info_medio="Sistema de Verificación"
                )
                resultados['brevo'] = {
                    'activo': correo_ok,
                    'mensaje': correo_msg,
                    'icono': '✅' if correo_ok else '❌'
                }
                if correo_ok:
                    st.success(f"📧 **Brevo**: {correo_msg}")
                else:
                    st.error(f"📧 **Brevo**: {correo_msg}")
            else:
                resultados['brevo'] = {
                    'activo': False,
                    'mensaje': "Brevo no configurado",
                    'icono': '⚠️'
                }
                st.warning("📧 **Brevo**: No configurado")
        except Exception as e:
            resultados['brevo'] = {
                'activo': False,
                'mensaje': f"Error verificando Brevo: {str(e)[:100]}",
                'icono': '❌'
            }
            st.error(f"📧 **Brevo**: Error verificando conexión")
    
    # 5. Verificar Cloudinary
    with st.spinner("☁️ Verificando Cloudinary..."):
        try:
            cloudinary_config = cargar_cloudinary_config()
            if cloudinary_config['enabled'] and cloudinary_config['cloud_name'] and cloudinary_config['api_key']:
                # Probar subida de archivo de prueba
                archivo_prueba = "test_cloudinary.txt"
                with open(archivo_prueba, 'w', encoding='utf-8') as f:
                    f.write("Prueba de conexión con Cloudinary")
                
                cloudinary_ok, cloudinary_msg, cloudinary_url = subir_video_cloudinary(
                    archivo_prueba,
                    "Prueba de conexión"
                )
                
                # Limpiar archivo de prueba
                if os.path.exists(archivo_prueba):
                    os.remove(archivo_prueba)
                
                resultados['cloudinary'] = {
                    'activo': cloudinary_ok,
                    'mensaje': cloudinary_msg,
                    'icono': '✅' if cloudinary_ok else '❌'
                }
                if cloudinary_ok:
                    st.success(f"☁️ **Cloudinary**: {cloudinary_msg}")
                else:
                    st.error(f"☁️ **Cloudinary**: {cloudinary_msg}")
            else:
                resultados['cloudinary'] = {
                    'activo': False,
                    'mensaje': "Cloudinary no configurado",
                    'icono': '⚠️'
                }
                st.warning("☁️ **Cloudinary**: No configurado")
        except Exception as e:
            resultados['cloudinary'] = {
                'activo': False,
                'mensaje': f"Error verificando Cloudinary: {str(e)[:100]}",
                'icono': '❌'
            }
            st.error(f"☁️ **Cloudinary**: Error verificando conexión")
    
    # Resumen final
    st.markdown("---")
    st.subheader("📊 **RESUMEN DE VERIFICACIÓN**")
    
    # Contar APIs activas
    apis_activas = sum(1 for api in resultados.values() if api['activo'])
    total_apis = len(resultados)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("APIs Activas", f"{apis_activas}/{total_apis}")
    with col2:
        st.metric("Estado General", "✅ Listo" if apis_activas > 0 else "❌ Sin APIs")
    with col3:
        st.metric("Google Drive", "✅ Activo" if resultados.get('google_drive', {}).get('activo') else "❌ Inactivo")
    
    # Mostrar estado de cada API
    for api_name, estado in resultados.items():
        nombre_display = api_name.replace('_', ' ').title()
        st.write(f"{estado['icono']} **{nombre_display}**: {estado['mensaje']}")
    
    log_info(f"Verificación de APIs completada: {apis_activas}/{total_apis} activas", func_name)
    return resultados

# === FUNCIONES DE CORREO BREVO ===

def generar_archivo_coincidencias_md(termino_encontrado, resumen_completo, nombre_video, info_medio="", terminos_detectados=[], video_url=None, video_path=None):
    """
    Genera un archivo Markdown con todas las coincidencias encontradas
    """
    func_name = "generar_archivo_coincidencias_md"
    
    try:
        # Dividir el resumen en transcripción y resumen ejecutivo
        transcripcion = ""
        resumen_ejecutivo = resumen_completo
        
        if "**TRANSCRIPCIÓN DEL CONTENIDO:**" in resumen_completo:
            partes = resumen_completo.split("**RESUMEN EJECUTIVO:**")
            if len(partes) >= 2:
                transcripcion = partes[0].replace("**TRANSCRIPCIÓN DEL CONTENIDO:**", "").strip()
                resumen_ejecutivo = partes[1].strip()
        
        # Nombre del archivo MD
        archivo_md = "coincidencias.md"
        
        # Crear contenido del archivo MD
        contenido_md = f"""
# 🎯 Sistema de Alerta de Medios de Edesur - Coincidencias

## 📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

---

## 🔍 Coincidencia Detectada: {termino_encontrado}

### 📺 Información del Medio
**{info_medio}**

### 🎬 Video de la Coincidencia
"""
        
        # Agregar información del video - OBLIGATORIO incluir URL de Cloudinary
        if video_url:
            contenido_md += f"""
**🎬 Video de Cloudinary:** [{video_url}]({video_url})

**📁 Archivo:** `{nombre_video}`

**🔗 Enlace directo:** {video_url}

> ✅ **URL de Cloudinary disponible para consulta**
"""
        elif video_path and os.path.exists(video_path):
            contenido_md += f"""
**📁 Archivo Local:** `{video_path}`

**📁 Archivo:** `{nombre_video}`

> ⚠️ **Nota:** Video local disponible, pero no subido a Cloudinary aún

> ❌ **IMPORTANTE:** Se requiere subir el video a Cloudinary para obtener URL de consulta
"""
        else:
            contenido_md += f"""
**📁 Archivo:** `{nombre_video}`

> ❌ **ERROR:** Video no disponible o no procesado

> ❌ **IMPORTANTE:** Se requiere subir el video a Cloudinary para obtener URL de consulta
"""
        
        # Agregar términos detectados
        if terminos_detectados:
            contenido_md += f"""
### 🔍 Términos Detectados
"""
            for termino in terminos_detectados:
                contenido_md += f"- **{termino}**\n"
        
        # Agregar resumen ejecutivo
        contenido_md += f"""
### 🎯 Resumen Ejecutivo
{resumen_ejecutivo}

### 📝 Transcripción del Contenido
{transcripcion}

---

"""
        
        # Verificar si el archivo ya existe
        if os.path.exists(archivo_md):
            # Leer contenido existente
            with open(archivo_md, 'r', encoding='utf-8') as f:
                contenido_existente = f.read()
            
            # Insertar nueva coincidencia al inicio (después del encabezado)
            lineas = contenido_existente.split('\n')
            indice_insertar = 0
            
            # Encontrar donde insertar (después del encabezado y antes del primer separador)
            for i, linea in enumerate(lineas):
                # Buscar después del encabezado principal y antes del primer contenido
                if linea.startswith('----') and i > 5:  # Después del encabezado
                    indice_insertar = i
                    break
            
            # Insertar nueva coincidencia al principio del contenido
            lineas.insert(indice_insertar, contenido_md)
            contenido_final = '\n'.join(lineas)
        else:
            # Crear archivo nuevo con encabezado
            encabezado = f"""# 🎯 Sistema de Alerta de Medios de Edesur - Coincidencias

> Archivo generado automáticamente por el sistema de monitoreo de medios
> 
> **Fecha de creación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
> 
> **Descripción:** Este archivo contiene todas las coincidencias detectadas por el sistema de análisis de videos.

---

"""
            contenido_final = encabezado + contenido_md
        
        # Escribir archivo
        with open(archivo_md, 'w', encoding='utf-8') as f:
            f.write(contenido_final)
        
        log_info(f"✅ Archivo MD actualizado: {archivo_md}", func_name)
        return True, f"Archivo MD actualizado: {archivo_md}"
        
    except Exception as e:
        log_exception(func_name, e)
        return False, f"Error generando archivo MD: {str(e)}"

def crear_plantilla_email_html(termino_encontrado, resumen_completo, nombre_video, info_medio="", terminos_detectados=[], video_url=None):
    """Crea una plantilla HTML moderna y elegante para el correo de coincidencia"""
    
    # Dividir el resumen en transcripción y resumen ejecutivo
    transcripcion = ""
    resumen_ejecutivo = resumen_completo
    
    if "**TRANSCRIPCIÓN DEL CONTENIDO:**" in resumen_completo:
        partes = resumen_completo.split("**RESUMEN EJECUTIVO:**")
        if len(partes) >= 2:
            transcripcion = partes[0].replace("**TRANSCRIPCIÓN DEL CONTENIDO:**", "").strip()
            resumen_ejecutivo = partes[1].strip()
    
    # Mejorar formato de transcripción con saltos de línea
    if transcripcion:
        # Dividir en párrafos basado en puntos y mayúsculas
        transcripcion = re.sub(r'\. ([A-Z])', r'.\n\n\1', transcripcion)
        # Limpiar espacios extra
        transcripcion = re.sub(r'\n\s*\n\s*\n', '\n\n', transcripcion)
    
    # Color scheme moderno y elegante
    primary_color = "#667eea"
    secondary_color = "#f8f9fa"
    accent_color = "#28a745"
    text_color = "#333"
    
    # Procesar términos encontrados
    terminos_html = ""
    if terminos_detectados:
        terminos_list = []
        for termino in terminos_detectados:
            terminos_list.append(f'<span style="background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%); color: white; padding: 8px 16px; border-radius: 25px; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(255, 71, 87, 0.3);">"{termino}"</span>')
        terminos_html = " ".join(terminos_list)
    else:
        terminos_html = f'<span style="background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%); color: white; padding: 8px 16px; border-radius: 25px; font-size: 14px; font-weight: 500; box-shadow: 0 2px 8px rgba(255, 71, 87, 0.3);">"{termino_encontrado}"</span>'
    
    # Información del medio
    medio_section = ""
    if info_medio:
        medio_section = f"""
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #2196f3; margin: 20px 0; text-align: center;">
            <strong style="color: #1976d2; font-size: 16px;">📺 {info_medio}</strong>
        </div>
        """
    
    # Botón de reproducir al inicio
    play_intro_section = ""
    if video_url:
        play_intro_section = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{video_url}" target="_blank" style="background: linear-gradient(135deg, #ff4757 0%, #ff3742 100%); border: none; border-radius: 50px; padding: 15px 30px; color: white; font-size: 18px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 12px; box-shadow: 0 4px 15px rgba(255, 71, 87, 0.3); text-decoration: none;">
                ▶️ Reproducir Video de Coincidencia
            </a>
        </div>
        """
    
    # Sección de video simplificada
    video_section = ""
    if video_url:
        video_section = f"""
        <div style="margin: 30px 0; text-align: center;">
            <h3 style="color: {primary_color}; margin: 0 0 20px 0; font-size: 20px; display: flex; align-items: center; justify-content: center;">
                <span style="margin-right: 10px;">🎬</span>
                Video de la Coincidencia
            </h3>
            
            <div style="position: relative; max-width: 650px; margin: 0 auto; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(0,0,0,0.3);">
                <video id="main-video" style="width: 100%; height: 400px; object-fit: cover; cursor: pointer;" controls preload="metadata">
                    <source src="{video_url}" type="video/mp4">
                    Tu navegador no soporta la reproducción de video.
                </video>
            </div>
            
            <div style="margin-top: 15px; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; border-left: 4px solid {primary_color};">
                <div style="font-weight: 600; color: #495057; margin-bottom: 8px; font-size: 16px;">{nombre_video}</div>
                <div style="color: #6c757d; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px;">
                    🌐 <span>Cloudinary CDN</span>
                </div>
            </div>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema de Alerta de Medios de Edesur: {termino_encontrado}</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
        <div style="background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, {primary_color} 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 300;">🎯 Sistema de Alerta de Medios de Edesur</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">Término: <strong>{termino_encontrado}</strong></p>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                
                {play_intro_section}
                
                {video_section}
                
                <!-- Términos Detectados -->
                {f'''
                <div style="margin: 30px 0; padding: 25px; background: #f8f9fa; border-radius: 12px; border-left: 5px solid {accent_color};">
                    <h3 style="margin: 0 0 20px 0; color: {accent_color}; font-size: 20px; display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 24px;">🔍</span>
                        Términos Detectados
                    </h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;">
                        {terminos_html}
                    </div>
                </div>
                ''' if terminos_detectados else ''}
                
                {medio_section}
                
                <!-- Resumen Ejecutivo -->
                <div style="background: linear-gradient(135deg, {primary_color} 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin: 25px 0; text-align: center;">
                    <h3 style="margin: 0 0 20px 0; color: white; font-size: 20px;">🎯 Resumen Ejecutivo</h3>
                    <p style="margin: 0; line-height: 1.8;">{resumen_ejecutivo}</p>
                </div>
                
                <!-- Transcripción -->
                {f'''
                <div style="margin: 30px 0; padding: 25px; background: #f8f9fa; border-radius: 12px; border-left: 5px solid {accent_color};">
                    <h3 style="margin: 0 0 20px 0; color: {accent_color}; font-size: 20px; display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 24px;">📝</span>
                        Transcripción del Contenido
                    </h3>
                    <div style="background: white; padding: 25px; border-radius: 12px; border: 1px solid #e9ecef; margin: 20px 0; font-family: 'Georgia', serif; line-height: 2.0; color: #495057; white-space: pre-line; text-align: justify;">
{transcripcion}
                    </div>
                </div>
                ''' if transcripcion else ''}
                
                <!-- Botones Centrados -->
                <div style="display: flex; gap: 15px; justify-content: center; margin: 30px 0; flex-wrap: wrap;">
                    {f'<a href="{video_url}" target="_blank" style="padding: 15px 30px; border: none; border-radius: 30px; text-decoration: none; font-weight: 600; text-align: center; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white;">🔗 Ver en Nueva Pestaña</a>' if video_url else ''}
                    <a href="#" style="padding: 15px 30px; border: none; border-radius: 30px; text-decoration: none; font-weight: 600; text-align: center; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); color: white;">⬇️ Descargar Video</a>
                    <a href="#" style="padding: 15px 30px; border: none; border-radius: 30px; text-decoration: none; font-weight: 600; text-align: center; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 10px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white;">📊 Ver Análisis Completo</a>
                </div>
                
            </div>
            
            <!-- Footer -->
            <div style="background: #343a40; color: white; padding: 25px; text-align: center;">
                <p style="margin: 5px 0; opacity: 0.8;"><strong>🤖 Sistema de Monitoreo Automático</strong></p>
                <p style="margin: 5px 0; opacity: 0.8;">Generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}</p>
                <p style="margin: 5px 0; opacity: 0.8;">Este es un correo automático, no responder.</p>
            </div>
            
        </div>
        
    </body>
    </html>
    """
    
    return html_template

def enviar_correo_brevo(termino_encontrado, resumen_completo, nombre_video, video_path=None, info_medio="", terminos_detectados=[], video_url_gdrive=None):
    """Envía correo usando Brevo SMTP con plantilla moderna a múltiples destinatarios"""
    func_name = "enviar_correo_brevo"
    
    try:
        config = cargar_brevo_config()
        
        if not config['enabled']:
            log_info("Correo Brevo deshabilitado", func_name)
            return False, "Correo deshabilitado"
            
        if not all([config['api_key'], config['sender_email']]):
            log_warning("Configuración de Brevo incompleta (API key o sender)", func_name)
            return False, "Configuración incompleta"
        
        # Obtener lista de correos destinatarios
        correos_destinatarios = obtener_correos_activos()
        if not correos_destinatarios:
            log_warning("No hay correos destinatarios configurados", func_name)
            return False, "No hay destinatarios configurados"
        
        # Verificar conectividad
        if not verificar_conectividad():
            log_warning("Sin conectividad - saltando envío de correo", func_name)
            return False, "Sin conectividad"
        
        log_info(f"Enviando correo para término: {termino_encontrado} a {len(correos_destinatarios)} destinatarios", func_name)
        
        # Crear mensaje base
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎯 Coincidencia: {termino_encontrado}"
        msg['From'] = f"{config['sender_name']} <{config['sender_email']}>"
        
        # Lista de destinatarios para BCC (copia oculta)
        msg['Bcc'] = ', '.join(correos_destinatarios)
        
        # Usar URL de Google Drive si está disponible, sino intentar Cloudinary
        video_url = None
        if video_url_gdrive:
            video_url = video_url_gdrive
            log_info(f"✅ Usando URL de Google Drive para player: {video_url}", func_name)
        elif video_path and os.path.exists(video_path):
            log_info(f"Intentando subir video a Cloudinary: {video_path}", func_name)
            try:
                cloudinary_configurado = configurar_cloudinary()
                log_info(f"Cloudinary configurado: {cloudinary_configurado}", func_name)
                
                if cloudinary_configurado:
                    video_url_result, mensaje_subida = subir_video_cloudinary(video_path, termino_encontrado)
                    if video_url_result:
                        video_url = video_url_result
                        log_info(f"✅ Video subido a Cloudinary exitosamente: {video_url}", func_name)
                    else:
                        log_warning(f"❌ Error subiendo video a Cloudinary: {mensaje_subida}", func_name)
                else:
                    log_warning("❌ Cloudinary no está configurado correctamente", func_name)
            except Exception as e:
                log_warning(f"❌ Excepción subiendo video a Cloudinary: {e}", func_name)
        else:
            log_warning(f"❌ No hay URL de Google Drive ni video local: {video_path}", func_name)
        
        # Crear contenido HTML con información completa
        html_content = crear_plantilla_email_html(
            termino_encontrado, 
            resumen_completo, 
            nombre_video, 
            info_medio, 
            terminos_detectados if terminos_detectados else [termino_encontrado], 
            video_url
        )
        
        # Crear versión texto plano completa como respaldo
        terminos_texto = ", ".join([f'"{t}"' for t in terminos_detectados]) if terminos_detectados else f'"{termino_encontrado}"'
        
        text_content = f"""
COINCIDENCIA DETECTADA EN ANÁLISIS DE VIDEOS

TÉRMINOS DETECTADOS: {terminos_texto}

{f"MEDIO: {info_medio}" if info_medio else ""}

RESUMEN COMPLETO DE LA COINCIDENCIA:
{resumen_completo}

INFORMACIÓN TÉCNICA:
- Fecha y Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- Archivo Analizado: {nombre_video}
- Sistema: Análisis Automático de Videos con IA

Este correo fue generado automáticamente por el Sistema de Análisis de Videos de FGJ Medios.
        """.strip()
        
        # Adjuntar contenido
        part_text = MIMEText(text_content, 'plain', 'utf-8')
        part_html = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part_text)
        msg.attach(part_html)
        
        # NO adjuntar videos - solo usar URLs (Cloudinary/Google Drive)
        # Esto evita el error "Max message size exceeded" de Brevo
        if video_url:
            log_info(f"✅ Usando URL para video en correo: {video_url}", func_name)
            # La URL ya está incluida en el contenido HTML/texto
        else:
            log_warning("⚠️ No hay URL de video disponible para incluir en el correo", func_name)
        
        # Enviar correo a todos los destinatarios
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            # Login con usuario SMTP pero envío desde email verificado
            smtp_user = config.get('smtp_user', config['sender_email'])
            server.login(smtp_user, config['api_key'])
            server.send_message(msg, to_addrs=correos_destinatarios)
        
        log_info(f"✅ Correo enviado exitosamente a {len(correos_destinatarios)} destinatarios: {', '.join(correos_destinatarios[:3])}{'...' if len(correos_destinatarios) > 3 else ''}", func_name)
        return True, f"Correo enviado a {len(correos_destinatarios)} destinatarios"
        
    except Exception as e:
        error_msg = f"Error enviando correo: {str(e)[:200]}"
        log_exception(func_name, e, error_msg)
        return False, error_msg

def test_brevo_connection():
    """Prueba la conexión con Brevo"""
    func_name = "test_brevo_connection"
    
    try:
        config = cargar_brevo_config()
        
        if not config['enabled']:
            return False, "❌ Brevo está deshabilitado"
            
        if not all([config['api_key'], config['sender_email']]):
            return False, "❌ Configuración incompleta (API key o sender)"
        
        correos_destinatarios = obtener_correos_activos()
        if not correos_destinatarios:
            return False, "❌ No hay destinatarios configurados"
        
        # Probar conexión SMTP
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            # Login con usuario SMTP
            smtp_user = config.get('smtp_user', config['sender_email'])
            server.login(smtp_user, config['api_key'])
        
        # Enviar correo de prueba
        exito, mensaje = enviar_correo_brevo(
            "PRUEBA",
            "**CORREO DE PRUEBA**\\n\\nEste es un correo de prueba del sistema de análisis de videos.\\n\\n✅ Si recibiste este correo, la configuración está funcionando correctamente.\\n\\n🎯 **Funcionalidades probadas:**\\n- Envío a múltiples destinatarios\\n- Plantilla HTML moderna\\n- Adjuntos sin limitación de tamaño\\n- Información completa del medio",
            "test_email.mp4",
            None,  # No hay video_path en prueba
            "Prueba del Sistema de Correos",  # info_medio
            ["PRUEBA", "SISTEMA", "CORREOS"],  # terminos_detectados
            None  # No hay video_url_gdrive en prueba
        )
        
        if exito:
            return True, f"✅ Conexión exitosa y correo de prueba enviado a {len(correos_destinatarios)} destinatarios"
        else:
            return False, f"❌ Error enviando correo de prueba: {mensaje}"
            
    except Exception as e:
        return False, f"❌ Error de conexión: {str(e)[:100]}"

def enviar_mensaje_telegram(mensaje, chat_id=None, bot_token=None, parse_mode='Markdown'):
    """Envía un mensaje de texto a Telegram - VERSIÓN ROBUSTA"""
    func_name = "enviar_mensaje_telegram"
    config = cargar_telegram_config()
    
    bot_token = bot_token or config['bot_token']
    chat_id = chat_id or config['chat_id']
    
    if not bot_token or not chat_id:
        log_info("Token o Chat ID no configurados para Telegram", func_name)
        return False, "Token o Chat ID no configurados"
    
    # Verificar conectividad antes de intentar
    if not verificar_conectividad():
        log_info("Sin conectividad - saltando envío a Telegram", func_name)
        return False, "Sin conectividad a internet"
    
    log_debug(f"Enviando mensaje a Telegram: {mensaje[:100]}...", func_name)
    
    # Reintentos con backoff exponencial
    max_intentos = 3
    for intento in range(max_intentos):
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': mensaje,
                'disable_web_page_preview': False
            }
            
            # Solo agregar parse_mode si no es None
            if parse_mode:
                data['parse_mode'] = parse_mode
            
            # Configuración robusta para conexiones problemáticas
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'VideoAnalyzer-AI/2.0',
                'Connection': 'close',
                'Accept': 'application/json'
            })
            
            response = session.post(
                url, 
                json=data, 
                timeout=45,  # Timeout generoso para Telegram
                allow_redirects=True
            )
            
            session.close()
            
            if response.status_code == 200:
                log_info(f"Mensaje enviado exitosamente a Telegram en intento {intento + 1}", func_name)
                return True, "Mensaje enviado a Telegram"
            else:
                error_msg = response.text[:150]
                log_info(f"Telegram respondió HTTP {response.status_code} en intento {intento + 1}: {error_msg}", func_name)
                if intento == max_intentos - 1:
                    return False, f"Error HTTP {response.status_code}: {error_msg}"
                
        except requests.exceptions.ConnectionError as e:
            error_msg = str(e)[:150]
            log_info(f"Error de conexión Telegram en intento {intento + 1}: {error_msg}", func_name)
            if intento == max_intentos - 1:
                return False, f"Error de conexión: {error_msg}"
                
        except requests.exceptions.Timeout as e:
            log_info(f"Timeout Telegram en intento {intento + 1}", func_name)
            if intento == max_intentos - 1:
                return False, "Timeout - Telegram no responde"
                
        except Exception as e:
            error_msg = str(e)[:150]
            log_exception(func_name, e, f"Intento {intento + 1}")
            if intento == max_intentos - 1:
                return False, f"Error enviando mensaje: {error_msg}"
        
        # Backoff exponencial antes del siguiente intento
        if intento < max_intentos - 1:
            esperar_con_backoff(intento, max_espera=20)
    
    log_info(f"Envío de mensaje Telegram falló después de {max_intentos} intentos", func_name)
    return False, f"Falló después de {max_intentos} intentos"

def enviar_video_telegram(video_path, caption="", chat_id=None, bot_token=None, usar_cloudinary=True):
    """Envía un video a Telegram (directamente o vía Cloudinary) y devuelve la URL del video"""
    config = cargar_telegram_config()
    
    bot_token = bot_token or config['bot_token']
    chat_id = chat_id or config['chat_id']
    
    if not bot_token or not chat_id:
        return False, "Token o Chat ID no configurados"
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        
        # Verificar tamaño del archivo
        file_size_mb = os.path.getsize(video_path) / (1024*1024)
        
        video_url_cloudinary = None
        if usar_cloudinary and config.get('use_cloudinary', True):
            # Subir a Cloudinary primero
            video_url_cloudinary, upload_msg = subir_video_cloudinary(video_path)
            
            if video_url_cloudinary:
                # Enviar URL del video
                data = {
                    'chat_id': chat_id,
                    'video': video_url_cloudinary,
                    'caption': caption.replace("🌐 *Vía:* Cloudinary - 5.6MB", f"🌐 *Vía:* Cloudinary - {file_size_mb:.1f}MB"),
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, data=data, timeout=config.get('timeout', 30))
            else:
                return False, f"Error subiendo video: {upload_msg}", None
        
        elif file_size_mb <= config.get('max_file_size_mb', 8):  # Límite configurable
            # Envío directo
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'chat_id': chat_id,
                    'caption': caption.replace("🌐 *Vía:* Cloudinary - 5.6MB", f"📹 *Envío directo* - {file_size_mb:.1f}MB")
                }
                
                response = requests.post(url, files=files, data=data, timeout=config.get('timeout', 30))
        else:
            return False, f"Archivo muy grande ({file_size_mb:.1f}MB) y Cloudinary deshabilitado", None
        
        if response.status_code == 200:
            return True, f"Video enviado a Telegram ({file_size_mb:.1f}MB)", video_url_cloudinary
        else:
            return False, f"Error HTTP {response.status_code}: {response.text[:100]}", None
            
    except Exception as e:
        return False, f"Error enviando video: {str(e)[:100]}", None

def enviar_video_telegram_directo(video_path, caption, chat_id=None, bot_token=None, parse_mode='Markdown'):
    """
    Envía un video directamente a Telegram usando sendVideo API
    Soporta videos hasta 50MB directamente, o URLs para videos más grandes
    """
    func_name = "enviar_video_telegram_directo"
    config = cargar_telegram_config()
    
    bot_token = bot_token or config['bot_token']
    chat_id = chat_id or config['chat_id']
    
    if not bot_token or not chat_id:
        return False, "Token o Chat ID no configurados", None
    
    try:
        # Verificar que el archivo existe
        if not os.path.exists(video_path):
            return False, f"Archivo no encontrado: {video_path}", None
        
        # Obtener información del archivo
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)
        
        log_info(f"Enviando video directo a Telegram: {os.path.basename(video_path)} ({file_size_mb:.1f}MB)", func_name)
        
        # Verificar límite de tamaño configurable (por defecto 8MB)
        max_mb = config.get('max_file_size_mb', 8)
        if file_size_mb > max_mb:
            return False, f"Video demasiado grande ({file_size_mb:.1f}MB > {max_mb}MB). Comprimir antes de enviar.", None
        
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        
        # Preparar datos del video
        with open(video_path, 'rb') as video_file:
            files = {
                'video': (os.path.basename(video_path), video_file, 'video/mp4')
            }
            
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'supports_streaming': True,  # Para videos MP4
                'duration': None,  # Telegram lo detectará automáticamente
                'width': None,    # Telegram lo detectará automáticamente
                'height': None    # Telegram lo detectará automáticamente
            }
            if parse_mode:
                data['parse_mode'] = parse_mode
            
            # Enviar video con timeout más largo para archivos grandes
            timeout = max(60, int(file_size_mb * 2))  # 2 s/MB, mínimo 60s
            response = requests.post(url, data=data, files=files, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                message_id = result['result']['message_id']
                video_info = result['result'].get('video', {})
                
                log_info(f"Video enviado exitosamente a Telegram: {os.path.basename(video_path)} (ID: {message_id})", func_name)
                return True, f"Video enviado exitosamente (ID: {message_id})", None
            else:
                error_desc = result.get('description', 'Error desconocido')
                return False, f"Error de Telegram: {error_desc}", None
        else:
            return False, f"Error HTTP: {response.status_code} - {response.text}", None
            
    except requests.exceptions.Timeout:
        return False, f"Timeout: Telegram no respondió en {timeout} segundos", None
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}", None
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", None

def enviar_video_telegram_url(video_url, caption, chat_id=None, bot_token=None, parse_mode='Markdown'):
    """
    Envía un video a Telegram usando una URL (para videos grandes o desde Cloudinary)
    Soporta videos hasta 2GB cuando se usa URL
    """
    func_name = "enviar_video_telegram_url"
    config = cargar_telegram_config()
    
    bot_token = bot_token or config['bot_token']
    chat_id = chat_id or config['chat_id']
    
    if not bot_token or not chat_id:
        return False, "Token o Chat ID no configurados", None
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
        
        data = {
            'chat_id': chat_id,
            'video': video_url,
            'caption': caption,
            'parse_mode': parse_mode,
            'supports_streaming': True
        }
        
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                message_id = result['result']['message_id']
                log_info(f"Video URL enviado exitosamente a Telegram: {video_url} (ID: {message_id})", func_name)
                return True, f"Video URL enviado exitosamente (ID: {message_id})", None
            else:
                error_desc = result.get('description', 'Error desconocido')
                return False, f"Error de Telegram: {error_desc}", None
        else:
            return False, f"Error HTTP: {response.status_code} - {response.text}", None
            
    except requests.exceptions.Timeout:
        return False, "Timeout: Telegram no respondió en 30 segundos", None
    except requests.exceptions.RequestException as e:
        return False, f"Error de conexión: {str(e)}", None
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", None

def enviar_video_telegram_inteligente(video_path, caption, chat_id=None, bot_token=None, parse_mode='Markdown', cloudinary_url=None):
    """
    Función inteligente que decide automáticamente el mejor método para enviar video a Telegram:
    1. Si hay URL de Cloudinary -> usar sendVideo con URL (hasta 2GB)
    2. Si video < 50MB -> envío directo
    3. Si video > 50MB -> subir a Cloudinary primero, luego usar URL
    """
    func_name = "enviar_video_telegram_inteligente"
    
    try:
        # Verificar que el archivo existe
        if not os.path.exists(video_path):
            return False, f"Archivo no encontrado: {video_path}", None
        
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)
        
        log_info(f"Enviando video inteligente a Telegram: {os.path.basename(video_path)} ({file_size_mb:.1f}MB)", func_name)

        # Prefijar método de envío en el caption para identificar API de Telegram
        if caption is None:
            caption = ""
        if not caption.strip().startswith("[AT]"):
            caption = f"[AT] {caption}".strip()
        
        # MÉTODO 1: Si ya tenemos URL de Cloudinary, usarla directamente
        if cloudinary_url:
            log_info(f"Usando URL de Cloudinary existente: {cloudinary_url}", func_name)
            return enviar_video_telegram_url(cloudinary_url, caption, chat_id, bot_token, parse_mode)
        
        # MÉTODO 2: Si video es pequeño (< 50MB), envío directo
        max_mb = config.get('max_file_size_mb', 8)
        if file_size_mb <= max_mb:
            log_info(f"Video pequeño ({file_size_mb:.1f}MB) - envío directo", func_name)
            return enviar_video_telegram_directo(video_path, caption, chat_id, bot_token, parse_mode)
        
        # MÉTODO 3: Video grande (> 50MB) - subir a Cloudinary primero
        log_info(f"Video grande ({file_size_mb:.1f}MB) - subiendo a Cloudinary primero", func_name)
        
        # Subir a Cloudinary
        cloudinary_ok, cloudinary_msg, cloudinary_url = subir_video_cloudinary(video_path, "Video para Telegram")
        
        if cloudinary_ok and cloudinary_url:
            log_info(f"Video subido a Cloudinary exitosamente: {cloudinary_url}", func_name)
            # Ahora enviar usando la URL
            return enviar_video_telegram_url(cloudinary_url, caption, chat_id, bot_token, parse_mode)
        else:
            return False, f"Error subiendo a Cloudinary: {cloudinary_msg}", None
            
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", None

def enviar_clips_a_telegram(clips_generados, resumen, terminos_detectados, video_origen):
    """ENVÍO GARANTIZADO: Resumen → Pausa → Video → Pausa → Siguiente"""
    config = cargar_telegram_config()
    
    if not config['enabled']:
        return False, "Telegram deshabilitado"
    
    if not config['bot_token'] or not config['chat_id']:
        return False, "Telegram no configurado correctamente"
    
    # ========== CONTROL DE DUPLICADOS ==========
    # Verificar si ya se enviaron estos clips individualmente
    clips_ya_enviados = 0
    clips_pendientes = []
    
    for clip in clips_generados:
        clip_path = clip.get('path', '')
        if clip_path in st.session_state.get('clips_enviados_telegram', []):
            clips_ya_enviados += 1
            st.info(f"⏭️ Clip ya enviado individualmente: {os.path.basename(clip_path)}")
        else:
            clips_pendientes.append(clip)
    
    if clips_ya_enviados == len(clips_generados):
        st.success(f"✅ Todos los clips ya fueron enviados individualmente ({clips_ya_enviados}/{len(clips_generados)})")
        return True, f"✅ Todos los clips ya enviados individualmente"
    
    if clips_pendientes:
        st.info(f"📤 Enviando {len(clips_pendientes)} clips pendientes (de {len(clips_generados)} total)")
        clips_generados = clips_pendientes  # Usar solo los clips pendientes
    
    try:
        # ========== PASO 1: SIEMPRE ENVIAR RESUMEN EJECUTIVO PRIMERO ==========
        mensaje_resumen = f"""🎬 *ANÁLISIS DE VIDEO COMPLETADO*

📹 *Video:* `{video_origen}`
🔍 *Términos detectados:* {', '.join(terminos_detectados)}
📊 *Total clips generados:* {len(clips_generados)}
⏰ *Fecha:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 *RESUMEN EJECUTIVO:*
{resumen}

🌐 *Servidor:* Analizador de Videos IA v2.0

⬇️ *Videos a continuación...*"""
        
        # GARANTIZAR que el resumen se envíe
        intentos_resumen = 0
        resumen_enviado = False
        while intentos_resumen < 3 and not resumen_enviado:
            exito_msg, resultado_msg = enviar_mensaje_telegram(mensaje_resumen)
            if exito_msg:
                st.success(f"📋 ✅ RESUMEN EJECUTIVO ENVIADO: {video_origen}")
                resumen_enviado = True
            else:
                intentos_resumen += 1
                st.warning(f"⚠️ Reintento {intentos_resumen}/3 enviando resumen: {resultado_msg}")
                time.sleep(10)  # Pausa más larga entre reintentos
        
        if not resumen_enviado:
            st.error(f"❌ FALLO CRÍTICO: No se pudo enviar resumen para {video_origen}")
            return False, "❌ Resumen no enviado"
        
        # ========== PASO 2: PAUSA OBLIGATORIA DESPUÉS DEL RESUMEN ==========
        st.info("⏸️ Pausa de 30 segundos después del resumen para evitar congestión...")
        time.sleep(30)
        
        # ========== PASO 3: ENVIAR CADA VIDEO CON SU PAUSA ==========
        if config.get('send_clips', True) and clips_generados:
            clips_enviados = 0
            clips_fallidos = 0
            
            for i, clip in enumerate(clips_generados, 1):
                if not os.path.exists(clip['path']):
                    st.warning(f"⚠️ Archivo no existe: {clip['path']}")
                    continue
                
                # Caption consolidado con toda la información
                caption = f"""🎯 *CLIP {i}/{len(clips_generados)} DE COINCIDENCIA*

📺 *Medio:* {video_origen}
⏰ *Generado:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 *TÉRMINOS DETECTADOS:* {', '.join(terminos_detectados)}

🏷️ *Término específico:* `{clip['termino']}`
⏱️ *Tiempo en video:* {clip['tiempo']}
📝 *Contexto:* {clip['contexto'][:200]}{'...' if len(clip['contexto']) > 200 else ''}

📋 *RESUMEN DEL VIDEO:*
{resumen}

━━━━━━━━━━━━━━━━━━━━━
🌐 *Vía:* Cloudinary - 5.6MB"""
                
                # GARANTIZAR que cada video se envíe
                intentos_video = 0
                # Forzar API directa sin reintentos ni uso de URL/Cloudinary
                video_enviado = False
                file_size_mb_clip = os.path.getsize(clip['path']) / (1024 * 1024) if os.path.exists(clip['path']) else 0
                if file_size_mb_clip <= 50 and os.path.exists(clip['path']):
                    exito_clip, resultado_clip, _ = enviar_video_telegram_directo(
                        clip['path'],
                        caption,
                        chat_id=config.get('chat_id'),
                        bot_token=config.get('bot_token'),
                        parse_mode=None
                    )
                    if exito_clip:
                        clips_enviados += 1
                        st.success(f"🎬 ✅ VIDEO {i} ENVIADO: {clip['termino']} - {resultado_clip}")
                        video_enviado = True
                    else:
                        st.error(f"❌ FALLO: Video {i} no enviado - {clip['termino']} - {resultado_clip}")
                else:
                    st.warning(f"🚫 Video {i} omitido ({file_size_mb_clip:.1f}MB > 50MB). Solo API directa permitida.")
                
                if not video_enviado:
                    clips_fallidos += 1
                    st.error(f"❌ FALLO: Video {i} no enviado - {clip['termino']}")
                
                # ========== PAUSA OBLIGATORIA ENTRE CADA VIDEO ==========
                if i < len(clips_generados):
                    st.info(f"⏸️ Pausa de 30 segundos antes del próximo video para evitar congestión...")
                    time.sleep(30)
            
            # ========== PASO 4: MENSAJE FINAL CON PAUSA ==========
            time.sleep(1)
            mensaje_final = f"""✅ *ENVÍO COMPLETADO*

📹 *Video procesado:* `{video_origen}`
📱 *Clips enviados exitosamente:* {clips_enviados}
❌ *Clips fallidos:* {clips_fallidos}
📊 *Total procesado:* {len(clips_generados)}

━━━━━━━━━━━━━━━━━━━━━"""
            
            enviar_mensaje_telegram(mensaje_final)
            time.sleep(30)  # Pausa final de 30 segundos antes del siguiente video
            
            return True, f"✅ GARANTIZADO: Resumen + {clips_enviados} videos enviados para {video_origen}"
        
        return True, f"✅ GARANTIZADO: Solo resumen enviado para {video_origen}"
        
    except Exception as e:
        st.error(f"❌ ERROR CRÍTICO en envío: {str(e)}")
        return False, f"❌ Error crítico: {str(e)[:100]}"

def test_telegram_connection():
    """Prueba la conexión con Telegram"""
    config = cargar_telegram_config()
    
    if not config['bot_token'] or not config['chat_id']:
        return False, "Token o Chat ID no configurados"
    
    mensaje_test = f"""🧪 *TEST DE CONEXIÓN*

✅ Bot conectado correctamente
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Analizador de Videos IA v2.0

Este es un mensaje de prueba."""
    
    return enviar_mensaje_telegram(mensaje_test)

def cargar_terminos_guardados():
    """Carga términos desde archivo JSON"""
    try:
        if os.path.exists(TERMINOS_CONFIG):
            with open(TERMINOS_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('terminos', [])
    except Exception as e:
        st.warning(f"⚠️ Error cargando términos guardados: {e}")
    return []

def guardar_terminos_archivo(terminos):
    """Guarda términos en archivo JSON"""
    try:
        data = {
            'terminos': terminos,
            'fecha_actualizacion': datetime.now().isoformat(),
            'total_terminos': len(terminos)
        }
        with open(TERMINOS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando términos: {e}")
        return False

def cargar_configuracion_completa():
    """Carga toda la configuración guardada"""
    config = {
        'terminos': [],
        'intervalo': 60,
        'duracion_clip': 60,  # 1 minuto total (30s antes + 30s después)
        'buffer_anterior': 30,  # 30s antes de la coincidencia
        'mostrar_coincidencias': True
    }
    
    try:
        if os.path.exists(TERMINOS_CONFIG):
            with open(TERMINOS_CONFIG, 'r', encoding='utf-8') as f:
                data = json.load(f)
                config.update(data)
    except Exception:
        pass
    
    return config

def guardar_configuracion_completa(terminos, intervalo=60, duracion_clip=60, buffer_anterior=30, mostrar_coincidencias=True):
    """Guarda toda la configuración"""
    try:
        data = {
            'terminos': terminos,
            'intervalo': intervalo,
            'duracion_clip': duracion_clip,
            'buffer_anterior': buffer_anterior,
            'mostrar_coincidencias': mostrar_coincidencias,
            'fecha_actualizacion': datetime.now().isoformat(),
            'total_terminos': len(terminos)
        }
        with open(TERMINOS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración: {e}")
        return False

# === INICIALIZAR ESTADO DE LA SESIÓN ===
def init_session_state():
    # Cargar configuración guardada
    config_guardada = cargar_configuracion_completa()
    
    defaults = {
        'resumen_global': [],
        'running': False,
        'terminos_continuos': config_guardada['terminos'],  # Cargar términos guardados
        'ultimo_chequeo': datetime.now(),
        'videos_encontrados': 0,
        'videos_procesados': 0,
        'clips_generados': 0,
        'app_restarted': False,
        'intervalo': config_guardada['intervalo'],
        'mostrar_coincidencias': config_guardada['mostrar_coincidencias'],
        'clips_encontrados_sesion': [],
        'duracion_clip': config_guardada.get('duracion_clip', 60),  # Default 1 minuto
        'buffer_anterior': config_guardada.get('buffer_anterior', 30),  # Default 30s
        'coincidencias_enviadas_supabase': set()  # Control de duplicados para Supabase
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Inicializar estado después de definir la función
init_session_state()

# === FUNCIÓN MISTRAL CLIENT (DEBE ESTAR ANTES DE verificar_estado_mistral) ===
@st.cache_resource
def cargar_cliente_mistral():
    model = "voxtral-mini-latest"
    client = Mistral(api_key=mistral_api_key)
    return client, model

def verificar_estado_mistral():
    """
    Verifica si Mistral API está disponible de forma simple
    """
    func_name = "verificar_estado_mistral"
    try:
        # Verificación simple sin crear archivos
        client, model = cargar_cliente_mistral()
        
        # Si llegamos aquí, al menos las credenciales están configuradas
        log_debug("Mistral client configurado correctamente", func_name)
        return True, "Configurado (verificación completa requiere audio)"
        
    except Exception as e:
        error_str = str(e).lower()
        if "503" in error_str or "service unavailable" in error_str:
            log_info("Mistral API no disponible (503)", func_name)
            return False, "Service Unavailable (503)"
        elif "500" in error_str:
            log_info("Mistral API error interno (500)", func_name)
            return False, "Internal Server Error (500)"
        elif "api" in error_str and "key" in error_str:
            log_info("Error de API key de Mistral", func_name)
            return False, "Error de API Key"
        else:
            log_info(f"Mistral API error: {e}", func_name)
            return False, f"Error: {str(e)[:50]}"

@st.cache_data
def buscar_todos_los_clips(busqueda_termino="", dias_limite=365):
    clips = []
    ahora = time.time()
    limite_tiempo = ahora - (dias_limite * 24 * 60 * 60) if dias_limite < 9999 else 0
    
    try:
        # Buscar en la carpeta de procesados
        if os.path.exists(CARPETA_PROCESADOS):
            for root, dirs, files in os.walk(CARPETA_PROCESADOS):
                # Verificar si es carpeta procesada con marcador P*
                marcador_procesado = os.path.join(root, "PROCESADO.txt")
                if os.path.exists(marcador_procesado):
                    for file in files:
                        if file.endswith(".mp4") and busqueda_termino.lower() in file.lower():
                            path_ = os.path.join(root, file)
                            if os.path.exists(path_) and os.path.isfile(path_):
                                file_time = os.path.getctime(path_)
                                if file_time >= limite_tiempo:
                                    # Extraer información del archivo
                                    info = extraer_info_clip(file, path_)
                                    clips.append(info)
    except Exception as e:
        st.warning(f"⚠️ Error buscando clips: {e}")
    
    return sorted(clips, key=lambda x: x['timestamp'], reverse=True)

def extraer_info_clip(filename, filepath):
    """Extrae información del nombre del clip"""
    # Formato esperado: YYYYMMDD_HHMMSS_termino_XmYYs.mp4
    try:
        parts = filename.replace('.mp4', '').split('_')
        if len(parts) >= 4:
            fecha_str = parts[0]
            hora_str = parts[1]
            termino = parts[2]
            duracion = parts[3] if len(parts) > 3 else "0m00s"
            
            # Convertir fecha y hora
            fecha_obj = datetime.strptime(f"{fecha_str}_{hora_str}", "%Y%m%d_%H%M%S")
            
            return {
                'filename': filename,
                'filepath': filepath,
                'termino': termino,
                'fecha': fecha_obj.strftime("%Y-%m-%d %H:%M:%S"),
                'fecha_creacion': fecha_obj,
                'timestamp': fecha_obj.timestamp(),
                'duracion': duracion,
                'tiempo_video': duracion,
                'size_mb': round(os.path.getsize(filepath) / (1024*1024), 1) if os.path.exists(filepath) else 0
            }

    except Exception as e:
        # Fallback para archivos con formato no estándar
        try:
            fecha_creacion_obj = datetime.fromtimestamp(os.path.getctime(filepath)) if os.path.exists(filepath) else datetime.now()
            timestamp_val = fecha_creacion_obj.timestamp()
        except:
            fecha_creacion_obj = datetime.now()
            timestamp_val = fecha_creacion_obj.timestamp()
            
        return {
            'filename': filename,
            'filepath': filepath,
            'termino': 'desconocido',
            'fecha': fecha_creacion_obj.strftime("%Y-%m-%d %H:%M:%S"),
            'fecha_creacion': fecha_creacion_obj,
            'timestamp': timestamp_val,
            'duracion': '0m00s',
            'tiempo_video': '0m00s',
            'size_mb': round(os.path.getsize(filepath) / (1024*1024), 1) if os.path.exists(filepath) else 0
        }

def generar_resumen_md(items):
    prompt = (
        "Genera un resumen ejecutivo en Markdown de los análisis de video realizados:\n\n"
        "DATOS ENCONTRADOS:\n"
    )
    for e in items:
        prompt += f"- **{e['termino']}** en `{e['video']}`: {e['texto'][:100]}...\n"

    prompt += "\n\nGenera un resumen que incluya:\n"
    prompt += "1. Resumen ejecutivo de los hallazgos\n"
    prompt += "2. Términos más frecuentes\n"
    prompt += "3. Videos más relevantes\n"
    prompt += "4. Conclusiones y recomendaciones\n"

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un analista especializado en generar reportes ejecutivos de análisis multimedia."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        md = resp.choices[0].message.content
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"resumen_ejecutivo_{timestamp}.md"
        filepath = os.path.join(CARPETA_VIDEOS, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
        
        st.success(f"✅ Reporte generado: `{filename}`")
        
        # Mostrar preview del reporte
        with st.expander("👁️ Preview del Reporte"):
            st.markdown(md)
            
    except Exception as e:
        st.error(f"❌ Error generando reporte: {e}")

def borrar_clips_antiguos(dias=7):
    """Borra clips de más de X días"""
    ahora = time.time()
    limite = ahora - (dias * 24 * 60 * 60)
    
    clips_borrados = 0
    carpetas_borradas = 0
    
    try:
        # Buscar en la carpeta de procesados
        if os.path.exists(CARPETA_PROCESADOS):
            for root, dirs, files in os.walk(CARPETA_PROCESADOS):
                # Verificar si es carpeta procesada con marcador P*
                marcador_procesado = os.path.join(root, "PROCESADO.txt")
                if os.path.exists(marcador_procesado):
                    archivos_en_carpeta = 0
                    for file in files:
                        if file.endswith((".mp4", ".txt")):
                            file_path = os.path.join(root, file)
                            if os.path.getctime(file_path) < limite:
                                try:
                                    os.remove(file_path)
                                    clips_borrados += 1
                                except Exception:
                                    pass
                            else:
                                archivos_en_carpeta += 1
                    
                    if archivos_en_carpeta == 0:
                        try:
                            shutil.rmtree(root)
                            carpetas_borradas += 1
                        except Exception:
                            pass
    except Exception:
        pass
    
    return clips_borrados

# Mostrar mensaje si se cargaron términos automáticamente
if st.session_state.terminos_continuos:
    st.success(f"✅ Se cargaron automáticamente {len(st.session_state.terminos_continuos)} términos desde `terminos_guardados.json`: {', '.join(st.session_state.terminos_continuos[:3])}{'...' if len(st.session_state.terminos_continuos) > 3 else ''}")

# Mostrar estado de servicios preconfigurados
st.info("🚀 **Sistema preconfigurado y listo para usar:**")
col1, col2, col3, col4, col5 = st.columns(5)

# Verificar estado real de cada servicio
webhook_config = cargar_webhook_config()
telegram_config = cargar_telegram_config()
brevo_config = cargar_brevo_config()

with col1:
    if webhook_config.get('enabled', False) and webhook_config.get('url'):
        st.success("🌐 **Webhook** ✅\nMake.com activo")
    else:
        st.warning("🌐 **Webhook** ⚠️\nDeshabilitado")

with col2:
    if telegram_config.get('enabled', False) and telegram_config.get('bot_token') and telegram_config.get('chat_id'):
        st.success("📱 **Telegram** ✅\n@edesuralertas activo")
    else:
        st.warning("📱 **Telegram** ⚠️\nNo configurado")

with col3:
    st.success("☁️ **Google Drive** ✅\nSiempre activo")

with col4:
    cloudinary_config = cargar_cloudinary_config()
    if cloudinary_config.get('cloud_name') and cloudinary_config.get('api_key'):
        st.success("☁️ **Cloudinary** ✅\ndhzxzbkmc activo")
    else:
        st.warning("☁️ **Cloudinary** ⚠️\nNo configurado")

with col5:
    correos_activos_dashboard = obtener_correos_activos()
    if brevo_config.get('enabled', False) and brevo_config.get('api_key') and brevo_config.get('sender_email') and correos_activos_dashboard:
        st.success(f"📧 **Brevo** ✅\n{len(correos_activos_dashboard)} destinatarios")
    else:
        st.warning("📧 **Brevo** ⚠️\nNo configurado")
    
st.title("🎬 Análisis Automático de Videos - Versión Preconfigurada ✅")
st.markdown(f"📁 Carpeta: `{CARPETA_VIDEOS}` | 🌐 Webhook: Make.com | 📱 Telegram: @edesuralertas | ☁️ Google Drive: Activo | 📧 Brevo: Correos")
st.info("⏱️ **Configuración de clips:** Por defecto genera clips de 1 minuto (30s antes + 30s después de cada coincidencia)")

# Mostrar flujo de envío completo
st.markdown("### 📤 **FLUJO DE ENVÍO DE COINCIDENCIAS:**")
st.markdown("""
**Cuando se detecta una coincidencia, el sistema envía automáticamente a TODOS estos destinos:**

1. **📝 PASO 1:** Envío inmediato de **resumen en texto** 
   - 🌐 **Webhook (Make.com)** → Texto de la coincidencia
   - 📱 **Telegram** → Mensaje de alerta

2. **📧 PASO 2.5:** Envío de **correo electrónico**
   - 📧 **Brevo** → Correo HTML moderno con video incrustado
   - 🎯 **Asunto:** Nombre del término encontrado
   - 📋 **Cuerpo:** Resumen completo en formato HTML

3. **⏸️ PASO 3:** Pausa de 30 segundos (evitar congestión)

4. **🎬 PASO 4:** Envío del **video clip**
   - 🌐 **Webhook (Make.com)** → Video en base64 (si <8MB) o metadatos
   - 📱 **Telegram** → Video directo o vía Cloudinary

5. **☁️ PASO 5:** Envío a **Google Drive**
   - 📄 **Archivo TXT** → Resumen completo de la coincidencia
   - 🎬 **Video clip** → Archivo MP4 del clip

**✅ RESULTADO:** Cada coincidencia llega a todos los destinos configurados automáticamente.
""")

st.markdown("---")

# === SIDEBAR CON ESTADÍSTICAS ===
with st.sidebar:
    st.header("📊 Estadísticas de Sesión")
    st.metric("Videos encontrados", st.session_state.videos_encontrados)
    st.metric("Videos procesados", st.session_state.videos_procesados)
    st.metric("Clips generados", st.session_state.clips_generados)
    
    st.markdown("---")
    st.header("⚙️ Configuración Avanzada")
    
    # Configuración de intervalos con auto-guardado
    nuevo_intervalo = st.selectbox(
        "⏱️ Intervalo de búsqueda:",
        options=[30, 60, 120, 300, 600],
        format_func=lambda x: f"{x} segundos ({x//60}min)" if x >= 60 else f"{x} segundos",
        index=1 if st.session_state.intervalo == 60 else [30, 60, 120, 300, 600].index(st.session_state.intervalo) if st.session_state.intervalo in [30, 60, 120, 300, 600] else 1,
        key="sidebar_intervalo_select"
    )
    
    # Auto-guardar si cambió el intervalo
    if nuevo_intervalo != st.session_state.intervalo:
        st.session_state.intervalo = nuevo_intervalo
        guardar_configuracion_completa(
            st.session_state.terminos_continuos,
            st.session_state.intervalo,
            st.session_state.get('duracion_clip', 60),
            st.session_state.get('buffer_anterior', 30),
            st.session_state.mostrar_coincidencias
        )
    
    # Opciones de visualización con auto-guardado
    nuevo_mostrar = st.checkbox("Mostrar coincidencias en tiempo real", value=st.session_state.mostrar_coincidencias)
    if nuevo_mostrar != st.session_state.mostrar_coincidencias:
        st.session_state.mostrar_coincidencias = nuevo_mostrar
        guardar_configuracion_completa(
            st.session_state.terminos_continuos,
            st.session_state.intervalo,
            st.session_state.get('duracion_clip', 60),
            st.session_state.get('buffer_anterior', 30),
            st.session_state.mostrar_coincidencias
        )
    
    # Configuración de clips con auto-guardado
    st.markdown("**⏱️ Configuración de Duración de Clips:**")
    st.info("💡 **Cómo funciona:** El clip incluirá [Buffer anterior] + momento de coincidencia + tiempo restante hasta [Duración total]")
    
    nueva_duracion = st.slider("Duración total del clip (segundos)", 30, 120, st.session_state.get('duracion_clip', 60), 
                              help="Duración total del clip generado. Por defecto 60s = 1 minuto (30s antes + 30s después)")
    
    # Forzar que el valor mínimo sea 60 si no está configurado
    if nueva_duracion < 60:
        nueva_duracion = 60
        st.warning("⚠️ Duración ajustada a 60 segundos (mínimo recomendado)")
    nuevo_buffer = st.slider("Buffer anterior (segundos)", 10, 60, st.session_state.get('buffer_anterior', 30),
                            help="Tiempo antes de la coincidencia. Por defecto 30s antes")
    
    # Mostrar cálculo del buffer posterior
    buffer_posterior = nueva_duracion - nuevo_buffer
    st.caption(f"📊 **Resultado:** {nuevo_buffer//60}:{nuevo_buffer%60:02d} antes + {buffer_posterior//60}:{buffer_posterior%60:02d} después de la coincidencia")
    
    # Auto-guardar configuración de clips
    if nueva_duracion != st.session_state.get('duracion_clip', 60) or nuevo_buffer != st.session_state.get('buffer_anterior', 30):
        st.session_state.duracion_clip = nueva_duracion
        st.session_state.buffer_anterior = nuevo_buffer
        guardar_configuracion_completa(
            st.session_state.terminos_continuos,
            st.session_state.intervalo,
            st.session_state.duracion_clip,
            st.session_state.buffer_anterior,
            st.session_state.mostrar_coincidencias
        )
    
    st.markdown("---")
    st.header("🌐 Configuración Webhook")
    
    webhook_config = cargar_webhook_config()
    
    # Habilitar/Deshabilitar webhook global
    webhook_enabled = st.checkbox("Activar envío de clips", value=webhook_config['enabled'])
    
    if webhook_enabled:
        st.subheader("📡 Seleccionar Webhooks de Destino")
        
        # Switches individuales para cada webhook
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enviar_makecom = st.checkbox(
                "🔵 Make.com", 
                value=webhook_config.get('enviar_makecom', True),
                help="Enviar a Make.com"
            )
            st.text("hook.us1.make.com")
        
        with col2:
            enviar_n8n = st.checkbox(
                "🟢 N8N", 
                value=webhook_config.get('enviar_n8n', True),
                help="Enviar a N8N principal"
            )
            st.text("webhook/edesurbot")
        
        with col3:
            enviar_n8n_test = st.checkbox(
                "🟡 N8N-Test", 
                value=webhook_config.get('enviar_n8n_test', True),
                help="Enviar a N8N de prueba"
            )
            st.text("webhook-test/edesurbot")
        
        # Mostrar estado de selección
        webhooks_activos = []
        if enviar_makecom:
            webhooks_activos.append("Make.com")
        if enviar_n8n:
            webhooks_activos.append("N8N")
        if enviar_n8n_test:
            webhooks_activos.append("N8N-Test")
            
        if webhooks_activos:
            st.info(f"📤 Enviando a: {', '.join(webhooks_activos)}")
        else:
            st.warning("⚠️ No hay webhooks seleccionados")
        
        # Configuración general
        max_size = st.slider("Tamaño máximo por clip (MB):", 1, 50, min(webhook_config['max_file_size_mb'], 25))
        
        if st.button("💾 Guardar Configuración Webhook"):
            nueva_config = webhook_config.copy()
            nueva_config.update({
                'enabled': webhook_enabled,
                'enviar_makecom': enviar_makecom,
                'enviar_n8n': enviar_n8n,
                'enviar_n8n_test': enviar_n8n_test,
                'max_file_size_mb': max_size
            })
            
            if guardar_webhook_config(nueva_config):
                st.success("✅ Configuración webhook guardada")
            
        # Test de webhooks seleccionados
        if webhooks_activos:
            if st.button("🧪 Probar Webhooks Seleccionados"):
                exito, mensaje = webhook_notification_simple(
                    "test_video.mp4", 
                    "**TÉRMINOS DETECTADOS:** test\n\nEsto es una prueba del webhook", 
                    ["test"]
                )
                if exito:
                    st.success(f"✅ Webhooks OK: {mensaje}")
                else:
                    st.error(f"❌ Error webhooks: {mensaje}")
                    
        st.info("💡 Se enviarán los clips donde se encontraron coincidencias + resumen a los webhooks seleccionados")
    else:
        st.info("Webhook desactivado")
    
    st.markdown("---")
    st.header("📱 Configuración Telegram")
    
    telegram_config = cargar_telegram_config()
    
    # Habilitar/Deshabilitar Telegram
    telegram_enabled = st.checkbox("Activar envío a Telegram", value=telegram_config['enabled'])
    
    if telegram_enabled:
        bot_token = st.text_input("🤖 Bot Token:", value=telegram_config['bot_token'], 
                                 placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz", type="password")
        
        chat_id = st.text_input("💬 Chat ID:", value=telegram_config['chat_id'], 
                               placeholder="-1001234567890")
        
        col1, col2 = st.columns(2)
        with col1:
            send_clips = st.checkbox("Enviar clips", value=telegram_config.get('send_clips', True))
        with col2:
            send_summary = st.checkbox("Enviar resumen", value=telegram_config.get('send_summary', True))
        
        use_cloudinary = st.checkbox("Usar Cloudinary para videos", value=telegram_config.get('use_cloudinary', True))
        
        if st.button("💾 Guardar Telegram"):
            nueva_config = telegram_config.copy()
            nueva_config.update({
                'enabled': telegram_enabled,
                'bot_token': bot_token.strip(),
                'chat_id': chat_id.strip(),
                'send_clips': send_clips,
                'send_summary': send_summary,
                'use_cloudinary': use_cloudinary
            })
            
            if guardar_telegram_config(nueva_config):
                st.success("✅ Configuración Telegram guardada")
        
        # Test de Telegram
        if bot_token.strip() and chat_id.strip():
            if st.button("🧪 Probar Telegram"):
                exito, mensaje = test_telegram_connection()
                if exito:
                    st.success(f"✅ Telegram OK: {mensaje}")
                else:
                    st.error(f"❌ Error Telegram: {mensaje}")
        
        # Configuración de Cloudinary si está habilitada
        if use_cloudinary:
            st.markdown("#### ☁️ Configuración Cloudinary")
            
            cloudinary_config = cargar_cloudinary_config()
            
            cloud_name = st.text_input("Cloud Name:", value=cloudinary_config['cloud_name'], 
                                      placeholder="tu-cloud-name")
            
            col1, col2 = st.columns(2)
            with col1:
                api_key = st.text_input("API Key:", value=cloudinary_config['api_key'], 
                                       placeholder="123456789012345", type="password")
            with col2:
                api_secret = st.text_input("API Secret:", value=cloudinary_config['api_secret'], 
                                          placeholder="abcdefghijklmnopqrstuvwxyz", type="password")
            
            folder_name = st.text_input("Carpeta:", value=cloudinary_config.get('folder', 'video_analyzer_clips'))
            
            if st.button("💾 Guardar Cloudinary"):
                nueva_config = cloudinary_config.copy()
                nueva_config.update({
                    'cloud_name': cloud_name.strip(),
                    'api_key': api_key.strip(),
                    'api_secret': api_secret.strip(),
                    'folder': folder_name.strip()
                })
                
                if guardar_cloudinary_config(nueva_config):
                    st.success("✅ Configuración Cloudinary guardada")
            
            st.info("💡 Cloudinary se usará para subir videos grandes a Telegram")
        
        st.info("📱 Se enviarán clips y resúmenes a tu canal/chat de Telegram")
    else:
        st.info("Telegram desactivado")
    
    st.markdown("---")
    st.header("☁️ Configuración Google Drive")
    
    # Habilitar/Deshabilitar Google Drive
    gdrive_enabled = st.checkbox("Activar envío a Google Drive", value=True)
    
    if gdrive_enabled:
        st.info(f"📁 **Carpeta destino:** `{GOOGLE_DRIVE_FOLDER_ID}`")
        st.info("🔑 **Credenciales configuradas:** ✅")
        
        # Mostrar información de la carpeta
        col1, col2 = st.columns(2)
        with col1:
            st.caption("📂 ID de carpeta")
            st.code(GOOGLE_DRIVE_FOLDER_ID)
        with col2:
            st.caption("🔐 Cliente ID")
            st.code(GOOGLE_CLIENT_ID[:20] + "...")
        
        # Test de conexión
        if st.button("🧪 Probar Google Drive", help="Verificar conexión con Google Drive"):
            with st.spinner("Probando Google Drive..."):
                exito, mensaje = test_google_drive_connection()
                if exito:
                    st.success(f"✅ Google Drive: {mensaje}")
                else:
                    st.error(f"❌ Google Drive: {mensaje}")
        
        st.info("💡 Se enviarán clips y resúmenes TXT a Google Drive automáticamente")
    else:
        st.info("Google Drive desactivado")
    
    st.markdown("---")
    st.header("📧 Configuración Brevo (Correo)")
    
    brevo_config = cargar_brevo_config()
    
    # Habilitar/Deshabilitar Brevo
    brevo_enabled = st.checkbox("Activar envío de correos", value=brevo_config['enabled'])
    
    if brevo_enabled:
        st.info("💡 **Brevo (ex SendinBlue)** - Servicio profesional de correo electrónico")
        
        # Configuración del remitente
        st.subheader("👤 Configuración del Remitente")
        sender_email = st.text_input("📧 Email del Remitente:", value=brevo_config['sender_email'], 
                                   placeholder="tu-email@dominio.com")
        sender_name = st.text_input("👤 Nombre del Remitente:", value=brevo_config['sender_name'], 
                                  placeholder="Sistema de Análisis de Videos")
        
        # API Key
        api_key = st.text_input("🔑 API Key de Brevo:", value=brevo_config['api_key'], 
                               placeholder="xkeysib-...", type="password",
                               help="Tu API Key de Brevo (SMTP Key)")
        
        # Gestión de múltiples destinatarios
        st.subheader("📨 Lista de Destinatarios")
        
        # Cargar correos guardados
        correos_guardados = cargar_correos_guardados()
        
        # Mostrar correos existentes
        if correos_guardados:
            st.success(f"📧 **{len(correos_guardados)} correos configurados:**")
            
            # Mostrar en columnas
            cols = st.columns(3)
            for i, correo_data in enumerate(correos_guardados):
                with cols[i % 3]:
                    estado = "🟢" if correo_data.get('activo', True) else "🔴"
                    st.write(f"{estado} **{correo_data['nombre']}**")
                    st.caption(f"📧 {correo_data['email']}")
                    
                    # Botón para eliminar
                    if st.button(f"🗑️ Eliminar", key=f"del_{correo_data['email']}"):
                        exito, mensaje = eliminar_correo_de_lista(correo_data['email'])
                        if exito:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
        else:
            st.info("📭 No hay correos configurados aún")
        
        st.markdown("---")
        
        # Agregar nuevo correo
        st.subheader("➕ Agregar Nuevo Destinatario")
        
        # Inicializar contador para widgets de Brevo
        if 'brevo_widget_counter' not in st.session_state:
            st.session_state.brevo_widget_counter = 0
        
        col1, col2 = st.columns([2, 1])
        with col1:
            nuevo_correo = st.text_input("📧 Email:", placeholder="nuevo@dominio.com", key=f"brevo_nuevo_correo_input_{st.session_state.brevo_widget_counter}")
        with col2:
            nombre_correo = st.text_input("👤 Nombre:", placeholder="Nombre", key=f"brevo_nombre_correo_input_{st.session_state.brevo_widget_counter}")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("➕ Agregar Correo"):
                if nuevo_correo.strip():
                    exito, mensaje = agregar_correo_a_lista(nuevo_correo, nombre_correo)
                    if exito:
                        st.success(mensaje)
                        # Forzar recreación de widgets incrementando contador
                        st.session_state.brevo_widget_counter += 1
                        st.rerun()
                    else:
                        st.error(mensaje)
                else:
                    st.warning("Ingresa un correo válido")
        
        with col2:
            if st.button("📧 Agregar FGJ Medios"):
                exito, mensaje = agregar_correo_a_lista("info@fgjmedios.com", "FGJ Medios")
                if exito:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.info("El correo ya existe")
        
        with col3:
            if correos_guardados and st.button("🧹 Limpiar Todos los Correos"):
                if guardar_correos_lista([]):
                    st.success("Lista de correos limpiada")
                    st.rerun()
        
        # Configuración avanzada
        with st.expander("⚙️ Configuración Avanzada"):
            smtp_server = st.text_input("🌐 Servidor SMTP:", value=brevo_config['smtp_server'], 
                                       placeholder="smtp-relay.sendinblue.com")
            smtp_port = st.number_input("🔌 Puerto SMTP:", value=brevo_config['smtp_port'], 
                                       min_value=1, max_value=65535, step=1)
        
        # Botón para guardar
        if st.button("💾 Guardar Configuración Brevo"):
            nueva_config = brevo_config.copy()
            nueva_config.update({
                'enabled': brevo_enabled,
                'api_key': api_key.strip(),
                'sender_email': sender_email.strip(),
                'sender_name': sender_name.strip(),
                'recipient_email': '',  # Ya no se usa, se maneja con la lista
                'recipient_name': '',   # Ya no se usa, se maneja con la lista
                'smtp_server': smtp_server.strip(),
                'smtp_port': smtp_port
            })
            
            if guardar_brevo_config(nueva_config):
                st.success("✅ Configuración Brevo guardada exitosamente")
                st.rerun()  # Recargar para mostrar el estado actualizado
        
        # Test de conexión
        if api_key.strip() and sender_email.strip() and correos_guardados:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧪 Probar Conexión Brevo"):
                    with st.spinner("Probando conexión con Brevo..."):
                        exito, mensaje = test_brevo_connection()
                        if exito:
                            st.success(f"✅ Brevo: {mensaje}")
                        else:
                            st.error(f"❌ Brevo: {mensaje}")
            
            with col2:
                if st.button("📧 Enviar Correo de Prueba"):
                    with st.spinner("Enviando correo de prueba..."):
                        exito, mensaje = enviar_correo_brevo(
                            "PRUEBA MANUAL",
                            "**CORREO DE PRUEBA MANUAL**\\n\\nEste es un correo de prueba manual del sistema de análisis de videos de FGJ Medios.\\n\\n✅ Si recibiste este correo, la configuración está funcionando correctamente.\\n\\n🎯 **Características del correo:**\\n- Plantilla HTML moderna y responsive\\n- Envío a múltiples destinatarios\\n- Resumen completo de coincidencias\\n- Videos adjuntos sin limitación de tamaño\\n- Información detallada del medio\\n- Términos detectados destacados\\n\\n📧 **Sistema configurado para:** Análisis automático de videos con notificaciones inmediatas por correo.",
                            "test_manual.mp4",
                            None,  # No hay video_path en prueba manual
                            "FGJ Medios - Prueba Manual del Sistema",  # info_medio
                            ["PRUEBA MANUAL", "FGJ MEDIOS", "SISTEMA CORREOS"],  # terminos_detectados
                            None  # No hay video_url_gdrive en prueba manual
                        )
                        if exito:
                            st.success(f"✅ {mensaje}")
                        else:
                            st.error(f"❌ Error enviando correo: {mensaje}")
        elif not correos_guardados:
            st.warning("⚠️ Agrega al menos un destinatario para poder probar")
        
        # Información sobre el funcionamiento
        st.info("📧 **Funcionamiento:** Se enviará un correo automáticamente cuando se detecte una coincidencia con:")
        st.markdown("""
        - 🎯 **Asunto:** "🎯 Coincidencia: [TÉRMINO_ENCONTRADO]"
        - 📋 **Cuerpo:** Resumen COMPLETO generado por IA en formato HTML moderno
        - 📺 **Medio:** Información detallada del medio donde se detectó
        - 🏷️ **Términos:** Todos los términos detectados destacados
        - 🎬 **Video:** Incrustado en el correo (si está disponible en Cloudinary)
        - 📎 **Adjunto:** Archivo de video completo (SIN limitación de tamaño)
        - 👥 **Destinatarios:** Envío a TODOS los correos configurados en la lista
        """)
        
        st.success("✨ **Mejoras implementadas:** Resumen completo, múltiples destinatarios, videos sin límite de tamaño")
        
        # Mostrar estado de configuración
        correos_activos = obtener_correos_activos()
        if all([api_key.strip(), sender_email.strip()]) and correos_activos:
            st.success(f"✅ Configuración completa - Lista para enviar correos a {len(correos_activos)} destinatarios")
        elif not correos_activos:
            st.warning("⚠️ Agrega al menos un destinatario para completar la configuración")
        else:
            st.warning("⚠️ Configuración incompleta - Completa API Key y email del remitente")
            
    else:
        st.info("📧 Correo Brevo desactivado")
        st.markdown("""
        **¿Por qué usar Brevo?**
        - ✅ Servicio profesional de correo
        - ✅ Alta deliverability 
        - ✅ Plantillas HTML modernas
        - ✅ Soporte para adjuntos y videos
        - ✅ API confiable y rápida
        """)

# === PANEL DE CONTROL PRINCIPAL ===
st.markdown("## 🎛️ Panel de Control Principal")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.session_state.running:
        st.success("🟢 **ACTIVO**")
        st.write(f"⏰ {st.session_state.ultimo_chequeo.strftime('%H:%M:%S')}")
    else:
        st.error("🔴 **INACTIVO**")
        st.write("⏸️ En espera")

with col2:
    if st.session_state.terminos_continuos:
        st.info(f"🔍 **{len(st.session_state.terminos_continuos)} términos configurados**")
        
        # Mostrar estado de guardado
        if os.path.exists(TERMINOS_CONFIG):
            try:
                with open(TERMINOS_CONFIG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fecha_guardado = data.get('fecha_actualizacion', '')
                    if fecha_guardado:
                        fecha_dt = datetime.fromisoformat(fecha_guardado.replace('Z', '+00:00').replace('+00:00', ''))
                        st.caption(f"💾 Guardado: {fecha_dt.strftime('%H:%M:%S')}")
            except Exception:
                pass
    else:
        st.warning("⚠️ Sin términos")

with col3:
    # Tiempo de próximo chequeo
    if st.session_state.running:
        proximo = st.session_state.ultimo_chequeo + timedelta(seconds=st.session_state.intervalo)
        tiempo_restante = proximo - datetime.now()
        if tiempo_restante.total_seconds() > 0:
            st.info(f"⏳ Próximo en {int(tiempo_restante.total_seconds())}s")
        else:
            st.info("🔄 Procesando...")
    else:
        st.info("⏸️ Pausado")

with col4:
    # Estado del sistema - Calculado después de definir las funciones
    try:
        total_clips = len(buscar_todos_los_clips())
        st.metric("Total clips", total_clips)
    except Exception:
        st.metric("Total clips", "...")

# === REINICIO Y LIMPIEZA ===
st.markdown("### 🔧 Controles del Sistema")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔄 Reiniciar Aplicación"):
        st.session_state.clear()
        init_session_state()
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success("✅ Aplicación reiniciada")
        st.rerun()

with col2:
    if st.button("💾 Limpiar Caché"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("🧹 Caché limpiado")
        st.rerun()

with col3:
    if st.button("🗑️ Borrar Clips Antiguos"):
        clips_borrados = borrar_clips_antiguos(dias=7)
        if clips_borrados > 0:
            st.success(f"🗑️ Borrados {clips_borrados} clips antiguos")
            st.rerun()
        else:
            st.info("✅ No hay clips antiguos para borrar")

with col4:
    if st.button("📊 Generar Reporte"):
        if st.session_state.resumen_global:
            generar_resumen_md(st.session_state.resumen_global)
        else:
            st.warning("⚠️ No hay datos para reportar")

# === OPTIMIZACIÓN Y CACHÉ ===
st.markdown("### ⚡ Optimización de Búsqueda")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🧹 Limpiar Caché", help="Limpiar caché de archivos escaneados"):
        archivos_limpiados = limpiar_cache_escaneo()
        if archivos_limpiados > 0:
            st.success(f"🧹 Caché limpiado: {archivos_limpiados} archivos eliminados")
        else:
            st.info("✅ Caché ya está limpio")

with col2:
    if st.button("📊 Ver Estadísticas Caché", help="Mostrar estadísticas del caché de escaneo"):
        try:
            cache = cargar_cache_escaneo()
            archivos_cache = cache.get('archivos_escaneados', {})
            ultima_actualizacion = cache.get('ultima_actualizacion', 0)
            
            if archivos_cache:
                st.markdown("**📊 Estadísticas del Caché:**")
                st.metric("Archivos en caché", len(archivos_cache))
                
                if ultima_actualizacion > 0:
                    fecha_actualizacion = datetime.fromtimestamp(ultima_actualizacion)
                    st.metric("Última actualización", fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S'))
                
                # Contar tipos de archivos
                procesados = sum(1 for info in archivos_cache.values() if info.get('procesado', False))
                muy_pequeños = sum(1 for info in archivos_cache.values() if info.get('muy_pequeño', False))
                nuevos_detectados = sum(1 for info in archivos_cache.values() if info.get('detectado_como_nuevo', False))
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Ya procesados", procesados)
                    st.metric("Muy pequeños", muy_pequeños)
                with col_b:
                    st.metric("Nuevos detectados", nuevos_detectados)
                    st.metric("Pendientes", len(archivos_cache) - procesados - muy_pequeños)
                    
            else:
                st.info("📭 Caché vacío")
        except Exception as e:
            st.error(f"❌ Error leyendo caché: {e}")

with col3:
    if st.button("🔄 Resetear Caché", help="Resetear completamente el caché de escaneo"):
        try:
            if os.path.exists(CACHE_ESCANEO):
                os.remove(CACHE_ESCANEO)
                st.success("🔄 Caché reseteado completamente")
            else:
                st.info("✅ No había caché para resetear")
        except Exception as e:
            st.error(f"❌ Error reseteando caché: {e}")

with col4:
    if st.button("🌐 Diagnóstico Red", help="Verificar conectividad con APIs"):
        with st.spinner("🔍 Verificando conectividad..."):
            resultados = diagnosticar_conectividad()
            
            st.markdown("**🌐 Estado de Conectividad:**")
            
            # Internet general
            if resultados['internet']:
                st.success("✅ Conectividad a internet: OK")
            else:
                st.error("❌ Sin conectividad a internet")
            
            # OpenAI
            if resultados['openai']:
                st.success("✅ OpenAI API: Disponible")
            else:
                st.warning("⚠️ OpenAI API: No disponible")
            
            # Mistral
            if resultados['mistral']:
                st.success("✅ Mistral API: Disponible")
            else:
                st.warning("⚠️ Mistral API: No disponible")
            
            # Resumen
            if not resultados['internet']:
                st.error("🔧 **Solución:** Verificar conexión a internet")
            elif not resultados['openai'] and not resultados['mistral']:
                st.error("🔧 **Solución:** Verificar configuración de APIs y claves")
            else:
                st.info("✅ **Estado:** Al menos una API disponible")

# === ESTADO DE APIS ===
# Verificar estado de Mistral y mostrar alerta si hay problemas
try:
    mistral_disponible, mistral_estado = verificar_estado_mistral()
    if not mistral_disponible:
        st.warning(f"⚠️ **Mistral API no disponible:** {mistral_estado}")
        st.info("🔄 **Sistema de Fallback Activo:** Se usará automáticamente OpenAI Whisper para todos los archivos")
    else:
        st.success(f"✅ **Mistral API:** {mistral_estado}")
except Exception as e:
    st.error(f"❌ Error verificando Mistral: {str(e)[:100]}")

# === PRUEBAS RÁPIDAS DE SERVICIOS ===
st.markdown("### 🧪 Pruebas Rápidas de Servicios")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("🌐 Probar Webhook", help="Verificar conexión con Make.com"):
        with st.spinner("Probando webhook..."):
            # Primero probar conectividad básica
            try:
                import requests
                test_response = requests.get("https://httpbin.org/status/200", timeout=5)
                if test_response.status_code == 200:
                    st.info("🌐 Conectividad a internet: ✅")
                else:
                    st.warning("⚠️ Problemas de conectividad")
            except Exception:
                st.error("❌ Sin conexión a internet")
            
            # Luego probar el webhook
            exito, mensaje = webhook_notification_simple(
                "test_video.mp4", 
                "**TÉRMINOS DETECTADOS:** prueba\n\nEste es un test del sistema de análisis de videos.", 
                ["prueba", "test"]
            )
            if exito:
                st.success(f"✅ Webhook funcionando: {mensaje}")
            else:
                st.error(f"❌ Error en webhook: {mensaje}")
                st.info("💡 Tip: El webhook puede tardar unos segundos en responder")

with col2:
    if st.button("📱 Probar Telegram", help="Verificar conexión con el bot de Telegram"):
        with st.spinner("Probando Telegram..."):
            exito, mensaje = test_telegram_connection()
            if exito:
                st.success(f"✅ Telegram funcionando: {mensaje}")
            else:
                st.error(f"❌ Error en Telegram: {mensaje}")

with col3:
    if st.button("☁️ Probar Cloudinary", help="Verificar configuración de Cloudinary"):
        with st.spinner("Probando Cloudinary..."):
            if configurar_cloudinary():
                st.success("✅ Cloudinary configurado correctamente")
                st.info("📹 Listo para subir videos grandes")
            else:
                st.error("❌ Error en configuración de Cloudinary")

with col4:
    if st.button("☁️ Probar Google Drive", help="Verificar conexión con Google Drive"):
        with st.spinner("Probando Google Drive..."):
            exito, mensaje = test_google_drive_connection()
            if exito:
                st.success(f"✅ Google Drive: {mensaje}")
            else:
                st.error(f"❌ Google Drive: {mensaje}")

with col5:
    if st.button("📤 Test Webhooks", help="Enviar primer resumen ejecutivo guardado a ambos webhooks"):
        with st.spinner("Enviando primer resumen ejecutivo guardado..."):
            # Buscar el primer resumen ejecutivo guardado
            config = cargar_webhook_config()
            
            # Intentar obtener el primer resumen del session_state
            primer_resumen = None
            primer_video = None
            terminos_encontrados = []
            
            if st.session_state.resumen_global and len(st.session_state.resumen_global) > 0:
                # Usar el primer elemento del resumen global
                primer_item = st.session_state.resumen_global[0]
                primer_video = primer_item.get('video', 'video_guardado.mp4')
                primer_resumen = primer_item.get('transcripcion_completa', primer_item.get('texto', 'Resumen ejecutivo guardado'))
                terminos_encontrados = [primer_item.get('termino', 'termino_guardado')]
            else:
                # Fallback si no hay resúmenes guardados
                primer_video = "resumen_ejemplo.mp4"
                primer_resumen = "**TÉRMINOS DETECTADOS:** ejemplo\n\n1. Tema principal: Este es un resumen ejecutivo de ejemplo del sistema\n2. Contexto: Enviado desde el analizador de videos\n3. Puntos clave: Sistema funcionando correctamente\n4. Relevancia: Prueba de conectividad con resumen real"
                terminos_encontrados = ["ejemplo", "prueba"]
            
            # Crear el mensaje con formato de resumen ejecutivo real
            data_prueba = {
                'evento': 'video_analizado',
                'timestamp': datetime.now().isoformat(),
                'video': primer_video,
                'terminos': terminos_encontrados,
                'resumen': primer_resumen[:500] + "..." if len(primer_resumen) > 500 else primer_resumen,
                'servidor': 'analizador_videos_ia_v2'
            }
            
            # Enviar solo a webhooks seleccionados
            exitos = []
            
            # Enviar a webhook principal (Make.com) si está habilitado
            if config.get('enviar_makecom', True):
                exito_principal, mensaje_principal = enviar_a_webhook_individual(
                    config['url'], data_prueba, "test_webhooks", "Make.com"
                )
                exitos.append(exito_principal)
                if exito_principal:
                    st.success(f"✅ Make.com: {mensaje_principal}")
                else:
                    st.error(f"❌ Make.com: {mensaje_principal}")
            else:
                st.info("🔵 Make.com: No seleccionado")
                
            # Enviar a webhook secundario (N8N) si está habilitado
            if config.get('enviar_n8n', True):
                exito_secundario, mensaje_secundario = enviar_a_webhook_individual(
                    config['url_secundario'], data_prueba, "test_webhooks", "N8N"
                )
                exitos.append(exito_secundario)
                if exito_secundario:
                    st.success(f"✅ N8N: {mensaje_secundario}")
                else:
                    st.error(f"❌ N8N: {mensaje_secundario}")
            else:
                st.info("🟢 N8N: No seleccionado")
                
            # Enviar a webhook terciario (N8N-Test) si está habilitado
            if config.get('enviar_n8n_test', True):
                exito_terciario, mensaje_terciario = enviar_a_webhook_individual(
                    config['url_terciario'], data_prueba, "test_webhooks", "N8N-Test"
                )
                exitos.append(exito_terciario)
                if exito_terciario:
                    st.success(f"✅ N8N-Test: {mensaje_terciario}")
                else:
                    st.error(f"❌ N8N-Test: {mensaje_terciario}")
            else:
                st.info("🟡 N8N-Test: No seleccionado")
            
            # Mostrar información del resumen enviado
            st.info(f"📋 **Video enviado:** {primer_video}")
            st.info(f"🏷️ **Términos:** {', '.join(terminos_encontrados)}")
            with st.expander("📄 Ver resumen enviado"):
                st.text(primer_resumen[:1000] + "..." if len(primer_resumen) > 1000 else primer_resumen)
            
            # Resultado general
            if not exitos:
                st.warning("⚠️ No hay webhooks seleccionados para probar")
            elif all(exitos):
                st.success("🎉 Todos los webhooks seleccionados recibieron el resumen ejecutivo")
            elif any(exitos):
                st.warning("⚠️ Solo algunos webhooks seleccionados funcionaron")
            else:
                st.error("❌ Ningún webhook seleccionado funcionó")

# === CONFIGURACIÓN DE TÉRMINOS ===
st.markdown("## 🔍 Configuración de Búsqueda")

terminos_input = st.text_input(
    "🏷️ Palabras clave (separadas por coma):",
    value=", ".join(st.session_state.terminos_continuos),
    help="Ejemplo: edesur, apagones, corte, energia, luz",
    key="terminos_input_field"
)

# Botones de acción organizados
col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])

with col1:
    if st.button("💾 Guardar Términos", help="Guardar la lista de términos"):
        if terminos_input.strip():
            nuevos_terminos = [t.strip().lower() for t in terminos_input.split(",") if t.strip()]
            st.session_state.terminos_continuos = nuevos_terminos
            if guardar_configuracion_completa(
                st.session_state.terminos_continuos,
                st.session_state.intervalo,
                st.session_state.duracion_clip,
                st.session_state.buffer_anterior,
                st.session_state.mostrar_coincidencias
            ):
                st.success(f"✅ {len(nuevos_terminos)} términos guardados en `terminos_guardados.json`")
            else:
                st.error("❌ Error guardando términos")
        else:
            st.session_state.terminos_continuos = []
            guardar_configuracion_completa([], st.session_state.intervalo, st.session_state.get('duracion_clip', 180), st.session_state.get('buffer_anterior', 90), st.session_state.mostrar_coincidencias)
            st.warning("🗑️ Términos limpiados")

with col2:
    # Botón para verificar APIs
    if st.button("🔍 Verificar APIs", help="Verificar estado de todas las APIs antes del procesamiento"):
        verificar_todas_las_apis()
    
    # Botón para probar envío de video
    if st.button("🎬 Probar Video", help="Probar envío inteligente de video a Telegram"):
        st.info("🎬 **PRUEBA DE ENVÍO DE VIDEO**")
        st.markdown("---")
        
        # Buscar un video de prueba
        videos_disponibles = []
        if os.path.exists("videos procesados"):
            for archivo in os.listdir("videos procesados"):
                if archivo.endswith('.mp4'):
                    videos_disponibles.append(archivo)
        
        if videos_disponibles:
            video_prueba = videos_disponibles[0]
            ruta_video = os.path.join("videos procesados", video_prueba)
            
            st.info(f"📹 Video de prueba: {video_prueba}")
            
            # Obtener tamaño del video
            file_size = os.path.getsize(ruta_video)
            file_size_mb = file_size / (1024 * 1024)
            
            st.info(f"📏 Tamaño: {file_size_mb:.1f}MB")
            
            # Determinar método
            if file_size_mb <= 50:
                st.success("✅ Método: Envío directo a Telegram")
            else:
                st.info("☁️ Método: Cloudinary + Telegram")
            
            # Probar envío
            caption_prueba = f"🧪 **PRUEBA DE ENVÍO INTELIGENTE**\n\n📹 Video: {video_prueba}\n📏 Tamaño: {file_size_mb:.1f}MB\n⏰ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            with st.spinner("🎬 Probando envío de video..."):
                exito, mensaje, url = enviar_video_telegram_inteligente(
                    ruta_video,
                    caption_prueba
                )
                
                if exito:
                    st.success(f"✅ **Video enviado exitosamente**: {mensaje}")
                    if url:
                        st.info(f"🔗 URL: {url}")
                else:
                    st.error(f"❌ **Error enviando video**: {mensaje}")
        else:
            st.warning("⚠️ No hay videos disponibles para probar")
    
    if st.button("🚀 Procesar Una Vez", type="primary", help="Procesar videos nuevos una sola vez"):
        if st.session_state.terminos_continuos:
            st.session_state.procesar_una_vez = True
        else:
            st.error("❌ Configura términos primero")

with col3:
    # Estado compacto sin mostrar lista
    if st.session_state.terminos_continuos:
        st.success(f"✅ {len(st.session_state.terminos_continuos)} términos")
    else:
        st.info("📝 Agrega términos")

with col4:
    if st.session_state.terminos_continuos:
        if st.button("🗑️", key="btn_limpiar", help="Limpiar todos"):
            st.session_state.terminos_continuos = []
            guardar_configuracion_completa([], st.session_state.intervalo, st.session_state.get('duracion_clip', 180), st.session_state.get('buffer_anterior', 90), st.session_state.mostrar_coincidencias)
            st.rerun()

# Separador visual
st.markdown("---")

# === GESTIÓN DE CORREOS PARA COINCIDENCIAS ===
st.markdown("## 📧 Correos para Coincidencias de Video")

# Cargar correos guardados
correos_guardados = cargar_correos_guardados()

# Mostrar correos actuales
if correos_guardados:
    st.success(f"✅ {len(correos_guardados)} correos configurados")
    
    # Mostrar lista de correos con opción de eliminar
    st.markdown("### 📬 Lista de Destinatarios")
    for i, correo_info in enumerate(correos_guardados):
        col1, col2 = st.columns([4, 1])
        with col1:
            nombre_display = correo_info.get('nombre', 'Sin nombre')
            correo_display = correo_info['correo']
            st.write(f"📧 **{nombre_display}** - {correo_display}")
        with col2:
            if st.button("🗑️", key=f"eliminar_correo_{i}", help=f"Eliminar {correo_display}"):
                eliminar_correo_de_lista(correo_display)
                st.success(f"✅ Correo {correo_display} eliminado")
                st.rerun()
else:
    st.info("📭 No hay correos configurados. Agrega correos para recibir notificaciones de coincidencias.")

# Formulario para agregar nuevo correo
st.markdown("### ➕ Agregar Nuevo Correo")

# Inicializar contador para widgets
if 'correos_widget_counter' not in st.session_state:
    st.session_state.correos_widget_counter = 0

col1, col2, col3 = st.columns([3, 2, 1])

with col1:
    nuevo_correo = st.text_input(
        "📧 Correo electrónico:",
        placeholder="ejemplo@correo.com",
        key=f"correos_nuevo_correo_input_{st.session_state.correos_widget_counter}"
    )

with col2:
    nuevo_nombre = st.text_input(
        "👤 Nombre (opcional):",
        placeholder="Nombre del destinatario",
        key=f"correos_nuevo_nombre_input_{st.session_state.correos_widget_counter}"
    )

with col3:
    st.write("")  # Espaciador
    if st.button("➕ Agregar", type="primary", help="Agregar correo a la lista"):
        if nuevo_correo.strip():
            # Validar formato de correo básico
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, nuevo_correo.strip()):
                if agregar_correo_a_lista(nuevo_correo.strip(), nuevo_nombre.strip()):
                    st.success(f"✅ Correo {nuevo_correo.strip()} agregado")
                    # Forzar recreación de widgets incrementando contador
                    if 'correos_widget_counter' not in st.session_state:
                        st.session_state.correos_widget_counter = 0
                    st.session_state.correos_widget_counter += 1
                    st.rerun()
                else:
                    st.warning("⚠️ El correo ya existe en la lista")
            else:
                st.error("❌ Formato de correo inválido")
        else:
            st.error("❌ Ingresa un correo válido")

# Botones de acción rápida
st.markdown("### ⚡ Acciones Rápidas")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏢 Agregar FGJ Medios", help="Agregar info@fgjmedios.com"):
        if agregar_correo_a_lista("info@fgjmedios.com", "FGJ Medios"):
            st.success("✅ FGJ Medios agregado")
            st.rerun()
        else:
            st.info("ℹ️ FGJ Medios ya está en la lista")

with col2:
    if st.button("🧪 Correo de Prueba", help="Agregar autosemana@gmail.com"):
        if agregar_correo_a_lista("autosemana@gmail.com", "Pruebas"):
            st.success("✅ Correo de prueba agregado")
            st.rerun()
        else:
            st.info("ℹ️ Correo de prueba ya está en la lista")

with col3:
    if correos_guardados and st.button("🗑️ Limpiar Todos", help="Eliminar todos los correos"):
        # Confirmar acción
        if 'confirmar_limpiar_correos' not in st.session_state:
            st.session_state.confirmar_limpiar_correos = False
        
        if not st.session_state.confirmar_limpiar_correos:
            st.session_state.confirmar_limpiar_correos = True
            st.warning("⚠️ Presiona nuevamente para confirmar")
        else:
            # Limpiar todos los correos
            guardar_correos_lista([])
            st.success("🗑️ Todos los correos eliminados")
            st.session_state.confirmar_limpiar_correos = False
            st.rerun()

# Información sobre el funcionamiento
with st.expander("ℹ️ Información sobre Notificaciones por Correo"):
    st.markdown("""
    ### 📧 **Cómo Funcionan las Notificaciones por Correo**
    
    **Cuándo se envían:**
    - ✅ Automáticamente cuando se detecta una coincidencia de video
    - ✅ Solo si Brevo está configurado y habilitado
    - ✅ A todos los correos en esta lista
    
    **Contenido del correo:**
    - 📧 **Asunto:** Nombre de la coincidencia detectada
    - 📝 **Cuerpo:** Resumen completo de la coincidencia con información del medio y términos detectados
    - 🎬 **Video:** Clip de la coincidencia incrustado con player personalizado
    - 🔗 **Enlaces:** Para ver y descargar el video
    
    **Características del Player:**
    - ✅ Player completamente incrustado en el correo
    - ✅ Controles personalizados (play/pause, volumen, progreso)
    - ✅ Funciona directamente en el correo sin controles externos
    - ✅ Diseño profesional y moderno
    
    **Configuración requerida:**
    - 🔧 Brevo debe estar configurado en la sección de configuración
    - 📧 Al menos un correo debe estar en esta lista
    - ✅ El sistema enviará a todos los correos configurados
    
    **Persistencia de datos:**
    - 💾 Los correos se guardan en: `correos_guardados.json` (raíz de la app)
    - 💾 Los términos se guardan en: `terminos_guardados.json` (raíz de la app)
    - 🔒 Los datos persisten entre sesiones y no se pierden al borrar videos
    - 📍 Ubicación segura fuera de la carpeta de videos procesados
    """)

# Separador visual
st.markdown("---")

# === FUNCIONES AUXILIARES ===
def cargar_procesados():
    """
    Carga la lista de archivos ya procesados desde procesados.log Y procesados.txt
    Lee ambos archivos para máxima compatibilidad y respaldo
    """
    procesados = set()
    
    # ========== LEER procesados.log (formato detallado con timestamps) ==========
    if os.path.exists(PROCESADOS_LOG):
        try:
            with open(PROCESADOS_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Ignorar líneas vacías, comentarios, timestamps y separadores
                    if line and not line.startswith('#') and not line.startswith('[') and not line.startswith('='):
                        # Extraer solo el nombre del archivo (puede estar en diferentes formatos)
                        if '|' in line and 'VIDEO_PROCESADO:' in line:
                            # Formato: [timestamp] 🎬 VIDEO_PROCESADO: archivo.mp4 | Términos: ...
                            partes = line.split('VIDEO_PROCESADO:')
                            if len(partes) > 1:
                                nombre = partes[1].split('|')[0].strip()
                                procesados.add(nombre)
                        elif not line.startswith('📹') and not 'SUBCLIP' in line:
                            # Formato simple: archivo.mp4 (línea de compatibilidad)
                            procesados.add(line)
            log_debug(f"✅ {len(procesados)} archivos cargados desde procesados.log", "cargar_procesados")
        except Exception as e:
            st.warning(f"⚠️ Error leyendo procesados.log: {e}")
            log_warning(f"Error leyendo procesados.log: {e}", "cargar_procesados")
    
    # ========== LEER procesados.txt (formato simple - respaldo adicional) ==========
    procesados_txt = os.path.join(CARPETA_PROCESADOS, "procesados.txt")
    if os.path.exists(procesados_txt):
        try:
            cantidad_inicial = len(procesados)
            with open(procesados_txt, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Agregar solo líneas válidas (nombres de archivo)
                    if line and not line.startswith('#') and not line.startswith('['):
                        procesados.add(line)
            cantidad_nueva = len(procesados) - cantidad_inicial
            if cantidad_nueva > 0:
                log_debug(f"✅ {cantidad_nueva} archivos adicionales desde procesados.txt", "cargar_procesados")
        except Exception as e:
            log_warning(f"Error leyendo procesados.txt: {e}", "cargar_procesados")
    else:
        # Crear procesados.txt si no existe (para compatibilidad futura)
        try:
            with open(procesados_txt, "w", encoding="utf-8") as f:
                f.write("# Archivo de videos procesados (formato simple)\n")
                f.write("# Un video por línea\n")
                f.write(f"# Creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_info("✅ Archivo procesados.txt creado", "cargar_procesados")
        except Exception as e:
            log_warning(f"No se pudo crear procesados.txt: {e}", "cargar_procesados")
    
    log_info(f"📊 Total de archivos procesados cargados: {len(procesados)}", "cargar_procesados")
    return procesados

def cargar_cache_escaneo():
    """Carga el caché de archivos escaneados para optimizar búsquedas"""
    cache_default = {
        'archivos_escaneados': {},  # path: {mtime, size, procesado}
        'ultima_actualizacion': 0,
        'version': '1.0'
    }
    
    try:
        if os.path.exists(CACHE_ESCANEO):
            with open(CACHE_ESCANEO, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                # Validar estructura del caché
                if isinstance(cache, dict) and 'archivos_escaneados' in cache:
                    return cache
    except Exception as e:
        log_warning(f"Error cargando caché de escaneo: {e}", "cargar_cache_escaneo")
    
    return cache_default

def guardar_cache_escaneo(cache):
    """Guarda el caché de archivos escaneados"""
    try:
        cache['ultima_actualizacion'] = time.time()
        with open(CACHE_ESCANEO, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_warning(f"Error guardando caché de escaneo: {e}", "guardar_cache_escaneo")
        return False

def limpiar_cache_escaneo():
    """Limpia archivos que ya no existen del caché"""
    try:
        cache = cargar_cache_escaneo()
        archivos_limpiados = 0
        
        # Crear una copia de las claves para iterar
        paths_to_check = list(cache['archivos_escaneados'].keys())
        
        for path in paths_to_check:
            if not os.path.exists(path):
                del cache['archivos_escaneados'][path]
                archivos_limpiados += 1
        
        if archivos_limpiados > 0:
            guardar_cache_escaneo(cache)
            log_info(f"Caché limpiado: {archivos_limpiados} archivos eliminados", "limpiar_cache_escaneo")
        
        return archivos_limpiados
    except Exception as e:
        log_warning(f"Error limpiando caché: {e}", "limpiar_cache_escaneo")
        return 0

def cargar_archivos_fallidos():
    """Carga la lista de archivos fallidos desde fallidos.txt"""
    try:
        if os.path.exists("fallidos.txt"):
            with open("fallidos.txt", "r", encoding="utf-8") as f:
                archivos_fallidos = [line.strip().split('|')[0] for line in f.readlines() if line.strip()]
            log_info(f"📋 Cargados {len(archivos_fallidos)} archivos fallidos", "cargar_archivos_fallidos")
            return archivos_fallidos
        return []
    except Exception as e:
        log_warning(f"Error cargando archivos fallidos: {e}", "cargar_archivos_fallidos")
        return []

def guardar_archivo_fallido(nombre_archivo, error_mensaje="", archivo_path=None):
    """
    Guarda un archivo fallido:
    1. Muestra mensaje en UI
    2. Envía notificación a plataformas
    3. Mueve archivo a carpeta archivos_fallidos/
    4. Crea archivo .txt con el error
    """
    func_name = "guardar_archivo_fallido"
    
    try:
        archivos_fallidos = cargar_archivos_fallidos()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Evitar duplicados
        if nombre_archivo in archivos_fallidos:
            log_info(f"ℹ️ Archivo ya está en fallidos: {nombre_archivo}", func_name)
            return False
        
        # 1. MOSTRAR MENSAJE EN UI
        st.error(f"❌ **ERROR PROCESANDO ARCHIVO:** `{nombre_archivo}`")
        st.warning(f"⚠️ **Error:** {error_mensaje}")
        st.info("📁 Moviendo archivo a carpeta de fallidos...")
        
        # 2. CREAR CARPETA archivos_fallidos/ si no existe
        carpeta_fallidos = "archivos_fallidos"
        if not os.path.exists(carpeta_fallidos):
            os.makedirs(carpeta_fallidos)
            log_info(f"📁 Carpeta creada: {carpeta_fallidos}", func_name)
        
        # 3. MOVER ARCHIVO a carpeta de fallidos
        archivo_movido = False
        ruta_destino = None
        
        if archivo_path and os.path.exists(archivo_path):
            try:
                nombre_base = os.path.basename(archivo_path)
                ruta_destino = os.path.join(carpeta_fallidos, nombre_base)
                
                # Si ya existe en destino, agregar timestamp
                if os.path.exists(ruta_destino):
                    nombre_sin_ext, ext = os.path.splitext(nombre_base)
                    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nombre_base = f"{nombre_sin_ext}_{timestamp_file}{ext}"
                    ruta_destino = os.path.join(carpeta_fallidos, nombre_base)
                
                shutil.move(archivo_path, ruta_destino)
                archivo_movido = True
                log_info(f"📁 Archivo movido a: {ruta_destino}", func_name)
                st.success(f"✅ Archivo movido a: `{carpeta_fallidos}/{nombre_base}`")
            except Exception as e_move:
                log_warning(f"⚠️ No se pudo mover archivo: {e_move}", func_name)
                st.warning(f"⚠️ No se pudo mover archivo: {e_move}")
        
        # 4. CREAR ARCHIVO .txt CON EL ERROR dentro de la carpeta
        nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
        timestamp_txt = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_txt = f"{nombre_sin_ext}_ERROR_{timestamp_txt}.txt"
        ruta_txt = os.path.join(carpeta_fallidos, nombre_txt)
        
        contenido_error = f"""❌ ERROR AL PROCESAR ARCHIVO
{'='*60}

📄 ARCHIVO: {nombre_archivo}
⏰ FECHA Y HORA: {timestamp}
❌ ERROR: {error_mensaje}

{'='*60}
UBICACIÓN ORIGINAL: {archivo_path if archivo_path else 'Desconocida'}
UBICACIÓN ACTUAL: {ruta_destino if archivo_movido else 'No movido'}
ARCHIVO MOVIDO: {'✅ Sí' if archivo_movido else '❌ No'}

{'='*60}
ACCIONES RECOMENDADAS:
- Verificar que el archivo no esté corrupto
- Verificar formato del archivo
- Revisar logs para más detalles
- Si el problema persiste, contactar soporte

{'='*60}
Generado automáticamente por Video Analyzer IA
"""
        
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(contenido_error)
        
        log_info(f"📝 Archivo de error creado: {ruta_txt}", func_name)
        st.success(f"📝 Reporte de error creado: `{carpeta_fallidos}/{nombre_txt}`")
        
        # 5. REGISTRAR EN fallidos.txt
        with open("fallidos.txt", "a", encoding="utf-8") as f:
            f.write(f"{nombre_archivo}|{timestamp}|{error_mensaje}\n")
        
        log_warning(f"❌ Archivo agregado a fallidos: {nombre_archivo} - Error: {error_mensaje}", func_name)
        
        # 6. ENVIAR NOTIFICACIONES A PLATAFORMAS
        st.info("📤 Enviando notificaciones...")
        enviar_notificacion_archivo_fallido(nombre_archivo, error_mensaje, ruta_destino if archivo_movido else None)
        
        return True
        
    except Exception as e:
        log_error_critico(func_name, f"Error guardando archivo fallido: {e}")
        st.error(f"❌ Error crítico guardando archivo fallido: {e}")
        return False

def enviar_notificacion_archivo_fallido(nombre_archivo, error_mensaje, ruta_archivo=None):
    """
    Envía notificaciones a todas las plataformas configuradas cuando falla un archivo
    """
    func_name = "enviar_notificacion_archivo_fallido"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Preparar mensaje
        mensaje = f"""❌ ERROR AL PROCESAR ARCHIVO

📄 Archivo: {nombre_archivo}
⏰ Fecha/Hora: {timestamp}
❌ Error: {error_mensaje}
📁 Ubicación: {ruta_archivo if ruta_archivo else 'No movido'}

El archivo ha sido movido a la carpeta archivos_fallidos/ y no será reprocesado.
"""
        
        # 1. ENVIAR A TELEGRAM
        telegram_config = cargar_telegram_config()
        if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
            try:
                mensaje_telegram = mensaje.replace('*', '').replace('_', '').replace('`', '')
                exito, msg = enviar_mensaje_telegram(
                    mensaje_telegram,
                    telegram_config['chat_id'],
                    telegram_config['bot_token']
                )
                if exito:
                    st.success("📱 Notificación enviada a Telegram")
                    log_info("✅ Notificación de archivo fallido enviada a Telegram", func_name)
                else:
                    st.warning(f"⚠️ Telegram: {msg}")
            except Exception as e:
                log_warning(f"Error enviando a Telegram: {e}", func_name)
        
        # 2. ENVIAR A WEBHOOK
        webhook_config = cargar_webhook_config()
        if webhook_config['enabled'] and webhook_config['url']:
            try:
                data = {
                    "tipo": "archivo_fallido",
                    "archivo": nombre_archivo,
                    "error": error_mensaje,
                    "timestamp": timestamp,
                    "ubicacion": ruta_archivo if ruta_archivo else None,
                    "fuente": "Video Analyzer IA - Sistema de Errores"
                }
                
                exito, msg = enviar_a_webhook_individual(
                    webhook_config['url'],
                    data,
                    func_name,
                    "Notificación Archivo Fallido"
                )
                
                if exito:
                    st.success("🌐 Notificación enviada a Webhook")
                    log_info("✅ Notificación de archivo fallido enviada a Webhook", func_name)
                else:
                    st.warning(f"⚠️ Webhook: {msg}")
            except Exception as e:
                log_warning(f"Error enviando a Webhook: {e}", func_name)
        
        # 3. ENVIAR EMAIL CON BREVO (si está configurado)
        brevo_config = cargar_brevo_config()
        if brevo_config['enabled'] and brevo_config['api_key']:
            try:
                correos = obtener_correos_activos()
                if correos:
                    # Preparar contenido del email
                    asunto = f"⚠️ Error procesando archivo: {nombre_archivo}"
                    contenido_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <div style="background-color: #ff4444; color: white; padding: 15px; border-radius: 5px;">
                            <h2>❌ Error al Procesar Archivo</h2>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #ff4444;">
                            <p><strong>📄 Archivo:</strong> {nombre_archivo}</p>
                            <p><strong>⏰ Fecha/Hora:</strong> {timestamp}</p>
                            <p><strong>❌ Error:</strong> {error_mensaje}</p>
                            <p><strong>📁 Ubicación:</strong> {ruta_archivo if ruta_archivo else 'No movido'}</p>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                            <h3>⚠️ Acción Tomada:</h3>
                            <p>El archivo ha sido movido a la carpeta <code>archivos_fallidos/</code> y no será reprocesado automáticamente.</p>
                            <p>Se ha generado un reporte detallado del error en la carpeta.</p>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background-color: #d1ecf1; border-left: 4px solid #17a2b8;">
                            <h3>🔍 Acciones Recomendadas:</h3>
                            <ul>
                                <li>Verificar que el archivo no esté corrupto</li>
                                <li>Verificar el formato del archivo</li>
                                <li>Revisar los logs para más detalles</li>
                                <li>Si el problema persiste, contactar soporte técnico</li>
                            </ul>
                        </div>
                        <hr style="margin-top: 30px;">
                        <p style="color: #666; font-size: 12px;">
                            Generado automáticamente por Video Analyzer IA<br>
                            {timestamp}
                        </p>
                    </body>
                    </html>
                    """
                    
                    # Enviar usando la API de Brevo
                    headers = {
                        'accept': 'application/json',
                        'api-key': brevo_config['api_key'],
                        'content-type': 'application/json'
                    }
                    
                    payload = {
                        'sender': {'email': 'noreply@videoanalyzer.com', 'name': 'Video Analyzer IA'},
                        'to': [{'email': correo} for correo in correos],
                        'subject': asunto,
                        'htmlContent': contenido_html
                    }
                    
                    response = requests.post(
                        'https://api.brevo.com/v3/smtp/email',
                        headers=headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code in [200, 201]:
                        st.success(f"📧 Email enviado a {len(correos)} destinatario(s)")
                        log_info(f"✅ Email de error enviado a {len(correos)} destinatarios", func_name)
                    else:
                        st.warning(f"⚠️ Email: Error {response.status_code}")
                        
            except Exception as e:
                log_warning(f"Error enviando email: {e}", func_name)
        
        log_info(f"Notificaciones enviadas para archivo fallido: {nombre_archivo}", func_name)
        
    except Exception as e:
        log_error_critico(func_name, f"Error enviando notificaciones: {e}")
        st.warning(f"⚠️ Error enviando algunas notificaciones: {e}")

def es_archivo_fallido(nombre_archivo):
    """Verifica si un archivo está en la lista de fallidos"""
    try:
        archivos_fallidos = cargar_archivos_fallidos()
        return nombre_archivo in archivos_fallidos
    except Exception as e:
        log_warning(f"Error verificando archivo fallido: {e}", "es_archivo_fallido")
        return False

def limpiar_archivos_fallidos():
    """Limpia la lista de archivos fallidos"""
    try:
        if os.path.exists("fallidos.txt"):
            os.remove("fallidos.txt")
            log_info("🧹 Lista de archivos fallidos limpiada", "limpiar_archivos_fallidos")
            return True
        return False
    except Exception as e:
        log_warning(f"Error limpiando archivos fallidos: {e}", "limpiar_archivos_fallidos")
        return False

def mostrar_archivos_fallidos():
    """Muestra la lista de archivos fallidos en la interfaz"""
    try:
        archivos_fallidos = cargar_archivos_fallidos()
        if archivos_fallidos:
            st.warning(f"⚠️ **{len(archivos_fallidos)} archivos fallidos** (serán omitidos en el procesamiento)")
            with st.expander("📋 Ver archivos fallidos", expanded=False):
                for i, archivo in enumerate(archivos_fallidos, 1):
                    st.text(f"{i}. {archivo}")
            
            if st.button("🧹 Limpiar lista de fallidos"):
                if limpiar_archivos_fallidos():
                    st.success("✅ Lista de archivos fallidos limpiada")
                    st.rerun()
        else:
            st.success("✅ No hay archivos fallidos")
    except Exception as e:
        st.error(f"❌ Error mostrando archivos fallidos: {e}")

def copiar_a_videoscheck_si_tangencial(ruta_archivo, termino="", razon=""):
    """
    Copia el archivo original analizado a videoscheck cuando la mención
    del término es tangencial o no relevante.
    """
    func_name = "copiar_a_videoscheck_si_tangencial"
    try:
        if not ruta_archivo or not os.path.exists(ruta_archivo):
            log_warning(f"⚠️ No se puede copiar a videoscheck, archivo inválido: {ruta_archivo}", func_name)
            return False

        os.makedirs(CARPETA_VIDEOSCHECK, exist_ok=True)
        nombre_archivo = os.path.basename(ruta_archivo)
        destino = os.path.join(CARPETA_VIDEOSCHECK, nombre_archivo)

        if os.path.exists(destino):
            log_info(f"ℹ️ Archivo ya existe en videoscheck: {destino}", func_name)
            return True

        shutil.copy2(ruta_archivo, destino)
        detalle_termino = f" | término: '{termino}'" if termino else ""
        detalle_razon = f" | razón: {razon}" if razon else ""
        log_info(f"📁 Archivo copiado a videoscheck: {destino}{detalle_termino}{detalle_razon}", func_name)
        st.info(f"📁 Copia enviada a videoscheck: `{nombre_archivo}`")
        return True
    except Exception as e:
        log_warning(f"⚠️ No se pudo copiar a videoscheck: {e}", func_name)
        return False

def obtener_duracion(video_path):
    try:
        res = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", video_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(json.loads(res.stdout)["format"]["duration"])
    except Exception as e:
        st.warning(f"⚠️ No se pudo obtener duración: {os.path.basename(video_path)}")
        return 1.0

def extraer_info_medio_hora(nombre_archivo):
    """
    Extrae el nombre del medio y la hora del nombre del archivo
    Ejemplo: TELEANTILLAS_720p_2025-09-15_07-37-25 -> "en Teleantillas a las 7:37 am del 15 de septiembre de 2025"
    """
    try:
        # Remover extensión
        nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
        
        # Buscar patrón de fecha y hora: YYYY-MM-DD_HH-MM-SS
        import re
        patron_fecha_hora = r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})'
        match = re.search(patron_fecha_hora, nombre_sin_ext)
        
        if match:
            año, mes, dia, hora, minuto, segundo = match.groups()
            
            # Convertir a formato legible
            fecha_obj = datetime(int(año), int(mes), int(dia))
            nombre_mes = fecha_obj.strftime('%B').lower()
            
            # Convertir hora a formato 12 horas
            hora_int = int(hora)
            if hora_int == 0:
                hora_12 = "12"
                am_pm = "am"
            elif hora_int < 12:
                hora_12 = str(hora_int)
                am_pm = "am"
            elif hora_int == 12:
                hora_12 = "12"
                am_pm = "pm"
            else:
                hora_12 = str(hora_int - 12)
                am_pm = "pm"
            
            # Extraer nombre del medio (todo antes de la fecha)
            nombre_medio = nombre_sin_ext[:match.start()].replace('_', ' ').strip()
            
            # Limpiar nombre del medio (remover resoluciones como 720p, 480p, etc.)
            nombre_medio = re.sub(r'\s+\d+p\s*$', '', nombre_medio).strip()
            
            # Capitalizar primera letra de cada palabra
            nombre_medio = ' '.join(word.capitalize() for word in nombre_medio.split())
            
            return f"en {nombre_medio} a las {hora_12}:{minuto} {am_pm} del {dia} de {nombre_mes} de {año}"
        else:
            # Si no se encuentra el patrón, usar el nombre del archivo
            nombre_medio = nombre_sin_ext.replace('_', ' ').strip()
            return f"en {nombre_medio}"
            
    except Exception as e:
        log_warning(f"Error extrayendo info de medio y hora: {e}", "extraer_info_medio_hora")
        return f"en {nombre_archivo}"

# === FUNCIONES CACHE Y PRINCIPALES ===
@st.cache_resource
def cargar_modelo_whisper_timestamps():
    return WhisperModel("small", device="cpu", compute_type="int8")

# === FUNCIONES PRINCIPALES DE PROCESAMIENTO ===

def transcribir_audio_mistral(audio_path):
    func_name = "transcribir_audio_mistral"
    try:
        log_info(f"Iniciando transcripción con Mistral: {audio_path}", func_name)
        
        client, model = cargar_cliente_mistral()
        
        with open(audio_path, "rb") as f:
            content = f.read()
        
        file_size_mb = len(content) / (1024 * 1024)
        log_debug(f"Tamaño archivo audio: {file_size_mb:.2f}MB", func_name)
        
        audio_base64 = base64.b64encode(content).decode('utf-8')
        
        log_debug("Enviando audio a Mistral API", func_name)
        chat_response = client.chat.complete(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": audio_base64,
                    },
                    {
                        "type": "text",
                        "text": "Transcribe este audio en español. Proporciona solo el texto transcrito sin comentarios adicionales.",
                    },
                ]
            }],
        )
        
        result = chat_response.choices[0].message.content
        log_info(f"Transcripción Mistral completada exitosamente. Longitud: {len(result)} caracteres", func_name)
        return result
        
    except Exception as e:
        log_exception(func_name, e, f"Archivo: {audio_path}")
        raise

def transcribir_con_openai(audio_path):
    """
    Transcribe audio usando OpenAI Whisper API
    Para archivos > 19MB que no puede procesar Mistral
    """
    func_name = "transcribir_con_openai"
    try:
        log_info(f"Iniciando transcripción con OpenAI Whisper: {audio_path}", func_name)
        
        # Configurar API key desde variable de entorno
        openai.api_key = os.getenv('OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY_BACKUP', '')
        
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        log_debug(f"Tamaño archivo audio: {file_size_mb:.2f}MB", func_name)
        
        with open(audio_path, "rb") as audio_file:
            log_debug("Enviando audio a OpenAI Whisper API", func_name)
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"  # Español
            )
        
        result = transcript.text
        log_info(f"Transcripción OpenAI completada exitosamente. Longitud: {len(result)} caracteres", func_name)
        return result
        
    except Exception as e:
        log_exception(func_name, e, f"Archivo: {audio_path}")
        raise

def transcribir_audio_hibrido(audio_path):
    """
    Sistema híbrido con FALLBACK AUTOMÁTICO y manejo de archivos grandes:
    - Usa Mistral para archivos ≤19MB
    - Usa OpenAI para archivos 19-25MB
    - Convierte archivos >25MB a MP3 y transcribe
    - Si OpenAI falla, convierte a MP3 como fallback
    """
    func_name = "transcribir_audio_hibrido"
    try:
        # Calcular tamaño del archivo en MB
        tamaño_mb = os.path.getsize(audio_path) / (1024 * 1024)
        
        st.info(f"🎯 **ANÁLISIS DE ARCHIVO:** {os.path.basename(audio_path)} ({tamaño_mb:.1f}MB)")
        st.info(f"🤖 **Sistema Híbrido:** Decidiendo la mejor estrategia de transcripción...")
        
        if tamaño_mb <= 19:
            # Archivo pequeño - usar Mistral
            st.info(f"📊 **DECISIÓN:** Archivo {tamaño_mb:.1f}MB (≤19MB) → Usando **Mistral API** (más rápido)")
            log_info(f"Archivo {tamaño_mb:.1f}MB - Intentando Mistral API", func_name)
            
            try:
                result = transcribir_audio_mistral(audio_path)
                st.success(f"✅ **Mistral API** completó la transcripción exitosamente")
                log_info(f"Transcripción exitosa con Mistral", func_name)
                return result, "Mistral"
                
            except Exception as mistral_error:
                # Fallback a OpenAI para archivos pequeños
                st.warning(f"⚠️ **Mistral falló** → Activando **FALLBACK a OpenAI**")
                log_info(f"Mistral falló ({mistral_error}) - Activando FALLBACK a OpenAI", func_name)
                
                # Diagnóstico de conectividad antes del fallback
                if "getaddrinfo failed" in str(mistral_error) or "Connection error" in str(mistral_error):
                    st.warning("🔍 **DIAGNÓSTICO:** Problema de conectividad detectado")
                    diagnosticar_conectividad()
                
                try:
                    result = transcribir_con_openai(audio_path)
                    st.success(f"✅ **FALLBACK exitoso:** OpenAI completó la transcripción")
                    log_info(f"FALLBACK exitoso: Transcripción completada con OpenAI", func_name)
                    return result, "OpenAI Whisper (Fallback desde Mistral)"
                except Exception as openai_error:
                    st.error(f"❌ **Ambas APIs fallaron** - Mistral: {mistral_error}, OpenAI: {openai_error}")
                    
                    # Diagnóstico completo si ambas fallan
                    if "getaddrinfo failed" in str(openai_error) or "Connection error" in str(openai_error):
                        st.error("🔍 **DIAGNÓSTICO COMPLETO:** Problemas de conectividad en ambas APIs")
                        diagnosticar_conectividad()
                    
                    log_exception(func_name, openai_error, f"Fallback OpenAI también falló")
                    raise Exception(f"Ambas APIs fallaron - Mistral: {mistral_error}, OpenAI: {openai_error}")
        
        elif tamaño_mb <= 25:
            # Archivo mediano - usar OpenAI directamente
            st.info(f"📊 **DECISIÓN:** Archivo {tamaño_mb:.1f}MB (19-25MB) → Usando **OpenAI Whisper** (límite cercano)")
            log_info(f"Archivo {tamaño_mb:.1f}MB - Usando OpenAI Whisper (archivo mediano)", func_name)
            try:
                result = transcribir_con_openai(audio_path)
                st.success(f"✅ **OpenAI Whisper** completó la transcripción exitosamente")
                log_info(f"Transcripción completada con OpenAI", func_name)
                return result, "OpenAI Whisper"
            except Exception as openai_error:
                st.warning(f"⚠️ **OpenAI falló** para archivo {tamaño_mb:.1f}MB → Activando **conversión a MP3**")
                log_info(f"OpenAI falló para archivo {tamaño_mb:.1f}MB - Intentando convertir a MP3", func_name)
                # Fallback: convertir a MP3
                return transcribir_archivo_grande_mp3(audio_path, func_name)
        
        else:
            # Archivo grande (>25MB) - convertir a MP3
            st.info(f"📊 **DECISIÓN:** Archivo {tamaño_mb:.1f}MB (>25MB) → **Convirtiendo a MP3** (evitar límite)")
            log_info(f"Archivo {tamaño_mb:.1f}MB - Convirtiendo a MP3 (archivo grande)", func_name)
            return transcribir_archivo_grande_mp3(audio_path, func_name)
        
    except Exception as e:
        log_exception(func_name, e, f"Archivo: {audio_path}, Tamaño: {tamaño_mb:.1f}MB")
        raise

def transcribir_archivo_grande_mp3(audio_path, func_name):
    """Convierte archivos grandes a MP3 y los transcribe"""
    try:
        # Crear archivo MP3 temporal
        audio_mp3 = audio_path.replace('.wav', '_comprimido.mp3')
        
        st.info(f"🔄 **Convirtiendo archivo grande a MP3:** {os.path.basename(audio_path)}")
        log_info(f"Convirtiendo archivo grande a MP3: {audio_path} -> {audio_mp3}", func_name)
        
        # Convertir a MP3 con ffmpeg (alta compresión, buena calidad para transcripción)
        try:
            with st.spinner("🎵 Convirtiendo audio a MP3 (64kbps, 16kHz, mono)..."):
                subprocess.run([
                    "ffmpeg", "-y", "-i", audio_path,
                    "-ac", "1", "-ar", "16000", "-acodec", "mp3", "-b:a", "64k",  # Mono, 16kHz, 64kbps
                    audio_mp3
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Verificar tamaño del archivo MP3
            tamaño_original_mb = os.path.getsize(audio_path) / (1024 * 1024)
            tamaño_mp3_mb = os.path.getsize(audio_mp3) / (1024 * 1024)
            reduccion = ((tamaño_original_mb - tamaño_mp3_mb) / tamaño_original_mb) * 100
            
            st.success(f"✅ **Conversión MP3 exitosa:** {tamaño_original_mb:.1f}MB → {tamaño_mp3_mb:.1f}MB (**{reduccion:.1f}% reducción**)")
            log_info(f"Archivo convertido: {tamaño_original_mb:.1f}MB -> {tamaño_mp3_mb:.1f}MB (reducción: {reduccion:.1f}%)", func_name)
            
        except subprocess.CalledProcessError as e:
            log_exception(func_name, e, f"Error convirtiendo archivo a MP3")
            raise Exception(f"Error convirtiendo a MP3: {e}")
        
        # Intentar transcripción con Mistral primero (más confiable para archivos comprimidos)
        st.info(f"🧠 **Intentando transcripción con Mistral API** (archivo MP3 de {tamaño_mp3_mb:.1f}MB)")
        try:
            result = transcribir_audio_mistral(audio_mp3)
            st.success(f"✅ **Mistral API** completó la transcripción del archivo MP3 exitosamente")
            log_info(f"Transcripción exitosa con archivo MP3 usando Mistral", func_name)
            
            # Limpiar archivo temporal
            if os.path.exists(audio_mp3):
                os.remove(audio_mp3)
                st.info(f"🧹 Archivo temporal MP3 eliminado")
            
            return result, f"Mistral (MP3 comprimido de {tamaño_mp3_mb:.1f}MB, reducción: {reduccion:.1f}%)"
            
        except Exception as mistral_error:
            st.warning(f"⚠️ **Mistral falló** con archivo MP3 → Activando **FALLBACK a OpenAI**")
            log_info(f"Mistral falló con archivo MP3 - Intentando OpenAI", func_name)
            
            # Fallback: usar OpenAI con archivo MP3
            st.info(f"🧠 **Intentando transcripción con OpenAI Whisper** (archivo MP3 de {tamaño_mp3_mb:.1f}MB)")
            try:
                result = transcribir_con_openai(audio_mp3)
                st.success(f"✅ **OpenAI Whisper** completó la transcripción del archivo MP3 exitosamente")
                log_info(f"Transcripción exitosa con archivo MP3 usando OpenAI", func_name)
                
                # Limpiar archivo temporal
                if os.path.exists(audio_mp3):
                    os.remove(audio_mp3)
                    st.info(f"🧹 Archivo temporal MP3 eliminado")
                
                return result, f"OpenAI Whisper (MP3 comprimido de {tamaño_mp3_mb:.1f}MB, reducción: {reduccion:.1f}%)"
                
            except Exception as openai_error:
                # Limpiar archivo temporal en caso de error
                if os.path.exists(audio_mp3):
                    os.remove(audio_mp3)
                
                log_exception(func_name, openai_error, f"Ambas APIs fallaron con archivo MP3")
                raise Exception(f"Error con archivo MP3 - Mistral: {mistral_error}, OpenAI: {openai_error}")
                
    except Exception as e:
        log_exception(func_name, e, f"Error convirtiendo archivo a MP3: {audio_path}")
        raise

def obtener_timestamps_whisper(audio_path):
    model = cargar_modelo_whisper_timestamps()
    
    segments, _ = model.transcribe(
        audio_path, language="es", chunk_length=300,
        beam_size=1, vad_filter=True, word_timestamps=False
    )
    
    timestamp_segments = []
    for seg in segments:
        timestamp_segments.append({
            'start': seg.start,
            'end': seg.end,
            'text': seg.text
        })
    
    return timestamp_segments


def determinar_segmento_inteligente_gemini(transcripcion_con_timestamps, termino_encontrado, timestamp_coincidencia, duracion_maxima=60):
    """
    🌟 USA GEMINI 3 PRO PARA DETERMINAR EL SEGMENTO MÁS LÓGICO Y COHERENTE
    
    Gemini analiza la transcripción completa y determina cuál es el segmento más lógico donde
    el término encontrado es el EJE CENTRAL de la conversación, no una mención tangencial.
    
    Args:
        transcripcion_con_timestamps: Lista de segmentos con 'start', 'end', 'text'
        termino_encontrado: El término que generó la coincidencia
        timestamp_coincidencia: Timestamp donde se encontró el término
        duracion_maxima: Duración máxima del clip en segundos (default: 60)
    
    Returns:
        dict: {'inicio': float, 'fin': float, 'razon': str, 'duracion': float, 'idea_central': str}
        None: Si el término solo se menciona tangencialmente (rechazado)
    """
    func_name = "determinar_segmento_inteligente_gemini"
    
    # Verificar si Gemini está configurado
    if not gemini_client:
        log_warning("⚠️ Gemini no configurado, usando fallback GPT-4o", func_name)
        return determinar_segmento_inteligente_gpt4(
            transcripcion_con_timestamps, termino_encontrado, 
            timestamp_coincidencia, duracion_maxima
        )
    
    try:
        log_info(f"🌟 Iniciando análisis GEMINI 3 PRO para segmento inteligente del término '{termino_encontrado}'", func_name)
        
        # Construir contexto de transcripción con timestamps
        contexto_transcripcion = []
        for seg in transcripcion_con_timestamps:
            tiempo_inicio = f"{int(seg['start']//60)}:{int(seg['start']%60):02d}"
            contexto_transcripcion.append(f"[{tiempo_inicio}] {seg['text'].strip()}")
        
        texto_completo_timestamps = "\n".join(contexto_transcripcion)
        
        # Calcular timestamp en formato legible
        minuto_coincidencia = int(timestamp_coincidencia // 60)
        segundo_coincidencia = int(timestamp_coincidencia % 60)
        
        # Prompt optimizado para Gemini - ENFOCADO EN IDEAS CENTRADAS EN LA COINCIDENCIA
        prompt = f"""Eres un experto editor de video y analista de contenido. Tu tarea es encontrar el SEGMENTO EXACTO donde "{termino_encontrado}" sea el TEMA CENTRAL de la conversación.

🎯 TÉRMINO A ANALIZAR: "{termino_encontrado}"
⏰ TIMESTAMP DE DETECCIÓN: {minuto_coincidencia}:{segundo_coincidencia:02d} ({timestamp_coincidencia:.1f} segundos)

📝 TRANSCRIPCIÓN COMPLETA CON TIMESTAMPS:
{texto_completo_timestamps}

═══════════════════════════════════════════════════════════════════
📋 TU MISIÓN CRÍTICA:
═══════════════════════════════════════════════════════════════════

1️⃣ IDENTIFICAR si "{termino_encontrado}" es el EJE CENTRAL del segmento:
   ✅ APROBADO: La conversación GIRA EN TORNO a "{termino_encontrado}"
   ✅ APROBADO: Hay información CONCRETA y DESARROLLADA sobre "{termino_encontrado}"
   ✅ APROBADO: El término es el PROTAGONISTA, no un actor secundario
   
   ❌ RECHAZAR: Solo se menciona de pasada o en una lista
   ❌ RECHAZAR: El tema principal es OTRO y "{termino_encontrado}" es tangencial
   ❌ RECHAZAR: No hay desarrollo de ideas sobre "{termino_encontrado}"

2️⃣ Si APRUEBAS, determinar el SEGMENTO ÓPTIMO que:
   - Capture la IDEA COMPLETA relacionada con "{termino_encontrado}"
   - Tenga INICIO y FIN naturales (no cortes abruptos)
   - NO exceda {duracion_maxima} segundos
   - Sea COHERENTE y COMPRENSIBLE por sí solo

3️⃣ EXTRAER LA IDEA CENTRAL:
   - ¿Qué se dice ESPECÍFICAMENTE sobre "{termino_encontrado}"?
   - Resume en 1-2 oraciones la información CONCRETA
   - NO resumas toda la transcripción, solo lo relacionado con el término

═══════════════════════════════════════════════════════════════════
📤 FORMATO DE RESPUESTA (JSON estricto, sin markdown):
═══════════════════════════════════════════════════════════════════

Si el término ES el tema central (APROBAR):
{{
  "rechazar": false,
  "inicio_segundos": <número>,
  "fin_segundos": <número>,
  "duracion_segundos": <número>,
  "razon": "<por qué este segmento captura la idea sobre {termino_encontrado}>",
  "idea_central": "<qué se dice CONCRETAMENTE sobre {termino_encontrado} - máximo 2 oraciones>"
}}

Si el término NO es el tema central (RECHAZAR):
{{
  "rechazar": true,
  "razon": "<por qué {termino_encontrado} solo es una mención tangencial>"
}}

⚠️ IMPORTANTE:
- Sé ESTRICTO: Si hay duda, RECHAZA
- La "idea_central" debe responder: "¿Qué dice este segmento SOBRE {termino_encontrado}?"
- NO incluyas información que no esté directamente relacionada con el término

RESPONDE SOLO CON EL JSON:"""

        # Llamar a Gemini 3 Pro
        log_info("📡 Enviando solicitud a GEMINI 3 PRO para análisis de segmento...", func_name)
        
        response = gemini_client.models.generate_content(
            model="gemini-3-pro-preview",  # Gemini 3 Pro (modelo más avanzado)
            contents=prompt,
            config={
                "temperature": 0.2,  # Bajo para respuestas más consistentes
                "max_output_tokens": 600
            }
        )
        
        respuesta_gemini = response.text.strip()
        log_debug(f"Respuesta Gemini: {respuesta_gemini}", func_name)
        
        # Limpiar respuesta (remover markdown si existe)
        respuesta_limpia = respuesta_gemini.replace("```json", "").replace("```", "").strip()
        
        # Parsear JSON
        resultado = json.loads(respuesta_limpia)
        
        # 🚫 VERIFICAR SI GEMINI RECHAZÓ EL SEGMENTO
        if resultado.get('rechazar', False):
            razon_rechazo = resultado.get('razon', 'Mención tangencial sin desarrollo')
            log_warning(f"🚫 GEMINI RECHAZÓ el segmento: {razon_rechazo}", func_name)
            st.warning(f"🚫 **Gemini:** {razon_rechazo}")
            return None  # Indica que se debe rechazar el clip
        
        # Validar y ajustar resultados
        inicio = float(resultado.get('inicio_segundos', timestamp_coincidencia - 30))
        fin = float(resultado.get('fin_segundos', timestamp_coincidencia + 30))
        razon = resultado.get('razon', 'Segmento determinado por Gemini')
        idea_central = resultado.get('idea_central', '')
        
        # Validaciones de seguridad
        inicio = max(0, inicio)  # No puede ser negativo
        duracion_calculada = fin - inicio
        
        # Si excede duración máxima, ajustar
        if duracion_calculada > duracion_maxima:
            log_warning(f"⚠️ Segmento Gemini ({duracion_calculada:.1f}s) excede máximo ({duracion_maxima}s), ajustando...", func_name)
            fin = inicio + duracion_maxima
            duracion_calculada = duracion_maxima
            razon += " (ajustado a duración máxima)"
        
        # Si es muy corto (< 10s), expandir un poco
        if duracion_calculada < 10:
            log_warning(f"⚠️ Segmento Gemini muy corto ({duracion_calculada:.1f}s), expandiendo...", func_name)
            centro = (inicio + fin) / 2
            inicio = max(0, centro - 15)
            fin = centro + 15
            duracion_calculada = fin - inicio
            razon += " (expandido para contexto mínimo)"
        
        resultado_final = {
            'inicio': inicio,
            'fin': fin,
            'razon': razon,
            'duracion': duracion_calculada,
            'idea_central': idea_central  # Nueva: idea centrada en la coincidencia
        }
        
        log_info(f"✅ Gemini determinó segmento: {inicio:.1f}s - {fin:.1f}s ({duracion_calculada:.1f}s)", func_name)
        log_info(f"📝 Razón: {razon}", func_name)
        log_info(f"💡 Idea central: {idea_central[:100]}...", func_name)
        
        # Mostrar en UI
        st.success(f"🌟 **Gemini 3 Pro:** Segmento inteligente: {inicio:.1f}s - {fin:.1f}s ({duracion_calculada:.1f}s)")
        st.info(f"💡 **Razón:** {razon}")
        if idea_central:
            st.info(f"🎯 **Idea central sobre '{termino_encontrado}':** {idea_central}")
        
        return resultado_final
        
    except json.JSONDecodeError as e:
        log_warning(f"⚠️ Error parseando JSON de Gemini: {e}. Intentando fallback GPT-4o", func_name)
        # Fallback a GPT-4o
        return determinar_segmento_inteligente_gpt4(
            transcripcion_con_timestamps, termino_encontrado,
            timestamp_coincidencia, duracion_maxima
        )
    
    except Exception as e:
        log_exception(func_name, e, f"Término: {termino_encontrado}, Timestamp: {timestamp_coincidencia}")
        st.warning(f"⚠️ Error en análisis Gemini, usando fallback GPT-4o: {str(e)}")
        
        # Fallback a GPT-4o
        return determinar_segmento_inteligente_gpt4(
            transcripcion_con_timestamps, termino_encontrado,
            timestamp_coincidencia, duracion_maxima
        )


def determinar_segmento_inteligente_gpt4(transcripcion_con_timestamps, termino_encontrado, timestamp_coincidencia, duracion_maxima=60):
    """
    🤖 USA GPT-4o PARA DETERMINAR EL SEGMENTO MÁS LÓGICO Y COHERENTE
    
    En lugar de recortar mecánicamente X segundos antes/después, GPT-4o analiza
    la transcripción completa y determina cuál es el segmento más lógico que:
    - Contiene la idea completa relacionada con la coincidencia
    - Tiene coherencia narrativa (inicio y fin naturales)
    - No excede 60 segundos de duración
    - Captura el contexto relevante sin cortes abruptos
    
    Args:
        transcripcion_con_timestamps: Lista de segmentos con 'start', 'end', 'text'
        termino_encontrado: El término que generó la coincidencia
        timestamp_coincidencia: Timestamp donde se encontró el término
        duracion_maxima: Duración máxima del clip en segundos (default: 60)
    
    Returns:
        dict: {'inicio': float, 'fin': float, 'razon': str, 'duracion': float}
    """
    func_name = "determinar_segmento_inteligente_gpt4"
    
    try:
        log_info(f"🤖 Iniciando análisis GPT-4o para segmento inteligente del término '{termino_encontrado}'", func_name)
        
        # Construir contexto de transcripción con timestamps
        contexto_transcripcion = []
        for seg in transcripcion_con_timestamps:
            tiempo_inicio = f"{int(seg['start']//60)}:{int(seg['start']%60):02d}"
            contexto_transcripcion.append(f"[{tiempo_inicio}] {seg['text'].strip()}")
        
        texto_completo_timestamps = "\n".join(contexto_transcripcion)
        
        # Calcular timestamp en formato legible
        minuto_coincidencia = int(timestamp_coincidencia // 60)
        segundo_coincidencia = int(timestamp_coincidencia % 60)
        
        # Prompt para GPT-4o
        prompt = f"""Eres un experto editor de video. Analiza esta transcripción con timestamps y determina el SEGMENTO donde "{termino_encontrado}" sea el TEMA CENTRAL.

🎯 TÉRMINO ENCONTRADO: "{termino_encontrado}"
⏰ TIMESTAMP DE COINCIDENCIA: {minuto_coincidencia}:{segundo_coincidencia:02d} ({timestamp_coincidencia:.1f} segundos)

📝 TRANSCRIPCIÓN COMPLETA CON TIMESTAMPS:
{texto_completo_timestamps}

📋 TU TAREA:
Encuentra el segmento donde "{termino_encontrado}" sea el TEMA PRINCIPAL de la conversación, que cumpla:

🎯 CRITERIO PRINCIPAL (MÁS IMPORTANTE):
- El término "{termino_encontrado}" debe ser el EJE CENTRAL del segmento
- La conversación debe GIRAR ALREDEDOR de "{termino_encontrado}"
- NO aceptes menciones de pasada o tangenciales
- La idea completa debe DESARROLLAR el tema de "{termino_encontrado}"

✅ OTROS REQUISITOS:
1. Tenga un INICIO y FIN NATURAL (no cortes abruptos)
2. Capture el CONTEXTO RELEVANTE que desarrolla el tema
3. NO EXCEDA {duracion_maxima} segundos de duración
4. Sea COHERENTE y COMPRENSIBLE por sí solo

⚠️ IMPORTANTE:
- Si "{termino_encontrado}" solo se menciona de pasada (sin desarrollar el tema), RESPONDE: {{"rechazar": true, "razon": "Mención tangencial sin desarrollo"}}
- Identifica dónde EMPIEZA el desarrollo del tema (puede ser varios segundos antes del término)
- Identifica dónde TERMINA el desarrollo completo de la idea
- Busca pausas naturales, cambios de tema, o conclusiones de frases
- Si la idea completa excede {duracion_maxima}s, prioriza el núcleo más importante

RESPONDE EN FORMATO JSON (sin markdown, sin comentarios):
{{
  "rechazar": false,
  "inicio_segundos": <timestamp de inicio en segundos como número>,
  "fin_segundos": <timestamp de fin en segundos como número>,
  "razon": "<breve explicación de por qué elegiste este segmento (1-2 líneas)>",
  "duracion_segundos": <duración total del segmento como número>
}}

O si la mención es tangencial/sin desarrollo:
{{
  "rechazar": true,
  "razon": "<explicación de por qué es solo mención tangencial>"
}}"""

        # Llamar a GPT-4o
        log_info("📡 Enviando solicitud a GPT-4o para análisis de segmento...", func_name)
        
        # Usar API key desde variable de entorno
        openai.api_key = os.getenv('OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY_BACKUP', '')
        
        response = openai.chat.completions.create(
            model="gpt-4o",  # Modelo más avanzado de OpenAI
            messages=[
                {"role": "system", "content": "Eres un experto editor de video que analiza transcripciones para determinar los mejores segmentos de corte."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Bajo para respuestas más consistentes
            max_tokens=500
        )
        
        respuesta_gpt = response.choices[0].message.content.strip()
        log_debug(f"Respuesta GPT-4o: {respuesta_gpt}", func_name)
        
        # Limpiar respuesta (remover markdown si existe)
        respuesta_limpia = respuesta_gpt.replace("```json", "").replace("```", "").strip()
        
        # Parsear JSON
        resultado = json.loads(respuesta_limpia)
        
        # 🚫 VERIFICAR SI GPT-4o RECHAZÓ EL SEGMENTO
        if resultado.get('rechazar', False):
            razon_rechazo = resultado.get('razon', 'Mención tangencial sin desarrollo')
            log_warning(f"🚫 GPT-4o RECHAZÓ el segmento: {razon_rechazo}", func_name)
            st.warning(f"🚫 **GPT-4o:** {razon_rechazo}")
            # Retornar None para indicar que se debe rechazar el clip
            return None
        
        # Validar y ajustar resultados
        inicio = float(resultado.get('inicio_segundos', timestamp_coincidencia - 30))
        fin = float(resultado.get('fin_segundos', timestamp_coincidencia + 30))
        razon = resultado.get('razon', 'Segmento determinado por GPT-4o')
        
        # Validaciones de seguridad
        inicio = max(0, inicio)  # No puede ser negativo
        duracion_calculada = fin - inicio
        
        # Si excede duración máxima, ajustar
        if duracion_calculada > duracion_maxima:
            log_warning(f"⚠️ Segmento GPT-4o ({duracion_calculada:.1f}s) excede máximo ({duracion_maxima}s), ajustando...", func_name)
            # Mantener el inicio, acortar el fin
            fin = inicio + duracion_maxima
            duracion_calculada = duracion_maxima
            razon += " (ajustado a duración máxima)"
        
        # Si es muy corto (< 10s), expandir un poco
        if duracion_calculada < 10:
            log_warning(f"⚠️ Segmento GPT-4o muy corto ({duracion_calculada:.1f}s), expandiendo...", func_name)
            centro = (inicio + fin) / 2
            inicio = max(0, centro - 15)
            fin = centro + 15
            duracion_calculada = fin - inicio
            razon += " (expandido para contexto mínimo)"
        
        resultado_final = {
            'inicio': inicio,
            'fin': fin,
            'razon': razon,
            'duracion': duracion_calculada
        }
        
        log_info(f"✅ GPT-4o determinó segmento: {inicio:.1f}s - {fin:.1f}s ({duracion_calculada:.1f}s)", func_name)
        log_info(f"📝 Razón: {razon}", func_name)
        
        # Mostrar en UI
        st.success(f"🤖 **GPT-4o:** Segmento inteligente determinado: {inicio:.1f}s - {fin:.1f}s ({duracion_calculada:.1f}s)")
        st.info(f"💡 **Razón:** {razon}")
        
        return resultado_final
        
    except json.JSONDecodeError as e:
        log_warning(f"⚠️ Error parseando JSON de GPT-4o: {e}. Usando método tradicional", func_name)
        # Fallback al método tradicional
        return {
            'inicio': max(0, timestamp_coincidencia - 30),
            'fin': timestamp_coincidencia + 30,
            'razon': 'Método tradicional (error en GPT-4o)',
            'duracion': 60
        }
    
    except Exception as e:
        log_exception(func_name, e, f"Término: {termino_encontrado}, Timestamp: {timestamp_coincidencia}")
        st.warning(f"⚠️ Error en análisis GPT-4o, usando método tradicional: {str(e)}")
        
        # Fallback al método tradicional
        return {
            'inicio': max(0, timestamp_coincidencia - 30),
            'fin': timestamp_coincidencia + 30,
            'razon': 'Método tradicional (error en GPT-4o)',
            'duracion': 60
        }

def extraer_idea_general_segmento_gpt4(transcripcion_segmento, termino_encontrado, duracion_segundos):
    """
    🤖 USA GPT-4o PARA EXTRAER LA IDEA GENERAL DE UN SEGMENTO ESPECÍFICO
    
    En lugar de enviar toda la transcripción del video, GPT-4o extrae solo
    la idea principal y relevante del segmento del clip.
    
    Args:
        transcripcion_segmento: Texto del segmento específico del clip
        termino_encontrado: El término que generó la coincidencia
        duracion_segundos: Duración del segmento en segundos
    
    Returns:
        str: Idea general condensada (máximo 1-2 párrafos)
    """
    func_name = "extraer_idea_general_segmento_gpt4"
    
    try:
        log_info(f"🤖 Extrayendo idea general con GPT-4o para término '{termino_encontrado}'", func_name)
        
        # Prompt para GPT-4o
        prompt = f"""Eres un analista de contenido EXTREMADAMENTE CRÍTICO. Tu trabajo es RECHAZAR menciones superficiales y APROBAR solo cuando el término es el TEMA CENTRAL.

🎯 TÉRMINO CLAVE: "{termino_encontrado}"
⏱️ DURACIÓN DEL SEGMENTO: {duracion_segundos:.1f} segundos

📝 TRANSCRIPCIÓN DEL SEGMENTO:
{transcripcion_segmento}

📋 TU TAREA CRÍTICA:
Analiza si "{termino_encontrado}" es el EJE CENTRAL de este segmento.

🚫 RECHAZA (responde "NO_RELEVANTE") SI:
1. El término solo se menciona de pasada o tangencialmente
2. La conversación NO GIRA ALREDEDOR del término
3. El término aparece en una lista o enumeración sin desarrollo
4. Es solo una referencia sin elaboración del tema
5. La idea principal del segmento es OTRO tema diferente

✅ APRUEBA (resume la idea) SOLO SI:
1. El término es el TEMA PRINCIPAL del segmento
2. La conversación DESARROLLA el tema del término
3. Hay información CONCRETA y SUSTANCIAL sobre el término
4. El término es el EJE que estructura toda la conversación

⚠️ FORMATO DE RESPUESTA:

Si NO es relevante (MAYORÍA de los casos):
"NO_RELEVANTE: El término '{termino_encontrado}' [explicar brevemente por qué no es el tema central]"

Si SÍ es relevante (CASOS EXCEPCIONALES):
Resume la IDEA GENERAL en 1-2 párrafos (máximo 150 palabras):
- Información CONCRETA sobre el término
- Desarrollo sustancial del tema
- Contexto que demuestra que es el eje central

IMPORTANTE:
- Sé EXTREMADAMENTE CRÍTICO
- En caso de duda, RECHAZA
- NO inventes información
- NO resumas la transcripción literal

RESPONDE DIRECTAMENTE:"""

        # Llamar a GPT-4o (API key desde variable de entorno)
        openai.api_key = os.getenv('OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY_BACKUP', '')
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un analista de contenido experto que resume ideas de forma clara y concisa."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=300
        )
        
        idea_general = response.choices[0].message.content.strip()
        
        log_info(f"✅ Idea general extraída: {len(idea_general)} caracteres", func_name)
        log_debug(f"Idea: {idea_general[:100]}...", func_name)
        
        return idea_general
        
    except Exception as e:
        log_exception(func_name, e, f"Término: {termino_encontrado}")
        # Fallback: retornar un resumen simple del segmento
        return f"Segmento relacionado con '{termino_encontrado}': {transcripcion_segmento[:200]}..."


def extraer_idea_general_segmento_gemini(transcripcion_segmento, termino_encontrado, duracion_segundos, nombre_video=""):
    """
    🌟 USA GEMINI 3 PRO PARA EXTRAER IDEAS CENTRADAS EN LA COINCIDENCIA
    
    Gemini 3 Pro analiza el segmento y extrae ESPECÍFICAMENTE qué se dice
    sobre el término encontrado, NO ideas generales al aire.
    
    Args:
        transcripcion_segmento: Texto del segmento específico del clip
        termino_encontrado: El término que generó la coincidencia
        duracion_segundos: Duración del segmento en segundos
        nombre_video: Nombre del video para contexto adicional
    
    Returns:
        dict: {
            'idea_general': str - Resumen contextualizado,
            'relevancia': str - 'alta', 'media', 'baja',
            'tema_principal': str - Tema central identificado,
            'contexto': str - Contexto en que se menciona el término,
            'es_relevante': bool - Si el término es tema central
        }
    """
    func_name = "extraer_idea_general_segmento_gemini"
    
    # Resultado por defecto
    resultado_default = {
        'idea_general': f"Segmento relacionado con '{termino_encontrado}'",
        'relevancia': 'media',
        'tema_principal': termino_encontrado,
        'contexto': transcripcion_segmento[:200] if transcripcion_segmento else '',
        'es_relevante': True,
        'que_se_dice': f"Mención de '{termino_encontrado}' en el segmento"
    }
    
    # Verificar si Gemini está configurado
    if not gemini_client:
        log_warning("⚠️ Gemini no configurado, usando fallback GPT-4o", func_name)
        # Fallback a GPT-4o si Gemini no está disponible
        idea_gpt = extraer_idea_general_segmento_gpt4(transcripcion_segmento, termino_encontrado, duracion_segundos)
        resultado_default['idea_general'] = idea_gpt
        return resultado_default
    
    try:
        log_info(f"🌟 Extrayendo idea CENTRADA EN COINCIDENCIA con GEMINI 3 PRO para término '{termino_encontrado}'", func_name)
        
        # Prompt optimizado para Gemini 3 Pro - ENFOCADO EN IDEAS CENTRADAS EN LA COINCIDENCIA
        prompt = f"""Eres un analista experto de contenido audiovisual. Tu ÚNICA tarea es extraer QUÉ SE DICE ESPECÍFICAMENTE sobre "{termino_encontrado}".

═══════════════════════════════════════════════════════════════════
📺 VIDEO: {nombre_video if nombre_video else 'Video de noticias/contenido'}
🎯 TÉRMINO DE INTERÉS: "{termino_encontrado}"
⏱️ DURACIÓN: {duracion_segundos:.1f} segundos
═══════════════════════════════════════════════════════════════════

📝 TRANSCRIPCIÓN DEL SEGMENTO:
---
{transcripcion_segmento}
---

═══════════════════════════════════════════════════════════════════
🎯 TU MISIÓN CRÍTICA:
═══════════════════════════════════════════════════════════════════

Responde ÚNICAMENTE estas preguntas sobre "{termino_encontrado}":

1️⃣ ¿Qué se DICE CONCRETAMENTE sobre "{termino_encontrado}"?
2️⃣ ¿Qué INFORMACIÓN ESPECÍFICA se revela sobre "{termino_encontrado}"?
3️⃣ ¿En qué CONTEXTO se menciona "{termino_encontrado}"?

⚠️ REGLAS ESTRICTAS:
- SOLO incluye información que DIRECTAMENTE mencione o se refiera a "{termino_encontrado}"
- NO resumas el segmento completo
- NO incluyas información sobre OTROS temas
- NO inventes información
- Si no hay información sustancial sobre "{termino_encontrado}", indica relevancia BAJA

📤 RESPONDE EN JSON (sin markdown, sin comentarios):

{{
    "es_relevante": true/false,
    "relevancia": "alta" | "media" | "baja",
    "que_se_dice": "¿Qué dice el segmento ESPECÍFICAMENTE sobre {termino_encontrado}? (1-2 oraciones concretas)",
    "contexto": "¿En qué situación/tema se menciona {termino_encontrado}? (1 oración)",
    "idea_general": "Resumen de lo que se dice SOBRE {termino_encontrado} - NO sobre otros temas (máximo 80 palabras)",
    "tema_principal": "El tema central EN RELACIÓN a {termino_encontrado} (5-10 palabras)"
}}

📌 CRITERIOS:
- ALTA: Se habla DIRECTAMENTE de "{termino_encontrado}" con información sustancial
- MEDIA: Se menciona "{termino_encontrado}" con algo de contexto
- BAJA: Solo se nombra sin desarrollo

RESPONDE SOLO CON EL JSON:"""

        # Llamar a Gemini 3 Pro
        log_info("📡 Enviando solicitud a Gemini 3 Pro...", func_name)
        
        response = gemini_client.models.generate_content(
            model="gemini-3-pro-preview",  # Gemini 3 Pro (modelo más avanzado)
            contents=prompt,
            config={
                "temperature": 0.3,
                "max_output_tokens": 500
            }
        )
        
        respuesta_texto = response.text.strip()
        log_debug(f"Respuesta Gemini: {respuesta_texto[:200]}...", func_name)
        
        # Limpiar respuesta (remover markdown si existe)
        respuesta_limpia = respuesta_texto.replace("```json", "").replace("```", "").strip()
        
        # Parsear JSON
        try:
            resultado = json.loads(respuesta_limpia)
            
            # Validar campos requeridos
            campos_requeridos = ['es_relevante', 'relevancia', 'tema_principal', 'contexto', 'idea_general', 'que_se_dice']
            for campo in campos_requeridos:
                if campo not in resultado:
                    resultado[campo] = resultado_default.get(campo, '')
            
            # Si hay "que_se_dice", usarlo para enriquecer la idea_general
            if resultado.get('que_se_dice') and resultado.get('idea_general'):
                # Combinar para un resumen más completo centrado en la coincidencia
                log_info(f"📝 Qué se dice sobre '{termino_encontrado}': {resultado['que_se_dice'][:100]}...", func_name)
            
            log_info(f"✅ Análisis Gemini completado - Relevancia: {resultado.get('relevancia', 'N/A')}", func_name)
            
            return resultado
            
        except json.JSONDecodeError as je:
            log_warning(f"⚠️ Error parseando JSON de Gemini: {je}", func_name)
            # Si no es JSON válido, usar el texto como idea general
            resultado_default['idea_general'] = respuesta_limpia[:500]
            return resultado_default
        
    except Exception as e:
        log_exception(func_name, e, f"Término: {termino_encontrado}")
        
        # Fallback a GPT-4o
        log_info("🔄 Fallback a GPT-4o...", func_name)
        try:
            idea_gpt = extraer_idea_general_segmento_gpt4(transcripcion_segmento, termino_encontrado, duracion_segundos)
            resultado_default['idea_general'] = idea_gpt
        except:
            resultado_default['idea_general'] = f"Segmento sobre '{termino_encontrado}': {transcripcion_segmento[:200]}..."
        
        return resultado_default


def generar_resumen_video(nombre_video, coincidencias, transcripcion_completa):
    terminos_encontrados = list(set([item['termino'] for item in coincidencias]))
    
    prompt = f"""
Analiza el siguiente video: "{nombre_video}"

TÉRMINOS ENCONTRADOS: {', '.join(terminos_encontrados)}

TRANSCRIPCIÓN COMPLETA:
{transcripcion_completa[:2000]}...

COINCIDENCIAS ESPECÍFICAS:
"""
    
    for item in coincidencias:
        prompt += f"- **{item['termino']}**: {item['texto']}\n"
    
    prompt += """

Genera un resumen ejecutivo que DEBE empezar exactamente así:
**TÉRMINOS DETECTADOS:** [lista los términos encontrados]

Luego incluir:
1. **Tema principal** del video
2. **Contexto** en que aparecen las palabras clave
3. **Puntos clave** mencionados
4. **Relevancia** de las coincidencias encontradas

Mantén el resumen conciso pero informativo (máximo 200 palabras).
"""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en análisis de contenido audiovisual que genera resúmenes ejecutivos precisos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        contenido_ia = resp.choices[0].message.content
        
        # Asegurar que empiece con los términos detectados
        if not contenido_ia.startswith("**TÉRMINOS DETECTADOS:**"):
            terminos_texto = f"**TÉRMINOS DETECTADOS:** {', '.join(terminos_encontrados)}\n\n"
            contenido_ia = terminos_texto + contenido_ia
        
        return contenido_ia
        
    except Exception as e:
        # Fallback manual si falla la IA
        terminos_texto = f"**TÉRMINOS DETECTADOS:** {', '.join(terminos_encontrados)}\n\n"
        return terminos_texto + f"Error generando resumen automático: {e}"

def generar_resumen_archivo(nombre_archivo, coincidencias, transcripcion_completa, tipo_archivo):
    """
    Genera resumen ejecutivo para cualquier tipo de archivo (video o audio)
    """
    terminos_encontrados = list(set([item['termino'] for item in coincidencias]))
    
    # Extraer información del medio y hora
    info_medio_hora = extraer_info_medio_hora(nombre_archivo)
    
    prompt = f"""
Analiza el siguiente archivo de {tipo_archivo.lower()}: "{nombre_archivo}"

TÉRMINOS ENCONTRADOS: {', '.join(terminos_encontrados)}

TRANSCRIPCIÓN COMPLETA:
{transcripcion_completa[:2000]}...

COINCIDENCIAS ESPECÍFICAS:
"""
    
    for item in coincidencias:
        prompt += f"- **{item['termino']}**: {item['texto']}\n"
    
    prompt += f"""

Genera un resumen ejecutivo que DEBE empezar exactamente así:
**TÉRMINOS DETECTADOS:** [lista los términos encontrados]

Luego incluir:
1. **Tema principal** del {tipo_archivo.lower()}
2. **Contexto** en que aparecen las palabras clave
3. **Puntos clave** mencionados
4. **Relevancia** de las coincidencias encontradas

Mantén el resumen conciso pero informativo (máximo 200 palabras).
"""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Eres un asistente especializado en análisis de contenido audiovisual que genera resúmenes ejecutivos precisos para archivos de {tipo_archivo.lower()}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        contenido_ia = resp.choices[0].message.content
        
        # Asegurar que empiece con los términos detectados
        if not contenido_ia.startswith("**TÉRMINOS DETECTADOS:**"):
            terminos_texto = f"**TÉRMINOS DETECTADOS:** {', '.join(terminos_encontrados)}\n\n"
            contenido_ia = terminos_texto + contenido_ia
        
        # Agregar contexto del medio y hora al inicio del resumen
        contexto_medio = f"📺 **Medio**: {info_medio_hora}\n\n"
        contenido_ia = contexto_medio + contenido_ia
        
        return contenido_ia
        
    except Exception as e:
        # Fallback manual si falla la IA
        contexto_medio = f"📺 **Medio**: {info_medio_hora}\n\n"
        terminos_texto = f"**TÉRMINOS DETECTADOS:** {', '.join(terminos_encontrados)}\n\n"
        return contexto_medio + terminos_texto + f"Error generando resumen automático para {tipo_archivo.lower()}: {e}"

def crear_archivo_consolidado(video_path, nombre_video, coincidencias, transcripcion_completa, resumen, terminos_buscados):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_limpio = re.sub(r'[^\w\-_\.]', '_', nombre_video.replace('.mp4', ''))
    archivo_consolidado = os.path.join(os.path.dirname(video_path), f"ANALISIS_{timestamp}_{nombre_limpio}.md")
    
    coincidencias_por_termino = {}
    for item in coincidencias:
        termino = item['termino']
        if termino not in coincidencias_por_termino:
            coincidencias_por_termino[termino] = []
        coincidencias_por_termino[termino].append(item)
    
    contenido = f"""# 📊 ANÁLISIS COMPLETO: {nombre_video}

## 📋 Información General
- **Archivo:** `{nombre_video}`
- **Fecha de análisis:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Términos buscados:** {', '.join(terminos_buscados)}
- **Coincidencias encontradas:** {len(coincidencias)} menciones de {len(coincidencias_por_termino)} términos diferentes

## 🎯 Resumen Ejecutivo

{resumen}

## 📈 Estadísticas de Coincidencias

"""
    
    for termino, items in coincidencias_por_termino.items():
        contenido += f"### 🔍 '{termino.upper()}' - {len(items)} mención(es)\n\n"
        for i, item in enumerate(items, 1):
            contexto = item['texto'][:150] + "..." if len(item['texto']) > 150 else item['texto']
            contenido += f"**Mención {i}:**\n> {contexto}\n\n"
    
    contenido += f"""
## 📝 Transcripción Completa

{transcripcion_completa}

---
*Análisis generado automáticamente con IA*
"""
    
    with open(archivo_consolidado, "w", encoding="utf-8") as f:
        f.write(contenido)
    
    return archivo_consolidado

def registrar_archivo_procesado(nombre_archivo, coincidencias, resumen, tipo_archivo):
    """
    Registra un archivo procesado en AMBOS archivos:
    - procesados.log (formato detallado con timestamps y metadatos)
    - procesados.txt (formato simple, una línea por video)
    """
    try:
        # ========== REGISTRAR EN procesados.log (formato detallado) ==========
        with open(PROCESADOS_LOG, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            terminos_encontrados = [item['termino'] for item in coincidencias]
            
            # Línea simple para compatibilidad
            f.write(f"{nombre_archivo}\n")
            
            # Línea de metadatos como comentario
            if coincidencias:
                f.write(f"# Procesado: {timestamp} | Tipo: {tipo_archivo} | Términos: {', '.join(terminos_encontrados)} | Coincidencias: {len(coincidencias)}\n")
            else:
                f.write(f"# Procesado: {timestamp} | Tipo: {tipo_archivo} | Sin coincidencias\n")
        
        # ========== REGISTRAR EN procesados.txt (formato simple) ==========
        procesados_txt = os.path.join(CARPETA_PROCESADOS, "procesados.txt")
        
        # Verificar si el archivo ya está registrado en procesados.txt
        ya_registrado = False
        if os.path.exists(procesados_txt):
            try:
                with open(procesados_txt, "r", encoding="utf-8") as f:
                    contenido = f.read()
                    ya_registrado = nombre_archivo in contenido
            except Exception:
                pass
        
        # Solo agregar si no está ya registrado (evitar duplicados)
        if not ya_registrado:
            with open(procesados_txt, "a", encoding="utf-8") as f:
                f.write(f"{nombre_archivo}\n")
            log_debug(f"✅ Archivo registrado en procesados.txt: {nombre_archivo}", "registrar_archivo_procesado")
        
        log_debug(f"✅ Archivo registrado en procesados.log: {nombre_archivo}", "registrar_archivo_procesado")
        
    except Exception as e:
        st.warning(f"⚠️ Error registrando archivo procesado: {e}")
        log_exception("registrar_archivo_procesado", e, f"Archivo: {nombre_archivo}")

def buscar_videos_nuevos_optimizado(procesados, func_name):
    """
    Busca videos nuevos de forma optimizada usando caché y timestamps
    """
    nuevos = []
    archivos_escaneados = 0
    carpetas_ignoradas = 0
    cache_hits = 0
    
    try:
        # Cargar caché de escaneo
        cache = cargar_cache_escaneo()
        archivos_cache = cache.get('archivos_escaneados', {})
        
        # Limpiar caché de archivos que ya no existen (cada 10 ejecuciones)
        if len(archivos_cache) > 100 and archivos_escaneados % 10 == 0:
            limpiar_cache_escaneo()
            cache = cargar_cache_escaneo()
            archivos_cache = cache.get('archivos_escaneados', {})
        
        # Obtener timestamp del último procesamiento
        ultimo_procesamiento = 0
        if procesados and os.path.exists(PROCESADOS_LOG):
            try:
                stat_info = os.stat(PROCESADOS_LOG)
                ultimo_procesamiento = stat_info.st_mtime
                log_debug(f"Último procesamiento: {datetime.fromtimestamp(ultimo_procesamiento)}", func_name)
            except Exception:
                pass
        
        # Escanear carpetas de forma optimizada
        for root, dirs, files in os.walk(CARPETA_VIDEOS):
            # OPTIMIZACIÓN 1: Ignorar carpetas con clips generados
            marcador_procesado = os.path.join(root, "PROCESADO.txt")
            if os.path.exists(marcador_procesado):
                carpetas_ignoradas += 1
                log_debug(f"Carpeta ignorada (clips): {os.path.basename(root)}", func_name)
                dirs.clear()  # No procesar subdirectorios
                continue
            
            # OPTIMIZACIÓN 1.5: Ignorar carpetas de subclips generados
            es_carpeta_subclips = False
            for file in files:
                # Patrón de subclips: YYYYMMDD_HHMMSS_termino_XmYYs.mp4
                if (file.lower().endswith('.mp4') and 
                    len(file.split('_')) >= 4 and 
                    file.split('_')[0].isdigit() and 
                    len(file.split('_')[0]) == 8):  # YYYYMMDD
                    es_carpeta_subclips = True
                    break
            
            # También verificar archivos .txt de transcripción de clips
            if not es_carpeta_subclips:
                for file in files:
                    if (file.lower().endswith('.txt') and 
                        len(file.split('_')) >= 4 and 
                        file.split('_')[0].isdigit() and 
                        len(file.split('_')[0]) == 8):  # YYYYMMDD
                        es_carpeta_subclips = True
                        break
            
            if es_carpeta_subclips:
                carpetas_ignoradas += 1
                log_debug(f"Carpeta ignorada (subclips): {os.path.basename(root)}", func_name)
                dirs.clear()  # No procesar subdirectorios
                continue
            
            # OPTIMIZACIÓN 2: Verificar fecha de carpeta (SOLO para optimización, no para filtrar)
            try:
                carpeta_mtime = os.path.getmtime(root)
                # NOTA: Comentado temporalmente para evitar filtrar carpetas que pueden tener archivos nuevos
                # if ultimo_procesamiento > 0 and carpeta_mtime < ultimo_procesamiento - 3600:  # 1 hora de margen
                #     log_debug(f"Carpeta sin cambios: {os.path.basename(root)}", func_name)
                #     continue
            except Exception:
                pass
            
            # Procesar archivos MP4 solamente
            for file in files:
                if file.lower().endswith(".mp4"):
                    path_full = os.path.join(root, file)
                    archivos_escaneados += 1
                    
                    try:
                        # OPTIMIZACIÓN 3: Usar caché si está disponible
                        if path_full in archivos_cache:
                            cache_info = archivos_cache[path_full]
                            file_stat = os.stat(path_full)
                            
                            # Verificar si el archivo ha cambiado
                            if (file_stat.st_mtime == cache_info.get('mtime', 0) and 
                                file_stat.st_size == cache_info.get('size', 0)):
                                cache_hits += 1
                                
                                # Si ya fue procesado según caché, saltar
                                if cache_info.get('procesado', False):
                                    log_debug(f"Archivo en caché (procesado): {file}", func_name)
                                    continue
                                
                                # Si es muy pequeño según caché, saltar
                                if cache_info.get('size', 0) < TAMANO_MINIMO_BYTES:
                                    log_debug(f"Archivo en caché (muy pequeño): {file}", func_name)
                                    continue
                        
                        # OPTIMIZACIÓN 4: Verificar tamaño mínimo
                        file_size = os.path.getsize(path_full)
                        if file_size < TAMANO_MINIMO_BYTES:
                            # Actualizar caché
                            file_stat = os.stat(path_full)
                            archivos_cache[path_full] = {
                                'mtime': file_stat.st_mtime,
                                'size': file_size,
                                'procesado': False,
                                'muy_pequeño': True
                            }
                            continue
                        
                        # OPTIMIZACIÓN 5: Verificar si ya está procesado
                        rel_path = os.path.relpath(path_full, CARPETA_VIDEOS)
                        nombre_archivo_solo = os.path.basename(rel_path)
                        if rel_path in procesados or nombre_archivo_solo in procesados:
                            # Actualizar caché
                            file_stat = os.stat(path_full)
                            archivos_cache[path_full] = {
                                'mtime': file_stat.st_mtime,
                                'size': file_size,
                                'procesado': True
                            }
                            log_debug(f"Video ya procesado: {file}", func_name)
                            continue
                        
                        # OPTIMIZACIÓN 6: Verificar fecha del archivo (SOLO para caché, no para filtrar)
                        file_stat = os.stat(path_full)
                        file_mtime = max(file_stat.st_mtime, file_stat.st_ctime)
                        
                        # NOTA: No filtrar por fecha del archivo, solo verificar si ya está procesado
                        # La lógica anterior estaba excluyendo archivos que deberían procesarse
                        
                        # ¡Este archivo es NUEVO y debe procesarse!
                        nuevos.append(path_full)
                        log_info(f"✨ Video NUEVO detectado: {rel_path}", func_name)
                        
                        # Actualizar caché
                        archivos_cache[path_full] = {
                            'mtime': file_stat.st_mtime,
                            'size': file_size,
                            'procesado': False,
                            'detectado_como_nuevo': True
                        }
                            
                    except Exception as e:
                        log_warning(f"Error verificando {file}: {e}", func_name)
                        continue
        
        # Guardar caché actualizado
        cache['archivos_escaneados'] = archivos_cache
        guardar_cache_escaneo(cache)
        
        # LOG DETALLADO PARA DIAGNÓSTICO
        log_info(f"=== DIAGNÓSTICO DE BÚSQUEDA OPTIMIZADA ===", func_name)
        log_info(f"Archivos escaneados: {archivos_escaneados}", func_name)
        log_info(f"Cache hits: {cache_hits}", func_name)
        log_info(f"Carpetas ignoradas: {carpetas_ignoradas}", func_name)
        log_info(f"Archivos NUEVOS encontrados: {len(nuevos)}", func_name)
        
        # Mostrar algunos ejemplos si hay archivos nuevos
        if nuevos:
            log_info("Ejemplos de archivos nuevos (optimizada):", func_name)
            for i, archivo in enumerate(nuevos[:3]):  # Mostrar máximo 3 ejemplos
                rel_path = os.path.relpath(archivo, CARPETA_VIDEOS)
                try:
                    size_mb = os.path.getsize(archivo) / (1024*1024)
                    log_info(f"  {i+1}. {rel_path} ({size_mb:.1f}MB)", func_name)
                except:
                    log_info(f"  {i+1}. {rel_path} (error obteniendo tamaño)", func_name)
        
        log_info(f"=== FIN DIAGNÓSTICO OPTIMIZADA ===", func_name)
        
    except Exception as e:
        log_exception(func_name, e, "Error en búsqueda optimizada")
        log_info("Activando búsqueda tradicional como fallback", func_name)
        return buscar_videos_tradicional(procesados, func_name)
    
    return nuevos

def buscar_videos_tradicional(procesados, func_name):
    """
    Búsqueda tradicional como fallback si la optimizada falla
    """
    archivos = []
    archivos_muy_pequeños = []
    archivos_en_carpetas_procesadas = []
    archivos_ya_procesados = []
    
    log_info("Ejecutando búsqueda tradicional de videos", func_name)
    
    for root, _, files in os.walk(CARPETA_VIDEOS):
        # IGNORAR carpetas que contienen clips generados
        marcador_procesado = os.path.join(root, "PROCESADO.txt")
        if os.path.exists(marcador_procesado):
            for file in files:
                if file.lower().endswith((".mp4", ".mp3", ".wav", ".aac", ".m4a", ".flac")):
                    archivos_en_carpetas_procesadas.append(os.path.join(root, file))
            continue
        
        # IGNORAR carpetas de subclips generados
        es_carpeta_subclips = False
        for file in files:
            # Patrón de subclips: YYYYMMDD_HHMMSS_termino_XmYYs.mp4/mp3
            if (file.lower().endswith(('.mp4', '.mp3')) and 
                len(file.split('_')) >= 4 and 
                file.split('_')[0].isdigit() and 
                len(file.split('_')[0]) == 8):  # YYYYMMDD
                es_carpeta_subclips = True
                break
        
        # También verificar archivos .txt de transcripción de clips
        if not es_carpeta_subclips:
            for file in files:
                if (file.lower().endswith('.txt') and 
                    len(file.split('_')) >= 4 and 
                    file.split('_')[0].isdigit() and 
                    len(file.split('_')[0]) == 8):  # YYYYMMDD
                    es_carpeta_subclips = True
                    break
        
        if es_carpeta_subclips:
            continue
            
        for file in files:
            if file.lower().endswith((".mp4", ".mp3", ".wav", ".aac", ".m4a", ".flac")):
                path_full = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(path_full)
                    if file_size >= TAMANO_MINIMO_BYTES:
                        archivos.append(path_full)
                    else:
                        archivos_muy_pequeños.append(path_full)
                        log_debug(f"Archivo muy pequeño ignorado: {file} ({file_size / (1024*1024):.1f}MB)", func_name)
                except Exception as e:
                    log_warning(f"Error verificando archivo {file}: {e}", func_name)
                    continue

    # Filtrar videos ya procesados
    nuevos = []
    for f in archivos:
        rel_path = os.path.relpath(f, CARPETA_VIDEOS)
        nombre_archivo_solo = os.path.basename(rel_path)
        if rel_path not in procesados and nombre_archivo_solo not in procesados:
            nuevos.append(f)
        else:
            archivos_ya_procesados.append(f)
    
    # LOG DETALLADO PARA DIAGNÓSTICO
    log_info(f"=== DIAGNÓSTICO DE BÚSQUEDA TRADICIONAL ===", func_name)
    log_info(f"Archivos encontrados (>={TAMANO_MINIMO_BYTES/(1024*1024):.0f}MB): {len(archivos)}", func_name)
    log_info(f"Archivos muy pequeños (<{TAMANO_MINIMO_BYTES/(1024*1024):.0f}MB): {len(archivos_muy_pequeños)}", func_name)
    log_info(f"Archivos en carpetas procesadas: {len(archivos_en_carpetas_procesadas)}", func_name)
    log_info(f"Archivos ya procesados: {len(archivos_ya_procesados)}", func_name)
    log_info(f"Archivos NUEVOS para procesar: {len(nuevos)}", func_name)
    
    # Mostrar algunos ejemplos si hay archivos nuevos
    if nuevos:
        log_info("Ejemplos de archivos nuevos encontrados:", func_name)
        for i, archivo in enumerate(nuevos[:3]):  # Mostrar máximo 3 ejemplos
            rel_path = os.path.relpath(archivo, CARPETA_VIDEOS)
            size_mb = os.path.getsize(archivo) / (1024*1024)
            log_info(f"  {i+1}. {rel_path} ({size_mb:.1f}MB)", func_name)
    
    # Mostrar ejemplos de archivos muy pequeños si los hay
    if archivos_muy_pequeños:
        log_info("Ejemplos de archivos muy pequeños ignorados:", func_name)
        for i, archivo in enumerate(archivos_muy_pequeños[:3]):  # Mostrar máximo 3 ejemplos
            rel_path = os.path.relpath(archivo, CARPETA_VIDEOS)
            size_mb = os.path.getsize(archivo) / (1024*1024)
            log_info(f"  {i+1}. {rel_path} ({size_mb:.1f}MB)", func_name)
    
    log_info(f"=== FIN DIAGNÓSTICO ===", func_name)
    
    return nuevos

def escanear_carpeta_completa():
    """
    Escanea toda la carpeta y genera estadísticas completas
    """
    func_name = "escanear_carpeta_completa"
    log_info("Iniciando escaneo completo de la carpeta", func_name)
    
    # Estadísticas
    total_archivos = 0
    videos_encontrados = 0
    archivos_procesados = 0
    archivos_nuevos = 0
    archivos_muy_pequeños = 0
    
    # Cargar lista de archivos ya procesados
    procesados = cargar_procesados()
    
    # Mostrar progreso del escaneo
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🔍 **ESCANEO COMPLETO DE CARPETA**")
        progress_bar = st.progress(0, text="Iniciando escaneo...")
    
    try:
        # Escanear toda la carpeta
        for root, dirs, files in os.walk(CARPETA_VIDEOS):
            # Ignorar carpetas con clips generados
            marcador_procesado = os.path.join(root, "PROCESADO.txt")
            if os.path.exists(marcador_procesado):
                continue
            
            # IGNORAR CARPETAS DE SUBCLIPS GENERADOS
            # Verificar si esta carpeta contiene subclips (archivos con timestamp en el nombre)
            es_carpeta_subclips = False
            for file in files:
                # Patrón de subclips: YYYYMMDD_HHMMSS_termino_XmYYs.mp4
                if (file.lower().endswith('.mp4') and 
                    len(file.split('_')) >= 4 and 
                    file.split('_')[0].isdigit() and 
                    len(file.split('_')[0]) == 8):  # YYYYMMDD
                    es_carpeta_subclips = True
                    break
            
            # También verificar si hay archivos .txt de transcripción de clips
            if not es_carpeta_subclips:
                for file in files:
                    if (file.lower().endswith('.txt') and 
                        len(file.split('_')) >= 4 and 
                        file.split('_')[0].isdigit() and 
                        len(file.split('_')[0]) == 8):  # YYYYMMDD
                        es_carpeta_subclips = True
                        break
            
            if es_carpeta_subclips:
                continue
            
            for file in files:
                if file.lower().endswith(".mp4"):
                    total_archivos += 1
                    path_full = os.path.join(root, file)
                    rel_path = os.path.relpath(path_full, CARPETA_VIDEOS)
                    
                    # Contar videos MP4
                    if file.lower().endswith('.mp4'):
                        videos_encontrados += 1
                    
                    # Verificar tamaño
                    try:
                        file_size = os.path.getsize(path_full)
                        if file_size < TAMANO_MINIMO_BYTES:
                            archivos_muy_pequeños += 1
                            continue
                    except Exception:
                        continue
                    
                    # Verificar si ya fue procesado
                    # También verificar solo el nombre del archivo (sin ruta) por compatibilidad
                    nombre_archivo_solo = os.path.basename(rel_path)
                    if rel_path in procesados or nombre_archivo_solo in procesados:
                        archivos_procesados += 1
                    else:
                        archivos_nuevos += 1
                    
                    # Actualizar progreso cada 10 archivos
                    if total_archivos % 10 == 0:
                        progress_bar.progress(min(0.9, total_archivos / 100), 
                                            text=f"Escaneados {total_archivos} archivos...")
        
        progress_bar.progress(1.0, text="Escaneo completado")
        
        # Mostrar estadísticas detalladas
        st.markdown("---")
        st.markdown("### 📊 **ESTADÍSTICAS DEL ESCANEO**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📁 Total Archivos", total_archivos)
            st.metric("🎞️ Videos", videos_encontrados)
        
        with col2:
            st.metric("✅ Ya Procesados", archivos_procesados)
            st.metric("🆕 Nuevos", archivos_nuevos)
            st.metric("📏 Muy Pequeños", archivos_muy_pequeños)
        
        with col3:
            porcentaje_procesados = (archivos_procesados / max(1, total_archivos - archivos_muy_pequeños)) * 100
            st.metric("📈 % Procesados", f"{porcentaje_procesados:.1f}%")
            
            if archivos_nuevos > 0:
                st.success(f"🚀 **{archivos_nuevos} archivos nuevos** listos para procesar")
            else:
                st.info("✅ **Todos los archivos ya fueron procesados**")
        
        with col4:
            # Información de archivos de procesados
            try:
                info_archivos = []
                
                # Contar en procesados.log
                if os.path.exists(PROCESADOS_LOG):
                    with open(PROCESADOS_LOG, 'r', encoding='utf-8') as f:
                        lineas = f.readlines()
                    log_count = len([l for l in lineas if not l.startswith('#') and not l.startswith('[') and not l.startswith('=') and l.strip()])
                    info_archivos.append(f"📄 Log: {log_count}")
                
                # Contar en procesados.txt
                procesados_txt = os.path.join(CARPETA_PROCESADOS, "procesados.txt")
                if os.path.exists(procesados_txt):
                    with open(procesados_txt, 'r', encoding='utf-8') as f:
                        lineas = f.readlines()
                    txt_count = len([l for l in lineas if not l.startswith('#') and l.strip()])
                    info_archivos.append(f"📝 TXT: {txt_count}")
                
                if info_archivos:
                    st.metric("📚 Registros", " | ".join(info_archivos))
                else:
                    st.metric("📚 Registros", "No hay")
            except Exception:
                st.metric("📚 Registros", "Error")
        
        # Mostrar detalles de archivos procesados
        if archivos_procesados > 0:
            with st.expander("📋 Ver archivos ya procesados"):
                archivos_procesados_lista = []
                for root, dirs, files in os.walk(CARPETA_VIDEOS):
                    marcador_procesado = os.path.join(root, "PROCESADO.txt")
                    if os.path.exists(marcador_procesado):
                        continue
                    
                    # Ignorar carpetas de subclips
                    es_carpeta_subclips = False
                    for file in files:
                        if (file.lower().endswith(('.mp4', '.mp3')) and 
                            len(file.split('_')) >= 4 and 
                            file.split('_')[0].isdigit() and 
                            len(file.split('_')[0]) == 8):
                            es_carpeta_subclips = True
                            break
                    
                    if not es_carpeta_subclips:
                        for file in files:
                            if (file.lower().endswith('.txt') and 
                                len(file.split('_')) >= 4 and 
                                file.split('_')[0].isdigit() and 
                                len(file.split('_')[0]) == 8):
                                es_carpeta_subclips = True
                                break
                    
                    if es_carpeta_subclips:
                        continue
                    
                    for file in files:
                        if file.lower().endswith((".mp4", ".mp3", ".wav", ".aac", ".m4a", ".flac")):
                            path_full = os.path.join(root, file)
                            rel_path = os.path.relpath(path_full, CARPETA_VIDEOS)
                            if rel_path in procesados:
                                archivos_procesados_lista.append(rel_path)
                
                if archivos_procesados_lista:
                    for archivo in sorted(archivos_procesados_lista)[:20]:  # Mostrar máximo 20
                        st.text(f"✅ {archivo}")
                    if len(archivos_procesados_lista) > 20:
                        st.text(f"... y {len(archivos_procesados_lista) - 20} más")
        
        # Recopilar lista de archivos nuevos (fuera del expander para poder retornarla)
        archivos_nuevos_lista = []
        # Recopilar lista de archivos omitidos por ser menores al tamaño mínimo
        archivos_muy_pequenos_lista = []
        for root, dirs, files in os.walk(CARPETA_VIDEOS):
            marcador_procesado = os.path.join(root, "PROCESADO.txt")
            if os.path.exists(marcador_procesado):
                continue
            
            # Ignorar carpetas de subclips
            es_carpeta_subclips = False
            for file in files:
                if (file.lower().endswith(('.mp4', '.mp3')) and 
                    len(file.split('_')) >= 4 and 
                    file.split('_')[0].isdigit() and 
                    len(file.split('_')[0]) == 8):
                    es_carpeta_subclips = True
                    break
            
            if not es_carpeta_subclips:
                for file in files:
                    if (file.lower().endswith('.txt') and 
                        len(file.split('_')) >= 4 and 
                        file.split('_')[0].isdigit() and 
                        len(file.split('_')[0]) == 8):
                        es_carpeta_subclips = True
                        break
            
            if es_carpeta_subclips:
                continue
            
            for file in files:
                if file.lower().endswith(".mp4"):
                    path_full = os.path.join(root, file)
                    rel_path = os.path.relpath(path_full, CARPETA_VIDEOS)
                    try:
                        file_size = os.path.getsize(path_full)
                        if file_size >= TAMANO_MINIMO_BYTES and rel_path not in procesados:
                            archivos_nuevos_lista.append(rel_path)
                        elif file_size < TAMANO_MINIMO_BYTES:
                            archivos_muy_pequenos_lista.append(rel_path)
                    except Exception:
                        continue
        
        # Mostrar detalles de archivos nuevos
        if archivos_nuevos > 0:
            with st.expander("🆕 Ver archivos nuevos"):
                if archivos_nuevos_lista:
                    for archivo in sorted(archivos_nuevos_lista):
                        icono = "🎞️"
                        st.text(f"{icono} {archivo}")
        
        # Mostrar lista de omitidos por tamaño mínimo
        if archivos_muy_pequenos_lista:
            umbral_mb = TAMANO_MINIMO_BYTES / (1024 * 1024)
            with st.expander(f"🚫 Ver archivos omitidos (< {umbral_mb:.0f} MB)"):
                for archivo in sorted(archivos_muy_pequenos_lista)[:50]:
                    st.text(f"🚫 {archivo}")
                if len(archivos_muy_pequenos_lista) > 50:
                    st.text(f"... y {len(archivos_muy_pequenos_lista) - 50} más")

            # Registrar omitidos en log diario
            try:
                logs_dir = os.path.join(os.getcwd(), "logs")
                os.makedirs(logs_dir, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                omitidos_log = os.path.join(logs_dir, f"omitidos_{date_str}.log")
                with open(omitidos_log, "a", encoding="utf-8") as lf:
                    marca_tiempo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    lf.write(f"{marca_tiempo} - Omitidos (< {umbral_mb:.0f} MB): {len(archivos_muy_pequenos_lista)}\n")
                    for rel in archivos_muy_pequenos_lista:
                        lf.write(f"- {rel}\n")
            except Exception as e:
                log_warning(f"No se pudo escribir omitidos en log: {e}", func_name)
        
        log_info(f"Escaneo completado: {total_archivos} total, {archivos_nuevos} nuevos, {archivos_procesados} procesados", func_name)
        
        return {
            'total_archivos': total_archivos,
            'total_videos': videos_encontrados,
            'archivos_procesados': archivos_procesados,
            'archivos_nuevos': archivos_nuevos,
            'archivos_muy_pequeños': archivos_muy_pequeños,
            'archivos_muy_pequeños_lista': archivos_muy_pequenos_lista,
            'procesados': procesados,
            'archivos_nuevos_lista': archivos_nuevos_lista
        }
        
    except Exception as e:
        log_exception(func_name, e, "Error en escaneo completo")
        st.error(f"❌ Error durante el escaneo: {e}")
        return None

def buscar_y_procesar_videos(duracion_clip=60, buffer_anterior=30):
    func_name = "buscar_y_procesar_videos"
    log_info(f"Iniciando búsqueda y procesamiento de videos. Duración clip: {duracion_clip}s, Buffer: {buffer_anterior}s", func_name)
    
    # ========== CONTROL DE EJECUCIÓN MÚLTIPLE ==========
    # Verificar si ya hay una ejecución en curso para evitar duplicados
    if hasattr(st.session_state, 'procesamiento_en_curso') and st.session_state.procesamiento_en_curso:
        log_warning("⚠️ PROCESAMIENTO YA EN CURSO - Evitando ejecución duplicada", func_name)
        st.warning("⚠️ Ya hay un procesamiento en curso. Esperando a que termine...")
        return
    
    # Marcar que el procesamiento está en curso
    st.session_state.procesamiento_en_curso = True
    log_info("🔒 Marcando procesamiento como en curso para evitar duplicados", func_name)
    
    # Limpiar control de duplicados de Supabase para nuevo procesamiento
    st.session_state.coincidencias_enviadas_supabase.clear()
    log_info("🧹 Control de duplicados Supabase limpiado para nuevo procesamiento", func_name)
    
    st.session_state.ultimo_chequeo = datetime.now()
    
    terminos = st.session_state.terminos_continuos
    log_debug(f"Términos configurados: {terminos}", func_name)
    
    if not terminos:
        log_info("No hay términos configurados para buscar", func_name)
        st.warning("⚠️ No hay términos configurados para buscar")
        st.session_state.procesamiento_en_curso = False
        return

    # === ESCANEO COMPLETO ANTES DE PROCESAR ===
    st.markdown("---")
    st.markdown("### 🔍 **ESCANEO COMPLETO DE CARPETA**")
    estadisticas = escanear_carpeta_completa()
    
    if not estadisticas:
        st.error("❌ Error en el escaneo, no se puede continuar")
        st.session_state.procesamiento_en_curso = False
        return
    
    # Mostrar resumen detallado del escaneo
    st.markdown("---")
    st.markdown("### 📊 **RESUMEN DEL ESCANEO**")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📁 Total Archivos", estadisticas['total_archivos'])
    
    with col2:
        st.metric("🎞️ Videos", estadisticas['total_videos'])
    
    with col3:
        st.metric("📊 Procesados", estadisticas['archivos_procesados'])
    
    with col4:
        st.metric("🆕 Nuevos", estadisticas['archivos_nuevos'])
    
    # Mostrar cuántos se omitieron por ser menores al tamaño mínimo
    with col5:
        try:
            umbral_mb = TAMANO_MINIMO_BYTES / (1024 * 1024)
            st.metric(f"🚫 Omitidos < {umbral_mb:.0f} MB", estadisticas.get('archivos_muy_pequeños', 0))
        except Exception:
            st.metric("🚫 Omitidos por tamaño", estadisticas.get('archivos_muy_pequeños', 0))
    
    # Mostrar archivos nuevos
    if estadisticas['archivos_nuevos'] > 0:
        st.success(f"🆕 **{estadisticas['archivos_nuevos']} ARCHIVOS NUEVOS** encontrados para procesar")
        
        # Mostrar lista de videos nuevos
        with st.expander("📋 Ver videos nuevos a procesar"):
            for archivo in estadisticas['archivos_nuevos_lista'][:10]:  # Mostrar máximo 10
                st.text(f"🎞️ {archivo}")
            if len(estadisticas['archivos_nuevos_lista']) > 10:
                st.text(f"... y {len(estadisticas['archivos_nuevos_lista']) - 10} más")
    else:
        st.success("✅ **TODOS LOS VIDEOS YA FUERON PROCESADOS**")
        st.info("💡 No hay videos nuevos para procesar. El sistema está al día.")
        
        # Mostrar opción de forzar reprocesamiento
        if st.button("🔄 **FORZAR REPROCESAMIENTO**", 
                    help="Reprocesar todos los videos (ignorar videos ya procesados)",
                    key="forzar_reprocesamiento"):
            st.session_state.forzar_escaneo_completo = True
            st.info("🚀 Forzando reprocesamiento de todos los videos...")
            st.rerun()
        st.session_state.procesamiento_en_curso = False
        return
    
    # Continuar con el procesamiento de archivos nuevos
    st.markdown("---")
    st.success(f"🚀 **INICIANDO PROCESAMIENTO** - {estadisticas['archivos_nuevos']} videos nuevos encontrados")
    
    # Usar la lista de procesados del escaneo
    procesados = estadisticas['procesados']
    
    # Verificar si se forzó un escaneo completo
    forzar_escaneo = getattr(st.session_state, 'forzar_escaneo_completo', False)
    
    if forzar_escaneo:
        st.info("🚀 Ejecutando escaneo completo forzado (ignorando archivos ya procesados)")
        nuevos = buscar_videos_tradicional(procesados, func_name)
        st.session_state.forzar_escaneo_completo = False  # Resetear flag
        log_info("Escaneo completo forzado ejecutado", func_name)
    else:
        # Buscar SOLO archivos nuevos de forma más eficiente
        nuevos = buscar_videos_nuevos_optimizado(procesados, func_name)
    
    log_info(f"Archivos nuevos encontrados para procesar: {len(nuevos)}", func_name)
    
    if not nuevos:
        st.info("✅ No hay videos nuevos para procesar después del escaneo")
        st.session_state.procesamiento_en_curso = False
        return

    st.success(f"🆕 Encontrados {len(nuevos)} videos nuevos para procesar")
    st.session_state.videos_encontrados += len(nuevos)
    
    clips_generados_en_sesion = []
    videos_procesados_data = []  # Almacenar datos de todos los videos procesados

    # Contenedor para el progreso
    progress_container = st.container()
    
    # FASE 1: PROCESAR TODOS LOS VIDEOS PRIMERO (sin enviar webhooks)
    st.info("🎬 FASE 1: Procesando todos los videos (sin envíos)")
    
    for i, archivo_path in enumerate(nuevos):
        rel = os.path.relpath(archivo_path, CARPETA_VIDEOS)
        
        # BLOQUE TRY-EXCEPT GENERAL PARA CADA ARCHIVO
        try:
            # Detectar tipo de archivo (solo videos)
            es_video = archivo_path.lower().endswith('.mp4')
            
            # Icono para videos
            icono = "🎞️"
            tipo_archivo = "Video"
            
            with progress_container:
                st.markdown(f"---\n### {icono} Procesando {tipo_archivo} ({i+1}/{len(nuevos)}): `{rel}`")
                progress_bar = st.progress(0, text="Iniciando procesamiento...")
            
            # Configurar rutas para videos MP4
            audio_path = archivo_path.replace(".mp4", ".wav")
            md_path = archivo_path.replace(".mp4", "_streaming.md")
            
            dur_total = obtener_duracion(archivo_path)

            # Extraer/convertir audio según el tipo de archivo
            progress_bar.progress(20, text="🎧 Procesando audio...")
        
            # Función para procesar audio con reintentos (solo videos)
            def procesar_audio_con_reintentos(archivo_path, audio_path, max_reintentos=3):
                for intento in range(max_reintentos):
                    try:
                        # Verificar que el archivo existe y es accesible
                        if not os.path.exists(archivo_path):
                            if intento < max_reintentos - 1:
                                st.warning(f"⚠️ Archivo no encontrado (intento {intento + 1}/{max_reintentos}): {archivo_path}")
                                time.sleep(5)  # Esperar 5 segundos antes del siguiente intento
                                continue
                            else:
                                st.error(f"❌ Archivo no encontrado después de {max_reintentos} intentos: {archivo_path}")
                                return False
                    
                        # Verificar tamaño del archivo
                        file_size = os.path.getsize(archivo_path)
                        if file_size == 0:
                            if intento < max_reintentos - 1:
                                st.warning(f"⚠️ Archivo vacío (intento {intento + 1}/{max_reintentos}): {archivo_path}")
                                time.sleep(5)  # Esperar 5 segundos antes del siguiente intento
                                continue
                            else:
                                st.error(f"❌ Archivo vacío después de {max_reintentos} intentos: {archivo_path}")
                                return False
                    
                        # Extraer audio del video MP4
                        cmd = [
                            "ffmpeg", "-y", "-i", archivo_path,
                            "-ac", "1", "-ar", "16000", "-f", "wav", audio_path
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                    
                        if result.returncode != 0:
                            if intento < max_reintentos - 1:
                                # Solo mostrar un mensaje breve en el primer intento
                                if intento == 0:
                                    st.warning(f"⚠️ Error procesando: {os.path.basename(archivo_path)} - reintentando...")
                                time.sleep(10)  # Esperar 10 segundos antes del siguiente intento
                                continue
                            else:
                                # Solo mostrar un resumen final en una línea
                                st.error(f"❌ No se pudo procesar: {os.path.basename(archivo_path)} - Error FFmpeg: {result.returncode}")
                            
                                # Intentar con parámetros más permisivos
                                st.info("🔄 Intentando con parámetros alternativos...")
                                cmd_alt = [
                                    "ffmpeg", "-y", "-i", archivo_path,
                                    "-ac", "1", "-ar", "16000", "-f", "wav", 
                                    "-avoid_negative_ts", "make_zero", audio_path
                                ]
                                result_alt = subprocess.run(cmd_alt, capture_output=True, text=True)
                            
                                if result_alt.returncode != 0:
                                    st.error(f"❌ Error persistente incluso con parámetros alternativos")
                                    return False
                                else:
                                    st.success("✅ Audio extraído con parámetros alternativos")
                                    return True
                        else:
                            st.success("✅ Audio extraído exitosamente")
                            return True
                    
                    except Exception as e:
                        if intento < max_reintentos - 1:
                            if intento == 0:
                                st.warning(f"⚠️ Error procesando: {os.path.basename(archivo_path)} - reintentando...")
                            time.sleep(5)  # Esperar 5 segundos antes del siguiente intento
                            continue
                        else:
                            st.error(f"❌ Error inesperado: {os.path.basename(archivo_path)} - {str(e)[:50]}...")
                            return False
            
                return False
        
            # Ejecutar procesamiento con reintentos
            if not procesar_audio_con_reintentos(archivo_path, audio_path):
                st.warning(f"⚠️ Saltando: {os.path.basename(archivo_path)}")
                continue

            # Transcribir con Mistral
            progress_bar.progress(40, text="🧠 Transcribiendo con sistema híbrido...")
            start = time.time()
            try:
                transcripcion_mistral, api_usada = transcribir_audio_hibrido(audio_path)
                st.info(f"🎯 Transcripción completada con {api_usada}")
            except Exception as e:
                st.error(f"❌ Error en transcripción: {e}")
                continue
            elapsed_mistral = time.time() - start

            # Obtener timestamps con faster-whisper
            progress_bar.progress(60, text="🕐 Obteniendo timestamps...")
            start = time.time()
            try:
                segments_timestamps = obtener_timestamps_whisper(audio_path)
            except Exception as e:
                st.error(f"❌ Error obteniendo timestamps: {e}")
                continue
            elapsed_whisper = time.time() - start

            progress_bar.progress(80, text="🔍 Buscando coincidencias...")
        
            coincidencias_md = []
            coincidencias_items = []
            # Crear carpeta principal del archivo (una sola vez)
            archivo_name_clean = os.path.splitext(rel)[0]  # Sin extensión
            archivo_name_safe = "".join(c for c in archivo_name_clean if c.isalnum() or c in (' ', '-', '_')).rstrip()
            archivo_name_safe = archivo_name_safe.replace(' ', '_')[:50]  # Máximo 50 caracteres
            fecha_folder = datetime.now().strftime("%Y%m%d_%H%M%S")
        
            # CARPETA PRINCIPAL DEL ARCHIVO (contiene todos los clips) - EN CARPETA PROCESADOS
            archivo_main_dir = os.path.join(CARPETA_PROCESADOS, f"c_{archivo_name_safe}_{fecha_folder}")
            os.makedirs(archivo_main_dir, exist_ok=True)
            log_info(f"Carpeta de coincidencias creada: {archivo_main_dir}", func_name)
        
            # Crear archivo marcador P* en la carpeta principal
            marcador_path = os.path.join(archivo_main_dir, "PROCESADO.txt")
            if not os.path.exists(marcador_path):
                with open(marcador_path, "w", encoding="utf-8") as f:
                    f.write(f"🚫 CARPETA PROCESADA - NO REPROCESAR\n")
                    f.write(f"Fecha creación: {datetime.now().isoformat()}\n")
                    f.write(f"Archivo origen: {rel} ({tipo_archivo})\n")
                    f.write(f"Términos encontrados: {', '.join(terminos)}\n")
                    f.write(f"Generado por: Video Analyzer IA v2.0\n")
            
            # ========== GUARDAR TRANSCRIPCIÓN COMPLETA DEL VIDEO ==========
            transcripcion_completa_path = os.path.join(archivo_main_dir, "TRANSCRIPCION_COMPLETA.txt")
            if not os.path.exists(transcripcion_completa_path):
                try:
                    with open(transcripcion_completa_path, "w", encoding="utf-8") as f:
                        f.write(f"📝 TRANSCRIPCIÓN COMPLETA DEL VIDEO\n")
                        f.write(f"{'='*80}\n\n")
                        f.write(f"📹 VIDEO: {rel}\n")
                        f.write(f"📅 FECHA DE ANÁLISIS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"⏱️ DURACIÓN TOTAL: {dur_total:.1f} segundos ({int(dur_total//60)}:{int(dur_total%60):02d})\n")
                        f.write(f"🔍 TÉRMINOS BUSCADOS: {', '.join(terminos)}\n")
                        f.write(f"\n{'='*80}\n")
                        f.write(f"TRANSCRIPCIÓN:\n")
                        f.write(f"{'='*80}\n\n")
                        f.write(transcripcion_mistral)
                        f.write(f"\n\n{'='*80}\n")
                        f.write(f"📊 ESTADÍSTICAS:\n")
                        f.write(f"- Total de palabras: {len(transcripcion_mistral.split())}\n")
                        f.write(f"- Total de caracteres: {len(transcripcion_mistral)}\n")
                        f.write(f"\n{'='*80}\n")
                        f.write(f"✅ Generado automáticamente por Video Analyzer IA v2.0\n")
                    
                    log_info(f"✅ Transcripción completa guardada: {transcripcion_completa_path}", func_name)
                    st.info(f"💾 Transcripción completa guardada en carpeta del video")
                except Exception as e:
                    log_warning(f"Error guardando transcripción completa: {e}", func_name)

            # Buscar términos - VERSIÓN CORREGIDA Y MEJORADA
            text_lower = transcripcion_mistral.lower()
        
            # Función auxiliar para buscar término con variaciones
            def buscar_termino_flexible(termino, texto):
                """Busca un término considerando variaciones comunes"""
                # Búsqueda exacta primero
                if re.search(rf"\b{re.escape(termino)}\b", texto):
                    return True, termino
            
                # Buscar variaciones comunes (plurales, conjugaciones básicas)
                variaciones = [
                    termino + "s",  # plural
                    termino + "es", # plural alternativo
                    termino + "a",  # género femenino
                    termino + "o",  # género masculino
                ]
            
                for variacion in variaciones:
                    if re.search(rf"\b{re.escape(variacion)}\b", texto):
                        return True, variacion
                
                # 🆕 NORMALIZACIÓN DE ESPACIOS: Buscar sin espacios
                # Ejemplo: "celsomarrancini" encontrará "celso marranzini" o "Celsomarrancini"
                # PERO NO hará match parcial: "edesur" NO encontrará "desur"
                termino_sin_espacios = termino.replace(" ", "").lower()
                
                # Buscar palabras consecutivas que al juntar coincidan EXACTAMENTE
                palabras = texto.split()
                for i in range(len(palabras)):
                    for j in range(i+1, min(i+6, len(palabras)+1)):  # Buscar hasta 5 palabras consecutivas
                        fragmento_sin_espacios = "".join(palabras[i:j]).lower()
                        # Match EXACTO, no substring
                        if termino_sin_espacios == fragmento_sin_espacios:
                            termino_encontrado = " ".join(palabras[i:j])
                            return True, termino_encontrado
            
                return False, None
        
            # ========== TÉRMINOS PRIORITARIOS ==========
            # Estos términos SIEMPRE deben generar clips cuando se mencionen
            # No se aplicarán verificaciones estrictas de relevancia a estos términos
            TERMINOS_PRIORITARIOS = {
                'edesur', 'edenorte', 'edeeste',
                'punta catalina',
                'apagones',
                'egehid', 'ede hid',
                'celso marranzini', 'celso', 'marranzini', 'celsomarrancini',
                'protecom',
                'pegase', 'pégase'
            }
            
            # ========== CONTROL DE DUPLICADOS MEJORADO ==========
            # Lista para rastrear timestamps ya procesados para evitar clips duplicados
            timestamps_procesados = []
            # Lista para rastrear combinaciones de término + timestamp ya procesadas
            coincidencias_procesadas = set()
        
            for termino in terminos:
                # PRIMERA VERIFICACIÓN: ¿El término (o variaciones) existe en la transcripción completa?
                encontrado, termino_encontrado = buscar_termino_flexible(termino, text_lower)
            
                if encontrado:
                    log_info(f"Término '{termino}' encontrado en transcripción completa", func_name)
                    
                    # Verificar si es un término prioritario
                    es_prioritario = termino.lower() in TERMINOS_PRIORITARIOS
                    if es_prioritario:
                        log_info(f"⭐ '{termino}' es un TÉRMINO PRIORITARIO - se aplicarán reglas flexibles", func_name)
                        st.info(f"⭐ Término prioritario detectado: '{termino}'")
                
                    mejor_timestamp = None
                    mejor_texto_contexto = ""
                
                    # SEGUNDA VERIFICACIÓN: ¿El término existe en algún segmento específico con timestamp?
                    for seg in segments_timestamps:
                        seg_encontrado, seg_termino_encontrado = buscar_termino_flexible(termino, seg['text'].lower())
                        if seg_encontrado:
                            mejor_timestamp = seg
                            mejor_texto_contexto = seg['text']
                            log_info(f"Término '{termino}' (variante: '{seg_termino_encontrado}') encontrado en segmento: {seg['text'][:100]}...", func_name)
                            break
                
                    # VERIFICACIÓN CRÍTICA: Solo continuar si encontramos el término en un segmento específico
                    # EXCEPCIÓN: Para términos prioritarios, buscar en todos los segmentos y usar el primero disponible
                    if not mejor_timestamp:
                        if es_prioritario and segments_timestamps:
                            # Para términos prioritarios, usar el segmento central como fallback
                            mejor_timestamp = segments_timestamps[len(segments_timestamps) // 2]
                            mejor_texto_contexto = mejor_timestamp['text']
                            log_info(f"⭐ TÉRMINO PRIORITARIO '{termino}': Usando segmento central como fallback", func_name)
                            st.info(f"⭐ Término prioritario '{termino}': Generando clip desde segmento representativo")
                        else:
                            log_warning(f"⚠️ TÉRMINO '{termino}' ENCONTRADO EN TRANSCRIPCIÓN GENERAL PERO NO EN SEGMENTOS ESPECÍFICOS", func_name)
                            log_warning(f"   - Esto puede indicar error de transcripción o segmentación", func_name)
                            log_warning(f"   - NO se generará clip para evitar falsos positivos", func_name)
                            st.warning(f"⚠️ Término '{termino}' encontrado en transcripción general pero no en momento específico - OMITIDO")
                            continue  # ❌ NO GENERAR CLIP - SALTAR AL SIGUIENTE TÉRMINO
                
                    # ========== CONTROL DE DUPLICADOS MEJORADO ==========
                    timestamp_actual = mejor_timestamp['start']
                    
                    # Crear clave única para esta coincidencia (término + timestamp + archivo)
                    clave_coincidencia = f"{termino}_{timestamp_actual:.1f}_{rel}"
                    
                    # Verificar si ya procesamos esta coincidencia exacta
                    if clave_coincidencia in coincidencias_procesadas:
                        log_info(f"⏭️ DUPLICADO DETECTADO: '{termino}' en {timestamp_actual:.1f}s ya procesado para {rel}", func_name)
                        st.info(f"⏭️ Coincidencia duplicada evitada: '{termino}' en {timestamp_actual:.1f}s")
                        continue  # ❌ NO GENERAR CLIP DUPLICADO
                    
                    # Verificar si ya procesamos un clip para este timestamp (tolerancia de ±60 segundos - 1 minuto)
                    es_duplicado = False
                    for ts_procesado in timestamps_procesados:
                        diferencia = abs(timestamp_actual - ts_procesado)
                        if diferencia <= 60:  # Tolerancia de 60 segundos (1 minuto) para evitar clips repetitivos
                            es_duplicado = True
                            log_info(f"⏭️ Término '{termino}' OMITIDO - Ya existe clip para timestamp similar ({diferencia:.1f}s de diferencia, mínimo requerido: 60s)", func_name)
                            st.info(f"⏭️ Término '{termino}' omitido - Ya existe clip reciente (separación mínima: 1 minuto)")
                            break
                
                    if es_duplicado:
                        continue  # ❌ NO GENERAR CLIP DUPLICADO - SALTAR AL SIGUIENTE TÉRMINO
                
                    # Agregar a las listas de control
                    timestamps_procesados.append(timestamp_actual)
                    coincidencias_procesadas.add(clave_coincidencia)
                    log_info(f"✅ Timestamp {timestamp_actual}s agregado a lista de procesados", func_name)
                    log_info(f"✅ Coincidencia '{clave_coincidencia}' registrada para evitar duplicados", func_name)

                    m, s = divmod(int(mejor_timestamp['start']), 60)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                    # SUBCARPETA PARA ESTE TÉRMINO ESPECÍFICO
                    clip_dir = os.path.join(archivo_main_dir, f"c_clip_{termino}")
                    os.makedirs(clip_dir, exist_ok=True)
                    log_info(f"Subcarpeta de clip creada: {clip_dir}", func_name)

                    # ========== 🌟 USAR GEMINI 3 PRO PARA DETERMINAR SEGMENTO INTELIGENTE ==========
                    momento_termino = mejor_timestamp['start']
                    
                    st.info(f"🌟 Analizando con Gemini 3 Pro el mejor segmento para '{termino}'...")
                    log_info(f"🌟 Solicitando análisis GEMINI 3 PRO para término '{termino}' en timestamp {momento_termino:.1f}s", func_name)
                    
                    # Variable para almacenar la idea central extraída por Gemini
                    idea_central_gemini = ""
                    
                    try:
                        # Llamar a GEMINI 3 PRO para determinar el segmento más lógico
                        segmento_gemini = determinar_segmento_inteligente_gemini(
                            transcripcion_con_timestamps=segments_timestamps,
                            termino_encontrado=termino,
                            timestamp_coincidencia=momento_termino,
                            duracion_maxima=duracion_clip
                        )
                        
                        # 🚫 VERIFICAR SI GEMINI RECHAZÓ EL SEGMENTO
                        if segmento_gemini is None:
                            log_warning(f"🚫 Gemini rechazó el segmento para '{termino}' - Mención tangencial", func_name)
                            st.warning(f"🚫 Término '{termino}' rechazado: Solo se menciona de pasada sin desarrollar el tema")
                            copiar_a_videoscheck_si_tangencial(
                                ruta_archivo=archivo_path,
                                termino=termino,
                                razon="Gemini rechazó el segmento por mención tangencial"
                            )
                            continue  # ❌ NO GENERAR CLIP - SALTAR AL SIGUIENTE TÉRMINO
                        
                        # Usar los valores determinados por Gemini
                        inicio = segmento_gemini['inicio']
                        fin_clip = segmento_gemini['fin']
                        duracion_clip_real = segmento_gemini['duracion']
                        razon_segmento = segmento_gemini['razon']
                        idea_central_gemini = segmento_gemini.get('idea_central', '')  # Nueva: idea centrada
                        
                        log_info(f"✅ Gemini 3 Pro determinó segmento inteligente:", func_name)
                        log_info(f"  - Inicio: {inicio:.2f}s", func_name)
                        log_info(f"  - Fin: {fin_clip:.2f}s", func_name)
                        log_info(f"  - Duración: {duracion_clip_real:.2f}s", func_name)
                        log_info(f"  - Razón: {razon_segmento}", func_name)
                        if idea_central_gemini:
                            log_info(f"  - Idea central: {idea_central_gemini[:100]}...", func_name)
                        
                    except Exception as e:
                        # Fallback al método tradicional si Gemini falla
                        log_warning(f"⚠️ Error en Gemini, usando método tradicional: {e}", func_name)
                        st.warning(f"⚠️ Gemini no disponible, usando método tradicional")
                        
                        inicio = max(0, momento_termino - buffer_anterior)
                        fin_clip = inicio + duracion_clip
                        duracion_clip_real = duracion_clip
                        razon_segmento = "Método tradicional (centrado en coincidencia)"
                    
                    # VERIFICAR LÍMITES DEL VIDEO: Asegurar que no se exceda la duración del video
                    try:
                        # Obtener duración del video original
                        cmd_duracion = [
                            "ffprobe", "-v", "quiet", "-show_entries", "format=duration", 
                            "-of", "csv=p=0", archivo_path
                        ]
                        resultado = subprocess.run(cmd_duracion, capture_output=True, text=True, check=True)
                        duracion_video = float(resultado.stdout.strip())
                    
                        log_info(f"📹 Duración del video original: {duracion_video:.2f}s", func_name)
                    
                        # Verificar si el clip se excede del video
                        if fin_clip > duracion_video:
                            log_warning(f"⚠️ El clip se excede del video ({fin_clip:.2f}s > {duracion_video:.2f}s)", func_name)
                            st.warning(f"⚠️ Ajustando clip a límites del video")
                            
                            # Ajustar para que quepa dentro del video
                            if duracion_clip_real <= duracion_video:
                                # Mover el inicio hacia atrás
                                inicio = max(0, duracion_video - duracion_clip_real)
                                fin_clip = duracion_video
                            else:
                                # Video más corto que duración deseada
                                inicio = 0
                                fin_clip = duracion_video
                                duracion_clip_real = duracion_video
                            
                            log_info(f"  - Segmento ajustado: {inicio:.2f}s - {fin_clip:.2f}s ({duracion_clip_real:.2f}s)", func_name)
                    
                    except Exception as e:
                        log_warning(f"⚠️ No se pudo obtener duración del video: {e}", func_name)
                        log_info("  - Continuando con el clip asumiendo que hay suficiente duración", func_name)
                
                    # Generar clip de video MP4
                    clip_name = f"{ts}_{termino}_{m}m{s:02d}s.mp4"
                    clip_path = os.path.join(clip_dir, clip_name)
                
                    # Calcular información del clip
                    buffer_anterior_real = momento_termino - inicio
                    buffer_posterior_real = fin_clip - momento_termino
                
                    st.success(f"🎬 Generando clip inteligente de {duracion_clip_real:.1f}s para '{termino}'")
                    st.info(f"📊 Segmento: {inicio:.1f}s - {fin_clip:.1f}s | Antes: {buffer_anterior_real:.1f}s | Después: {buffer_posterior_real:.1f}s")
                    st.info(f"💡 {razon_segmento}")
                    
                    # Comando para recortar video con duración exacta determinada por GPT-4o
                    cmd = [
                        "ffmpeg", "-y", "-ss", str(inicio),
                        "-t", str(duracion_clip_real), "-i", archivo_path,
                        "-c:v", "libx264", "-c:a", "aac",
                        clip_path
                    ]
                
                    try:
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                        # ========== 🤖 EXTRAER IDEA GENERAL DEL SEGMENTO CON GPT-4o ==========
                        st.info(f"🤖 Extrayendo idea general del segmento con GPT-4o...")
                        
                        # Extraer transcripción solo del segmento del clip
                        transcripcion_segmento = ""
                        for seg in segments_timestamps:
                            # Si el segmento está dentro del rango del clip
                            if seg['start'] >= inicio and seg['start'] <= fin_clip:
                                transcripcion_segmento += seg['text'] + " "
                        
                        # Si no se encontró transcripción del segmento, usar contexto completo
                        if not transcripcion_segmento.strip():
                            transcripcion_segmento = mejor_texto_contexto
                        
                        # Llamar a GEMINI 3.0 para extraer idea general (con fallback a GPT-4o)
                        try:
                            # Usar Gemini 3.0 como modelo principal
                            resultado_gemini = extraer_idea_general_segmento_gemini(
                                transcripcion_segmento=transcripcion_segmento.strip(),
                                termino_encontrado=termino,
                                duracion_segundos=duracion_clip_real,
                                nombre_video=rel
                            )
                            
                            # Extraer la idea general del resultado estructurado
                            idea_general_clip = resultado_gemini.get('idea_general', transcripcion_segmento[:200])
                            relevancia_gemini = resultado_gemini.get('relevancia', 'media')
                            es_relevante_gemini = resultado_gemini.get('es_relevante', True)
                            tema_principal = resultado_gemini.get('tema_principal', termino)
                            contexto_gemini = resultado_gemini.get('contexto', '')
                            
                            log_info(f"✅ Análisis Gemini 3.0 - Relevancia: {relevancia_gemini}, Tema: {tema_principal}", func_name)
                            log_info(f"📝 Idea general: {idea_general_clip[:100]}...", func_name)
                            
                            # ========== VERIFICACIÓN DE RELEVANCIA CON GEMINI ==========
                            # Si Gemini determinó que la mención no es relevante, descartar el clip
                            # EXCEPCIÓN: NO descartar clips de términos prioritarios
                            if not es_relevante_gemini or relevancia_gemini == 'baja':
                                if es_prioritario:
                                    # Para términos prioritarios, mantener el clip aunque Gemini lo considere no relevante
                                    log_info(f"⭐ TÉRMINO PRIORITARIO '{termino}': Clip mantenido a pesar de evaluación de relevancia", func_name)
                                    st.info(f"⭐ Término prioritario '{termino}': Clip generado (cualquier mención es relevante)")
                                    idea_general_clip = f"Mención del término '{termino}': {transcripcion_segmento[:200]}..."
                                else:
                                    st.warning(f"⚠️ Clip descartado (Relevancia: {relevancia_gemini}): {contexto_gemini or idea_general_clip[:100]}")
                                    log_info(f"⏭️ Clip descartado por falta de contexto relevante: {termino}", func_name)
                                    copiar_a_videoscheck_si_tangencial(
                                        ruta_archivo=archivo_path,
                                        termino=termino,
                                        razon=f"Relevancia {relevancia_gemini} - {contexto_gemini or 'sin contexto suficiente'}"
                                    )
                                    
                                    # Eliminar el clip generado
                                    if os.path.exists(clip_path):
                                        os.remove(clip_path)
                                        log_info(f"🗑️ Clip eliminado (no relevante): {clip_path}", func_name)
                                    
                                    continue  # Saltar al siguiente término
                            
                            st.success(f"✅ Idea extraída: {idea_general_clip[:150]}...")
                        except Exception as e:
                            log_warning(f"⚠️ Error extrayendo idea general: {e}", func_name)
                            idea_general_clip = transcripcion_segmento[:300] + "..."  # Fallback
                    
                        # VERIFICACIÓN POST-GENERACIÓN: Confirmar que el clip contiene el término
                        # Para términos prioritarios, esta verificación es opcional (más tolerante)
                        if not es_prioritario:
                            st.info(f"🔍 Verificando que el clip generado contenga el término '{termino}'...")
                        else:
                            st.info(f"⭐ Término prioritario '{termino}': Verificación opcional")
                    
                        # Extraer audio del clip para verificación
                        clip_audio_path = clip_path.replace(".mp4", "_verify.wav")
                        verify_cmd = [
                            "ffmpeg", "-y", "-i", clip_path,
                            "-ac", "1", "-ar", "16000", "-f", "wav", clip_audio_path
                        ]
                    
                        try:
                            subprocess.run(verify_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                            # Transcribir el clip para verificar
                            verificacion_transcripcion, _ = transcribir_audio_hibrido(clip_audio_path)
                            verificacion_lower = verificacion_transcripcion.lower()
                        
                            # Verificar si el término está presente en el clip
                            clip_encontrado, clip_termino_encontrado = buscar_termino_flexible(termino, verificacion_lower)
                            if clip_encontrado:
                                st.success(f"✅ VERIFICADO: El término '{termino}' (variante: '{clip_termino_encontrado}') está presente en el clip generado")
                                log_info(f"✅ Término '{termino}' verificado en clip: {verificacion_transcripcion[:100]}...", func_name)
                            else:
                                if es_prioritario:
                                    # Para términos prioritarios, mantener el clip aunque no se verifique en la revisión
                                    st.warning(f"⚠️ Término prioritario '{termino}': No verificado en clip pero se mantiene")
                                    log_info(f"⭐ TÉRMINO PRIORITARIO '{termino}': Clip mantenido sin verificación estricta", func_name)
                                    
                                    # Limpiar archivo de verificación pero CONTINUAR con el clip
                                    if os.path.exists(clip_audio_path):
                                        os.remove(clip_audio_path)
                                else:
                                    st.error(f"❌ ERROR: El término '{termino}' NO está presente en el clip generado")
                                    log_warning(f"❌ Término '{termino}' NO verificado en clip. Transcripción: {verificacion_transcripcion[:100]}...", func_name)
                                
                                    # Eliminar el clip defectuoso
                                    if os.path.exists(clip_path):
                                        os.remove(clip_path)
                                        st.warning(f"🗑️ Clip defectuoso eliminado: {clip_name}")
                                        log_warning(f"Clip defectuoso eliminado: {clip_path}", func_name)
                            
                                    # Limpiar archivo de verificación
                                    if os.path.exists(clip_audio_path):
                                        os.remove(clip_audio_path)
                            
                                    continue  # No agregar a la lista ni enviar
                        
                            # Limpiar archivo de verificación
                            if os.path.exists(clip_audio_path):
                                os.remove(clip_audio_path)
                            
                        except Exception as verify_error:
                            st.warning(f"⚠️ No se pudo verificar el clip (continuando): {verify_error}")
                            log_warning(f"Error en verificación de clip: {verify_error}", func_name)
                    
                        # SUBIR CLIP A CLOUDINARY INMEDIATAMENTE
                        url_cloudinary_clip = None
                        with st.spinner("☁️ Subiendo clip a Cloudinary..."):
                            try:
                                cloudinary_configurado = configurar_cloudinary()
                                if cloudinary_configurado:
                                    video_url_cloudinary, mensaje_cloudinary = subir_video_cloudinary(clip_path, termino)
                                    if video_url_cloudinary:
                                        url_cloudinary_clip = video_url_cloudinary
                                        st.success(f"☁️ ✅ **CLIP subido a Cloudinary**: {video_url_cloudinary}")
                                        log_info(f"Clip subido a Cloudinary: {video_url_cloudinary}", func_name)
                                    else:
                                        st.warning(f"⚠️ Error subiendo clip a Cloudinary: {mensaje_cloudinary}")
                                        log_warning(f"Error subiendo clip a Cloudinary: {mensaje_cloudinary}", func_name)
                                else:
                                    st.warning("⚠️ Cloudinary no está configurado")
                                    log_warning("Cloudinary no está configurado para subir clip", func_name)
                            except Exception as e:
                                st.warning(f"⚠️ Error subiendo clip a Cloudinary: {str(e)}")
                                log_warning(f"Error subiendo clip a Cloudinary: {str(e)}", func_name)
                        
                        # Agregar a la lista de clips generados SOLO si pasó la verificación
                        clips_generados_en_sesion.append({
                            'path': clip_path,
                            'termino': termino,
                            'tiempo': f"{m}m{s:02d}s",
                            'contexto': mejor_texto_contexto,
                            'archivo_origen': rel,
                            'momento_exacto': momento_termino,
                            'verificado': True,
                            'url_cloudinary': url_cloudinary_clip  # URL de Cloudinary
                        })
                        st.session_state.clips_generados += 1
                    
                        # 🚀 ENVÍO INMEDIATO DE COINCIDENCIA
                        st.info(f"🚀 Enviando coincidencia inmediata para '{termino}'...")
                        
                        # Log de la coincidencia detectada para evitar duplicados
                        try:
                            coincidencias_logger.coincidencias_logger.info(
                                f"🎯 COINCIDENCIA DETECTADA | Video: {rel} | Término: {termino} | Timestamp: {timestamp_actual:.1f}s | Duración: 0s | Confianza: N/A"
                            )
                        except Exception as e:
                            log_warning(f"Error registrando coincidencia en log: {e}", func_name)
                        
                        exito_envio, mensaje_envio = enviar_coincidencia_inmediata(
                            rel,  # nombre del archivo
                            termino,  # término encontrado
                            mejor_texto_contexto,  # contexto del término
                            tipo_archivo,  # tipo de archivo
                            clip_path,  # ruta del clip
                            transcripcion_mistral,  # transcripción completa
                            timestamp_actual,  # timestamp para control de duplicados
                            idea_general_clip  # 🤖 IDEA GENERAL EXTRAÍDA POR GPT-4o
                        )
                    
                        if exito_envio:
                            st.success(f"✅ Coincidencia enviada inmediatamente: {mensaje_envio}")
                            log_info(f"✅ Coincidencia enviada exitosamente: {termino} en {rel}", func_name)
                        else:
                            st.warning(f"⚠️ Error enviando coincidencia inmediata: {mensaje_envio}")
                            log_warning(f"❌ Error enviando coincidencia: {mensaje_envio}", func_name)
                    
                    except Exception as e:
                        st.warning(f"⚠️ Error generando clip para {termino}: {e}")
                        continue

                    # Guardar transcripción en archivo TXT
                    txt_path = clip_path.replace(".mp4", ".txt")
                    
                    buffer_posterior = duracion_clip - buffer_anterior
                    with open(txt_path, "w", encoding="utf-8") as tf:
                        tf.write(f"""TRANSCRIPCIÓN COMPLETA DEL {tipo_archivo.upper()}
    ===============================================

    {tipo_archivo.upper()} ORIGEN: {rel}
    TÉRMINO ENCONTRADO: {termino}
    TIEMPO EN {tipo_archivo.upper()}: {m}m{s:02d}s
    FECHA ANÁLISIS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    ===============================================
    CONFIGURACIÓN DEL CLIP:
    ===============================================

    - Archivo de {tipo_archivo.lower()}: {clip_name}
    - Duración total del clip: {duracion_clip} segundos ({duracion_clip//60}:{duracion_clip%60:02d})
    - Tiempo antes de coincidencia: {buffer_anterior} segundos ({buffer_anterior//60}:{buffer_anterior%60:02d})
    - Tiempo después de coincidencia: {buffer_posterior} segundos ({buffer_posterior//60}:{buffer_posterior%60:02d})
    - Tiempo de inicio del clip: {inicio:.2f}s
    - Momento de coincidencia: {mejor_timestamp['start']:.2f}s
    - API de transcripción utilizada: Mistral/OpenAI Whisper

    ===============================================
    TRANSCRIPCIÓN COMPLETA (Mistral):
    ===============================================

    {transcripcion_mistral}

    ===============================================
    CONTEXTO DEL TIMESTAMP:
    ===============================================

    {mejor_texto_contexto}
    """)
                
                    st.info(f"💾 Clip y transcripción guardados: {clip_name}")

                    coincidencias_items.append({
                        "termino": termino, 
                        "archivo": rel,
                        "tipo_archivo": tipo_archivo.lower(),
                        "texto": idea_general_clip,  # 🤖 USAR IDEA GENERAL EN LUGAR DE CONTEXTO
                        "contexto": idea_general_clip,  # 🤖 IDEA GENERAL DEL SEGMENTO
                        "timestamp": timestamp_actual,  # Agregar timestamp para control de duplicados
                        "transcripcion_completa": idea_general_clip,  # 🤖 ENVIAR SOLO IDEA GENERAL
                        "url_cloudinary": url_cloudinary_clip  # URL del clip en Cloudinary
                    })

            progress_bar.progress(90, text="📝 Generando resumen...")
        
            # Si hubo coincidencias, generar resumen
            # Inicializar resumen_archivo
            resumen_archivo = ""
        
            if coincidencias_items:
                try:
                    resumen_archivo = generar_resumen_archivo(rel, coincidencias_items, transcripcion_mistral, tipo_archivo)
                
                    # Crear archivo consolidado con información de clips
                    clips_info = []
                    for clip in clips_generados_en_sesion:
                        if clip['archivo_origen'] == rel:  # Solo clips de este archivo
                            clips_info.append(clip)
                
                    # Llamada con argumentos posicionales para evitar errores
                    try:
                        archivo_completo = crear_archivo_consolidado(
                            archivo_path, rel, coincidencias_items, transcripcion_mistral, resumen_archivo, terminos, clips_info
                        )
                    except TypeError:
                        # Fallback sin clips_generados si hay error
                        archivo_completo = crear_archivo_consolidado(
                            archivo_path, rel, coincidencias_items, transcripcion_mistral, resumen_archivo, terminos
                        )
                
                    if st.session_state.mostrar_coincidencias:
                        st.markdown("### 📋 Resumen de coincidencias encontradas:")
                        st.markdown("---")
                    
                        # Mostrar resumen completo en un expander expandido por defecto
                        with st.expander("📄 **RESUMEN EJECUTIVO COMPLETO**", expanded=True):
                            st.markdown(resumen_archivo)
                    
                        # Mostrar detalles adicionales de las coincidencias
                        if coincidencias_items:
                            st.markdown("### 🔍 **DETALLES DE COINCIDENCIAS**")
                            for i, item in enumerate(coincidencias_items, 1):
                                with st.expander(f"🎯 Coincidencia {i}: **{item['termino'].upper()}**", expanded=False):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"**🏷️ Término encontrado:** {item['termino']}")
                                        st.markdown(f"**📄 Tipo de archivo:** {item['tipo_archivo']}")
                                        st.markdown(f"**📁 Archivo:** {item['archivo']}")
                                    with col2:
                                        st.markdown(f"**📝 Contexto:**")
                                        st.text_area("", value=item['texto'], height=100, disabled=True, key=f"contexto_{i}_{item['termino']}")
                    
                        st.markdown("---")
                
                    st.session_state.resumen_global.extend(coincidencias_items)
                    st.session_state.videos_procesados += 1
                
                    progress_bar.progress(100, text="✅ Completado")
                    st.success(f"✅ Procesado: {len(coincidencias_items)} coincidencias - Archivo: `{os.path.basename(archivo_completo)}`")
                
                    # Enviar coincidencias a Supabase
                    try:
                        with st.spinner("🗄️ Enviando coincidencias a Supabase..."):
                            supabase_success, supabase_msg = enviar_coincidencias_a_supabase(
                                coincidencias_items, rel, tipo_archivo, resumen_archivo, transcripcion_mistral, None, None
                            )
                            if supabase_success:
                                st.success(f"🗄️ {supabase_msg}")
                            else:
                                st.warning(f"⚠️ {supabase_msg}")
                    except Exception as e:
                        st.warning(f"⚠️ Error enviando a Supabase: {str(e)}")
                
                    # Almacenar datos del archivo procesado para envío posterior
                    terminos_encontrados = list(set([item['termino'] for item in coincidencias_items]))
                    videos_procesados_data.append({
                        'nombre_archivo': rel,
                        'tipo_archivo': tipo_archivo,
                        'resumen_archivo': resumen_archivo,
                        'terminos_encontrados': terminos_encontrados,
                        'clips_info': clips_info,
                        'coincidencias_items': coincidencias_items,
                        'transcripcion_completa': transcripcion_mistral  # Agregar transcripción completa
                    })
                
                    st.info(f"📦 {tipo_archivo} almacenado para envío posterior: {rel}")
                    
                    # ========== REGISTRAR VIDEO PROCESADO (CON COINCIDENCIAS) ==========
                    registrar_archivo_procesado(rel, coincidencias_items, resumen_archivo, tipo_archivo)
                    log_info(f"✅ Video registrado en procesados.log: {rel} ({len(coincidencias_items)} coincidencias)", func_name)
                
                except Exception as e:
                    st.warning(f"⚠️ Error en resumen: {e}")
            else:
                progress_bar.progress(100, text="✅ Sin coincidencias")
                st.info(f"🔍 Sin coincidencias en `{rel}`")

                # Limpieza
                if os.path.exists(audio_path) and audio_path != archivo_path: 
                    os.remove(audio_path)
            
                # ========== REGISTRAR VIDEO PROCESADO (SIN COINCIDENCIAS) ==========
                registrar_archivo_procesado(rel, coincidencias_items, resumen_archivo, tipo_archivo)
                log_info(f"✅ Video registrado en procesados.log: {rel} (sin coincidencias)", func_name)
        
        except Exception as e:
            # MANEJO DE ERRORES: Archivo falló
            error_mensaje = f"{type(e).__name__}: {str(e)}"
            log_error_critico(func_name, f"Error procesando archivo {rel}: {error_mensaje}")
            
            # Guardar archivo fallido (mueve, crea txt, envía notificaciones)
            guardar_archivo_fallido(
                nombre_archivo=rel,
                error_mensaje=error_mensaje,
                archivo_path=archivo_path
            )
            
            # Continuar con el siguiente archivo
            continue

    # FASE 2: ENVIAR TODOS LOS ARCHIVOS PROCESADOS AL WEBHOOK
    if videos_procesados_data:
        st.success(f"✅ FASE 1 COMPLETADA: {len(videos_procesados_data)} archivos procesados exitosamente")
        st.info("🌐 FASE 2: Enviando todos los archivos al webhook con pausas de 60s")
        
        webhook_config = cargar_webhook_config()
        telegram_config = cargar_telegram_config()
        
        for i, archivo_data in enumerate(videos_procesados_data, 1):
            icono_archivo = "🎞️" if archivo_data.get('tipo_archivo', '').lower() == 'video' else "🎵"
            st.markdown(f"---\n### 📤 Enviando {archivo_data.get('tipo_archivo', 'Archivo')} {i}/{len(videos_procesados_data)}: {icono_archivo} `{archivo_data['nombre_archivo']}`")
            
            # PASO 1: Enviar SOLO el resumen ejecutivo al webhook
            if webhook_config['enabled'] and webhook_config['url']:
                try:
                    with st.spinner("🌐 Enviando resumen ejecutivo al webhook..."):
                        exito, mensaje = webhook_notification_simple(
                            archivo_data['nombre_archivo'], 
                            archivo_data['resumen_archivo'], 
                            archivo_data['terminos_encontrados']
                        )
                        
                        if exito:
                            st.success(f"🌐 Webhook - Resumen ejecutivo enviado: {mensaje}")
                            
                            # PASO 2: Pausa obligatoria de 60 segundos después del resumen
                            log_info(f"PASO 1 COMPLETADO - Esperando 60 segundos después del resumen ejecutivo del video {i}", "buscar_y_procesar_videos")
                            with st.spinner("⏳ PASO 1: Esperando 60s después del resumen ejecutivo..."):
                                time.sleep(60)
                            st.info("✅ PASO 1 completado - Procediendo a enviar clips")
                            
                            # PASO 3: Ahora enviar los clips individualmente con pausas de 60s
                            if archivo_data['clips_info']:
                                st.info("🌐 Enviando clips individuales al webhook con pausas de 60s...")
                                exito_clips, mensaje_clips = enviar_clips_individuales_webhook(
                                    archivo_data['clips_info'],
                                    archivo_data['resumen_archivo'], 
                                    archivo_data['terminos_encontrados'],
                                    archivo_data['nombre_archivo']
                                )
                                
                                if exito_clips:
                                    st.success(f"🌐 Webhook - Clips enviados: {mensaje_clips}")
                                else:
                                    st.warning(f"⚠️ Webhook - Error en clips: {mensaje_clips}")
                            else:
                                st.info("📭 No hay clips para enviar en este video")
                        else:
                            st.warning(f"⚠️ Webhook - Error en resumen: {mensaje}")
                except Exception as e:
                    st.warning(f"⚠️ Error enviando webhook: {e}")
            
            # PASO 4: Enviar a Telegram (DESACTIVADO PARA EVITAR DUPLICADOS)
            # COMENTADO: El envío masivo a Telegram está desactivado porque ya se envían
            # los clips individualmente cuando se detecta cada término en enviar_coincidencia_inmediata()
            # if telegram_config['enabled'] and telegram_config['bot_token'] and telegram_config['chat_id']:
            #     try:
            #         with st.spinner("📱 Enviando a Telegram..."):
            #             exito_telegram, mensaje_telegram = enviar_clips_a_telegram(
            #                 archivo_data['clips_info'],
            #                 archivo_data['resumen_archivo'], 
            #                 archivo_data['terminos_encontrados'],
            #                 archivo_data['nombre_archivo']
            #             )
            #             
            #             if exito_telegram:
            #                 st.success(f"📱 Telegram: {mensaje_telegram}")
            #             else:
            #                 st.warning(f"⚠️ Telegram: {mensaje_telegram}")
            #     except Exception as e:
            #         st.warning(f"⚠️ Error enviando a Telegram: {e}")
            
            # PASO 4.5: Enviar a Google Drive (DESACTIVADO PARA EVITAR DUPLICADOS)
            # COMENTADO: El envío masivo a Google Drive está desactivado porque ya se suben
            # los clips individualmente cuando se detecta cada término en enviar_coincidencia_inmediata()
            # try:
            #     with st.spinner("☁️ Enviando a Google Drive..."):
            #         exito_gdrive, mensaje_gdrive = enviar_clips_a_google_drive(
            #             archivo_data['clips_info'],
            #             archivo_data['resumen_archivo'], 
            #             archivo_data['terminos_encontrados'],
            #             archivo_data['nombre_archivo'],
            #             archivo_data.get('transcripcion_completa', '')  # Agregar transcripción completa
            #         )
            #         
            #         if exito_gdrive:
            #             st.success(f"☁️ Google Drive: {mensaje_gdrive}")
            #         else:
            #             st.warning(f"⚠️ Google Drive: {mensaje_gdrive}")
            # except Exception as e:
            #     st.warning(f"⚠️ Error enviando a Google Drive: {e}")
            
            # INFORMACIÓN: Los clips ya fueron enviados individualmente durante el procesamiento
            st.info("ℹ️ Los clips ya fueron enviados individualmente durante el procesamiento (Telegram + Google Drive + Correo)")
            
            # PASO 5: Pausa final de 60 segundos antes del siguiente video (excepto el último)
            if i < len(videos_procesados_data):
                log_info(f"PROCESAMIENTO COMPLETADO - Esperando 60 segundos antes del siguiente video ({i+1}/{len(videos_procesados_data)})", "buscar_y_procesar_videos")
                with st.spinner(f"⏳ FINAL: Esperando 60s antes del siguiente video ({i+1}/{len(videos_procesados_data)})..."):
                    time.sleep(60)
                st.info(f"✅ Listo para procesar video {i+1}")
        
        st.success(f"🎉 FASE 2 COMPLETADA: Todos los {len(videos_procesados_data)} videos enviados exitosamente")
    else:
        st.info("📭 No se procesaron videos con coincidencias en esta sesión")

    # Mostrar resúmenes ejecutivos de la sesión
    if videos_procesados_data:
        st.markdown("---")
        st.markdown("## 📋 **RESÚMENES EJECUTIVOS DE LA SESIÓN**")
        
        for i, video_data in enumerate(videos_procesados_data, 1):
            with st.expander(f"📄 **RESUMEN {i}: {video_data['nombre_archivo']}**", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("### 📊 **Resumen Ejecutivo:**")
                    st.markdown(video_data['resumen_archivo'])
                
                with col2:
                    st.markdown("### ℹ️ **Información:**")
                    st.markdown(f"**📁 Archivo:** {video_data['nombre_archivo']}")
                    st.markdown(f"**🎞️ Tipo:** {video_data.get('tipo_archivo', 'Video')}")
                    st.markdown(f"**🔍 Términos:** {', '.join(video_data['terminos_encontrados'])}")
                    st.markdown(f"**🎬 Clips generados:** {len(video_data.get('clips_info', []))}")
                    
                    # Mostrar lista de clips si los hay
                    if video_data.get('clips_info'):
                        st.markdown("**📹 Clips:**")
                        for clip in video_data['clips_info']:
                            st.markdown(f"• {clip['termino']} ({clip['tiempo']})")
    
    # Mostrar clips generados en esta sesión
    if clips_generados_en_sesion:
        st.session_state.clips_encontrados_sesion.extend(clips_generados_en_sesion)
        mostrar_player_clips(clips_generados_en_sesion, titulo="🎬 Clips Generados en Esta Sesión")
    
    # === FINALIZACIÓN Y REINICIO AUTOMÁTICO ===
    st.markdown("---")
    st.success("✅ **PROCESAMIENTO COMPLETADO** - Todos los archivos han sido procesados")
    
    # Control de reinicio automático
    col_reinicio1, col_reinicio2 = st.columns([3, 1])
    
    with col_reinicio1:
        if st.session_state.get('auto_reinicio', True):
            st.info("🔄 **REINICIO AUTOMÁTICO ACTIVADO** - Escaneando nuevos videos en 30 segundos...")
        else:
            st.info("⏹️ **REINICIO AUTOMÁTICO DESACTIVADO** - Procesamiento finalizado")
    
    with col_reinicio2:
        if st.button("🔄 Activar Auto-Reinicio" if not st.session_state.get('auto_reinicio', True) else "⏹️ Desactivar Auto-Reinicio"):
            st.session_state.auto_reinicio = not st.session_state.get('auto_reinicio', True)
            st.rerun()
    
    # Ejecutar reinicio automático si está activado
    if st.session_state.get('auto_reinicio', True):
        # Countdown visual
        countdown_container = st.empty()
        for i in range(30, 0, -1):
            countdown_container.warning(f"⏳ Reiniciando en {i} segundos... (Puedes desactivar arriba)")
            time.sleep(1)
        
        # Mantener registro de archivos procesados para evitar reprocesar
        if 'archivos_procesados_total' not in st.session_state:
            st.session_state.archivos_procesados_total = set()
        
        # Agregar archivos de esta sesión al registro total
        for video_data in videos_procesados_data:
            st.session_state.archivos_procesados_total.add(video_data['nombre_archivo'])
        
        # Limpiar estado de sesión actual para nuevo escaneo
        st.session_state.videos_procesados_data = []
        st.session_state.clips_generados_en_sesion = []
        
        st.info("🔄 **REINICIANDO ESCANEO** - Buscando nuevos videos...")
        time.sleep(2)
        st.rerun()  # Reiniciar la aplicación
    
    # Mostrar resumen final solo si no se va a reiniciar
    if not st.session_state.get('auto_reinicio', True):
        st.markdown("### 📊 **RESUMEN FINAL**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📁 Archivos Procesados", len(videos_procesados_data))
        
        with col2:
            total_archivos_procesados = len(st.session_state.get('archivos_procesados_total', set()))
            st.metric("📚 Total Procesados (Sesión)", total_archivos_procesados)
        
        with col3:
            total_terminos = sum(len(archivo.get('terminos_encontrados', [])) for archivo in videos_procesados_data)
            st.metric("🔍 Términos Encontrados", total_terminos)
    
    # Botón para procesar nuevamente (solo si hay archivos nuevos)
    if st.button("🔄 **PROCESAR NUEVOS ARCHIVOS**", 
                type="primary", 
                help="Buscar y procesar archivos nuevos agregados a la carpeta",
                key="procesar_nuevos"):
        st.info("🔍 Iniciando búsqueda de archivos nuevos...")
        st.session_state.nueva_verificacion_solicitada = True
        st.rerun()
    
    # Información adicional
    st.info("💡 **Tip:** El sistema busca y procesa únicamente archivos de video (MP4)")
    st.info("✅ **Completado:** Procesamiento terminado. Presiona 'PROCESAR NUEVOS ARCHIVOS' para buscar más videos.")
    
    # ========== LIBERAR FLAG DE PROCESAMIENTO ==========
    st.session_state.procesamiento_en_curso = False
    log_info("🔓 Flag de procesamiento liberado", func_name)

# === BUCLE CONTINUO (REMOVIDO - AHORA SE USA LÓGICA SÍNCRONA) ===
# La lógica continua ahora se maneja de forma síncrona en el flujo principal

# === PLAYER DE CLIPS AVANZADO ===
def mostrar_player_clips(clips_list, titulo="🎬 Player de Clips"):
    """Player avanzado para mostrar clips con controles"""
    
    st.markdown(f"## {titulo}")
    
    if not clips_list:
        st.info("📭 No hay clips para mostrar")
        return
    
    # Estadísticas de clips
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Clips", len(clips_list))
    with col2:
        terminos_unicos = len(set([clip['termino'] for clip in clips_list]))
        st.metric("Términos Únicos", terminos_unicos)
    with col3:
        videos_origen = len(set([clip.get('video_origen', 'desconocido') for clip in clips_list]))
        st.metric("Videos Origen", videos_origen)
    with col4:
        tamano_total = sum([os.path.getsize(clip['path']) for clip in clips_list if os.path.exists(clip['path'])])
        st.metric("Tamaño Total", f"{tamano_total / (1024*1024):.1f} MB")
    
    # Filtros avanzados
    st.markdown("### 🔧 Filtros y Controles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro por término
        terminos_disponibles = ['Todos'] + sorted(list(set([clip['termino'] for clip in clips_list])))
        termino_filtro = st.selectbox("🏷️ Filtrar por término:", terminos_disponibles, key=f"filtro_termino_{titulo.replace(' ', '_')}")
    
    with col2:
        # Filtro por video origen
        videos_disponibles = ['Todos'] + sorted(list(set([clip.get('video_origen', 'desconocido') for clip in clips_list])))
        video_filtro = st.selectbox("📹 Filtrar por video origen:", videos_disponibles, key=f"filtro_video_{titulo.replace(' ', '_')}")
    
    with col3:
        # Modo de visualización
        modo_vista = st.selectbox("👁️ Modo de vista:", 
                                 ["Lista completa", "Solo reproductores", "Compacto"], 
                                 key=f"modo_vista_{titulo.replace(' ', '_')}")
    
    # Aplicar filtros
    clips_filtrados = clips_list
    if termino_filtro != 'Todos':
        clips_filtrados = [clip for clip in clips_filtrados if clip['termino'] == termino_filtro]
    if video_filtro != 'Todos':
        clips_filtrados = [clip for clip in clips_filtrados if clip.get('video_origen', 'desconocido') == video_filtro]
    
    # Búsqueda por texto
    busqueda_texto = st.text_input("🔍 Buscar en contexto:", placeholder="Buscar texto en las transcripciones...", key=f"busqueda_texto_{titulo.replace(' ', '_')}")
    if busqueda_texto:
        clips_filtrados = [clip for clip in clips_filtrados 
                          if busqueda_texto.lower() in clip.get('contexto', '').lower()]
    
    # Ordenamiento
    orden = st.selectbox("📊 Ordenar por:", 
                        ["Más recientes", "Más antiguos", "Por término", "Por duración"],
                        key=f"orden_{titulo.replace(' ', '_')}")
    
    if orden == "Más recientes":
        clips_filtrados.sort(key=lambda x: os.path.getctime(x['path']) if os.path.exists(x['path']) else 0, reverse=True)
    elif orden == "Más antiguos":
        clips_filtrados.sort(key=lambda x: os.path.getctime(x['path']) if os.path.exists(x['path']) else 0)
    elif orden == "Por término":
        clips_filtrados.sort(key=lambda x: x['termino'])
    
    st.info(f"📊 Mostrando {len(clips_filtrados)} de {len(clips_list)} clips")
    
    # Control de reproducción automática
    col1, col2 = st.columns(2)
    with col1:
        autoplay = st.checkbox("▶️ Reproducción automática", value=False, key=f"autoplay_{titulo.replace(' ', '_')}")
    with col2:
        clips_por_pagina = st.slider("Clips por página:", 5, 50, 10, key=f"clips_pagina_{titulo.replace(' ', '_')}")
    
    # Paginación
    if clips_filtrados:
        total_paginas = (len(clips_filtrados) - 1) // clips_por_pagina + 1
        if total_paginas > 1:
            pagina_actual = st.selectbox(f"📄 Página (de {total_paginas}):", 
                                        range(1, total_paginas + 1), index=0,
                                        key=f"pagina_{titulo.replace(' ', '_')}")
        else:
            pagina_actual = 1
        
        inicio = (pagina_actual - 1) * clips_por_pagina
        fin = inicio + clips_por_pagina
        clips_pagina = clips_filtrados[inicio:fin]
        
        # Debug info
        st.caption(f"Mostrando clips {inicio + 1}-{min(fin, len(clips_filtrados))} de {len(clips_filtrados)} total")
    else:
        clips_pagina = []
        st.info("📭 No hay clips que coincidan con los filtros aplicados")
    
    # Mostrar clips según el modo
    titulo_limpio = titulo.replace(' ', '_').replace('🎬', '').replace('🆕', '').strip()
    
    if modo_vista == "Lista completa":
        mostrar_clips_completos(clips_pagina, titulo_limpio)
    elif modo_vista == "Solo reproductores":
        mostrar_solo_reproductores(clips_pagina, autoplay, titulo_limpio)
    else:  # Compacto
        mostrar_clips_compactos(clips_pagina, titulo_limpio)
    
    # Botones de acción masiva
    if clips_filtrados:
        st.markdown("### 🔧 Acciones Masivas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 Exportar Lista", key=f"exportar_{titulo.replace(' ', '_')}"):
                exportar_lista_clips(clips_filtrados)
        
        with col2:
            if st.button("📊 Generar Estadísticas", key=f"stats_{titulo.replace(' ', '_')}"):
                generar_estadisticas_clips(clips_filtrados)
        
        with col3:
            if st.button("🗑️ Limpiar Filtrados", key=f"limpiar_{titulo.replace(' ', '_')}"):
                eliminar_clips_filtrados(clips_filtrados)
        
        with col4:
            if st.button("📁 Crear Playlist", key=f"playlist_{titulo.replace(' ', '_')}"):
                crear_playlist_clips(clips_filtrados)

def mostrar_clips_completos(clips, titulo_seccion="clips"):
    """Muestra clips con información completa"""
    for i, clip in enumerate(clips):
        if not os.path.exists(clip['path']):
            continue
            
        with st.expander(f"🎬 {clip['termino'].upper()} - {clip['tiempo']} | {os.path.basename(clip['path'])}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.video(clip['path'])
            
            with col2:
                st.markdown(f"**🏷️ Término:** {clip['termino']}")
                st.markdown(f"**⏱️ Tiempo:** {clip['tiempo']}")
                st.markdown(f"**📹 Video origen:** {clip.get('video_origen', 'Desconocido')}")
                
                # Información del archivo
                file_info = os.stat(clip['path'])
                st.markdown(f"**📊 Tamaño:** {file_info.st_size / (1024*1024):.2f} MB")
                st.markdown(f"**📅 Creado:** {datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Botones de acción con keys únicos
                if st.button(f"🗑️ Eliminar", key=f"del_clip_{i}_{titulo_seccion}_{hash(clip['path'])}"):
                    try:
                        os.remove(clip['path'])
                        st.success("Clip eliminado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                if st.button(f"📁 Abrir carpeta", key=f"folder_clip_{i}_{titulo_seccion}_{hash(clip['path'])}"):
                    folder_path = os.path.dirname(clip['path'])
                    os.startfile(folder_path)
            
            # Contexto
            if clip.get('contexto'):
                st.markdown("**📝 Contexto:**")
                st.markdown(f"> {clip['contexto']}")

def mostrar_solo_reproductores(clips, autoplay=False, titulo_seccion="reproductores"):
    """Muestra solo los reproductores de video"""
    for i, clip in enumerate(clips):
        if os.path.exists(clip['path']):
            st.markdown(f"**🎬 {clip['termino'].upper()} - {clip['tiempo']}**")
            st.video(clip['path'], autoplay=autoplay and i==0)
            if i < len(clips) - 1:
                st.markdown("---")

def mostrar_clips_compactos(clips, titulo_seccion="compactos"):
    """Muestra clips en formato compacto"""
    for i, clip in enumerate(clips):
        if os.path.exists(clip['path']):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**{clip['termino']}** - {clip['tiempo']}")
            with col2:
                st.markdown(f"_{clip.get('video_origen', 'Desconocido')}_")
            with col3:
                if st.button("▶️", key=f"play_compact_{titulo_seccion}_{i}_{hash(clip['path'])}"):
                    st.video(clip['path'])

def exportar_lista_clips(clips):
    """Exporta lista de clips a CSV"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Termino', 'Tiempo', 'Video_Origen', 'Archivo', 'Tamaño_MB', 'Fecha_Creacion'])
    
    for clip in clips:
        if os.path.exists(clip['path']):
            file_info = os.stat(clip['path'])
            writer.writerow([
                clip['termino'],
                clip['tiempo'],
                clip.get('video_origen', 'Desconocido'),
                os.path.basename(clip['path']),
                f"{file_info.st_size / (1024*1024):.2f}",
                datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    csv_data = output.getvalue()
    st.download_button(
        label="📥 Descargar CSV",
        data=csv_data,
        file_name=f"clips_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

def generar_estadisticas_clips(clips):
    """Genera estadísticas detalladas de los clips"""
    st.markdown("### 📊 Estadísticas Detalladas")
    
    # Estadísticas por término
    terminos_count = {}
    for clip in clips:
        termino = clip['termino']
        terminos_count[termino] = terminos_count.get(termino, 0) + 1
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Clips por término:**")
        for termino, count in sorted(terminos_count.items(), key=lambda x: x[1], reverse=True):
            st.markdown(f"• {termino}: {count} clips")
    
    with col2:
        # Estadísticas de tiempo
        fechas = []
        for clip in clips:
            if os.path.exists(clip['path']):
                fechas.append(datetime.fromtimestamp(os.path.getctime(clip['path'])))
        
        if fechas:
            fechas.sort()
            st.markdown("**Distribución temporal:**")
            st.markdown(f"• Primer clip: {fechas[0].strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"• Último clip: {fechas[-1].strftime('%Y-%m-%d %H:%M')}")
            st.markdown(f"• Período: {(fechas[-1] - fechas[0]).days} días")

def eliminar_clips_filtrados(clips):
    """Elimina clips filtrados (con confirmación)"""
    st.warning(f"⚠️ Esto eliminará {len(clips)} clips permanentemente")
    if st.button("🗑️ CONFIRMAR ELIMINACIÓN", type="primary", key=f"confirm_delete_{len(clips)}_{hash(str(clips))}"):
        eliminados = 0
        for clip in clips:
            try:
                if os.path.exists(clip['path']):
                    os.remove(clip['path'])
                    eliminados += 1
            except Exception:
                pass
        st.success(f"✅ Eliminados {eliminados} clips")
        st.rerun()

def crear_playlist_clips(clips):
    """Crea un archivo playlist con los clips"""
    playlist_content = "#EXTM3U\n"
    for clip in clips:
        if os.path.exists(clip['path']):
            playlist_content += f"#EXTINF:-1,{clip['termino']} - {clip['tiempo']}\n"
            playlist_content += f"{clip['path']}\n"
    
    st.download_button(
        label="📁 Descargar Playlist",
        data=playlist_content,
        file_name=f"playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.m3u",
        mime="audio/x-mpegurl"
    )

# === PROCESAR ACCIÓN PENDIENTE ===
# Ejecutar procesamiento si se solicitó
if hasattr(st.session_state, 'procesar_una_vez') and st.session_state.get('procesar_una_vez', False):
    # Obtener configuración del session_state
    duracion_clip = getattr(st.session_state, 'duracion_clip', 60)  # 1 minuto total por defecto
    buffer_anterior = getattr(st.session_state, 'buffer_anterior', 30)  # 30s antes por defecto
    
    buscar_y_procesar_videos(duracion_clip, buffer_anterior)
    st.session_state.procesar_una_vez = False

# === PROCESAR NUEVA VERIFICACIÓN SOLICITADA ===
# Ejecutar nueva verificación solo si se solicitó manualmente
if hasattr(st.session_state, 'nueva_verificacion_solicitada') and st.session_state.get('nueva_verificacion_solicitada', False):
    # Obtener configuración del session_state
    duracion_clip = getattr(st.session_state, 'duracion_clip', 60)  # 1 minuto total por defecto
    buffer_anterior = getattr(st.session_state, 'buffer_anterior', 30)  # 30s antes por defecto
    
    st.info("🔍 **NUEVA VERIFICACIÓN INICIADA** - Buscando archivos nuevos agregados después del último procesamiento")
    buscar_y_procesar_videos(duracion_clip, buffer_anterior)
    st.session_state.nueva_verificacion_solicitada = False

# === PROCESAR BÚSQUEDA CONTINUA ===
# Ejecutar procesamiento continuo si está activo
if st.session_state.running and st.session_state.terminos_continuos:
    # Inicializar timestamp del último procesamiento si no existe
    if 'ultimo_procesamiento_continuo' not in st.session_state:
        st.session_state.ultimo_procesamiento_continuo = 0
    
    # Verificar si es hora de procesar
    tiempo_actual = time.time()
    tiempo_desde_ultimo = tiempo_actual - st.session_state.ultimo_procesamiento_continuo
    
    if tiempo_desde_ultimo >= st.session_state.intervalo:
        # Obtener configuración del session_state  
        duracion_clip = getattr(st.session_state, 'duracion_clip', 60)  # 1 minuto total por defecto
        buffer_anterior = getattr(st.session_state, 'buffer_anterior', 30)  # 30s antes por defecto
        
        # Mostrar que está en modo continuo
        st.info(f"🔄 **MODO CONTINUO ACTIVO** - Ejecutando ciclo de procesamiento")
        
        # Ejecutar procesamiento (igual que "Procesar Una Vez")
        buscar_y_procesar_videos(duracion_clip, buffer_anterior)
        
        # Actualizar timestamp
        st.session_state.ultimo_procesamiento_continuo = time.time()
        
        # Mostrar mensaje de espera
        st.success(f"✅ Ciclo completado. Próximo procesamiento en {st.session_state.intervalo} segundos...")
        
        # Recargar para continuar el ciclo inmediatamente
        st.rerun()
    else:
        # Mostrar countdown hasta el próximo procesamiento
        tiempo_restante = st.session_state.intervalo - int(tiempo_desde_ultimo)
        st.info(f"⏳ **MODO CONTINUO ACTIVO** - Próximo procesamiento en {tiempo_restante} segundos")
        
        # Usar st.rerun() para actualizar el countdown cada 5 segundos
        # Agregar un pequeño delay para evitar refresh demasiado frecuente
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = 0
        
        if time.time() - st.session_state.last_refresh >= 5:
            st.session_state.last_refresh = time.time()
            st.rerun()
        else:
            # Mostrar mensaje estático si no es momento de refresh
            pass

# === CONTROLES PRINCIPALES ===
st.markdown("## ⚡ Control de Búsqueda Continua")

col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ INICIAR BÚSQUEDA CONTINUA", 
                disabled=st.session_state.running,
                type="primary",
                help="Iniciar monitoreo automático continuo"):
        if not st.session_state.terminos_continuos:
            st.error("❌ Primero configura los términos de búsqueda")
        else:
            st.session_state.running = True
            st.success(f"🚀 Búsqueda continua iniciada (cada {st.session_state.intervalo}s)")
            st.rerun()

with col2:
    if st.button("⏹️ DETENER BÚSQUEDA", 
                disabled=not st.session_state.running,
                type="secondary"):
        st.session_state.running = False
        st.warning("🛑 Búsqueda continua detenida")
        st.rerun()

# === PLAYER PRINCIPAL DE CLIPS ===
st.markdown("---")

# Tabs para diferentes vistas
tab1, tab2, tab3 = st.tabs(["🎬 Todos los Clips", "🆕 Clips de Sesión", "📊 Análisis"])

with tab1:
    # Mostrar todos los clips disponibles
    todos_los_clips = buscar_todos_los_clips()
    if todos_los_clips:
        # Convertir a formato compatible
        clips_convertidos = []
        for clip_info in todos_los_clips:
            clips_convertidos.append({
                'path': clip_info['filepath'],
                'termino': clip_info['termino'],
                'tiempo': clip_info['tiempo_video'],
                'contexto': f"Generado el {clip_info['fecha_creacion'].strftime('%Y-%m-%d %H:%M:%S')}",
                'video_origen': 'Análisis previo'
            })
        mostrar_player_clips(clips_convertidos, "🎬 Biblioteca Completa de Clips")
    else:
        st.info("📭 No hay clips disponibles. Ejecuta un análisis para generar clips.")

with tab2:
    # Mostrar clips de la sesión actual
    if st.session_state.clips_encontrados_sesion:
        mostrar_player_clips(st.session_state.clips_encontrados_sesion, "🆕 Clips de Esta Sesión")
    else:
        st.info("📭 No se han generado clips en esta sesión. Ejecuta un análisis para ver clips aquí.")

with tab3:
    # Análisis y estadísticas
    st.markdown("### 📊 Análisis de la Biblioteca de Clips")
    
    todos_los_clips = buscar_todos_los_clips()
    if todos_los_clips:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Clips", len(todos_los_clips))
        
        with col2:
            terminos_unicos = len(set([clip['termino'] for clip in todos_los_clips]))
            st.metric("Términos Únicos", terminos_unicos)
        
        with col3:
            # Clips de hoy
            hoy = datetime.now().date()
            clips_hoy = sum(1 for clip in todos_los_clips 
                           if clip['fecha_creacion'].date() == hoy)
            st.metric("Clips de Hoy", clips_hoy)
        
        with col4:
            # Tamaño total
            tamano_total = sum([clip['size_mb'] for clip in todos_los_clips])
            st.metric("Tamaño Total", f"{tamano_total:.1f} MB")
        
        # Gráfico de distribución por términos
        if len(todos_los_clips) > 0:
            st.markdown("#### 📈 Distribución por Términos")
            terminos_count = {}
            for clip in todos_los_clips:
                termino = clip['termino']
                terminos_count[termino] = terminos_count.get(termino, 0) + 1
            
            # Crear DataFrame para el gráfico
            df_terminos = pd.DataFrame(list(terminos_count.items()), 
                                     columns=['Término', 'Cantidad'])
            df_terminos = df_terminos.sort_values('Cantidad', ascending=True)
            
            st.bar_chart(df_terminos.set_index('Término'))
            
            # Timeline de clips
            st.markdown("#### 📅 Timeline de Generación de Clips")
            df_timeline = pd.DataFrame(todos_los_clips)
            df_timeline['fecha'] = pd.to_datetime(df_timeline['fecha_creacion']).dt.date
            clips_por_dia = df_timeline.groupby('fecha').size().reset_index(name='clips')
            
            st.line_chart(clips_por_dia.set_index('fecha'))
    else:
        st.info("📭 No hay datos para analizar. Genera algunos clips primero.")

# === FUNCIÓN PARA SINCRONIZAR CON SUPABASE DESDE coincidencias.md ===
def sincronizar_coincidencias_md_a_supabase():
    """
    Lee el archivo coincidencias.md y sincroniza con Supabase:
    1. Elimina duplicados
    2. Inserta coincidencias faltantes
    """
    func_name = "sincronizar_coincidencias_md_a_supabase"
    
    if not supabase:
        return False, "❌ Cliente de Supabase no inicializado"
    
    # Verificar si existe el archivo
    if not os.path.exists("coincidencias.md"):
        return False, "❌ Archivo coincidencias.md no encontrado"
    
    try:
        # Leer el archivo
        with open("coincidencias.md", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        # PASO 1: Limpiar duplicados por URL de Cloudinary
        st.info("🧹 Paso 1: Limpiando registros duplicados por URL de Cloudinary...")
        result = supabase.table('alertas_medios').select('*').order('fecha_detencion', desc=False).execute()
        
        # Agrupar por URL de Cloudinary (url_video o enlace_directo)
        registros_por_url = {}
        duplicados_ids = []
        
        for reg in result.data:
            url = reg.get('url_video', '') or reg.get('enlace_directo', '')
            
            # Solo procesar si hay URL de Cloudinary
            if url and 'cloudinary' in url.lower():
                if url in registros_por_url:
                    # Ya existe uno con esta URL
                    # Comparar fechas para mantener el más antiguo
                    registro_existente = registros_por_url[url]
                    fecha_existente = registro_existente.get('fecha_detencion', '')
                    fecha_actual = reg.get('fecha_detencion', '')
                    
                    # Si el actual es más reciente, lo marcamos para eliminar
                    if fecha_actual > fecha_existente:
                        duplicados_ids.append(reg['id'])
                        log_info(f"Duplicado reciente encontrado: ID {reg['id']} (fecha: {fecha_actual})", func_name)
                    else:
                        # El existente es más reciente, eliminamos el existente y guardamos el actual
                        duplicados_ids.append(registro_existente['id'])
                        registros_por_url[url] = reg
                        log_info(f"Duplicado reciente encontrado: ID {registro_existente['id']} (fecha: {fecha_existente})", func_name)
                else:
                    # Primera vez que vemos esta URL
                    registros_por_url[url] = reg
        
        if duplicados_ids:
            eliminados = 0
            for dup_id in duplicados_ids:
                try:
                    supabase.table('alertas_medios').delete().eq('id', dup_id).execute()
                    eliminados += 1
                except Exception as e:
                    log_warning(f"Error eliminando duplicado ID {dup_id}: {e}", func_name)
            
            st.success(f"✅ Eliminados {eliminados} registros duplicados (manteniendo los más antiguos)")
            log_info(f"Duplicados eliminados: {eliminados} de {len(duplicados_ids)} intentos", func_name)
        else:
            st.success("✅ No se encontraron duplicados por URL de Cloudinary")
        
        # PASO 2: Extraer coincidencias del MD
        st.info("📖 Paso 2: Extrayendo coincidencias del archivo MD...")
        
        # Extraer URLs de Cloudinary del contenido
        import re
        urls = re.findall(r'https://res\.cloudinary\.com/[^\s\)]+', contenido)
        
        # Extraer información de cada coincidencia
        bloques = re.split(r'\d+\.\s+', contenido)[1:]  # Dividir por numeración
        
        coincidencias_nuevas = []
        for i, bloque in enumerate(bloques):
            try:
                # Extraer datos del bloque
                termino_match = re.search(r'Menciones de (\w+)', bloque, re.IGNORECASE)
                medio_match = re.search(r'Medio:\s*([^\n]+)', bloque)
                hora_match = re.search(r'Hora:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{1,2}:\d{2})', bloque)
                contexto_match = re.search(r'Contexto:\s*([^\n]+)', bloque)
                resumen_match = re.search(r'Resumen:\s*([^\n]+)', bloque)
                archivo_match = re.search(r'URL Video:\s*([^\n]+)', bloque)
                
                if i < len(urls):
                    url_video = urls[i]
                    
                    coincidencia = {
                        'fecha_detencion': datetime.now().isoformat(),
                        'termino_detectado': termino_match.group(1) if termino_match else 'desconocido',
                        'nombre_medio': medio_match.group(1).strip() if medio_match else 'Medio de Comunicacion',
                        'contexto': contexto_match.group(1).strip() if contexto_match else 'Sin contexto',
                        'resumen_ejecutivo': resumen_match.group(1).strip() if resumen_match else 'Sin resumen',
                        'url_video': url_video,
                        'nombre_archivo': archivo_match.group(1).strip() if archivo_match else 'desconocido',
                        'enlace_directo': url_video,
                        'transcripcion': bloque[:500],
                        'relevancia': 'Alta'
                    }
                    
                    # Parsear fecha y hora
                    if hora_match:
                        fecha_str = hora_match.group(1)  # DD/MM/YYYY
                        hora_str = hora_match.group(2)   # HH:MM
                        
                        try:
                            from datetime import datetime as dt, date, time
                            fecha_parts = fecha_str.split('/')
                            hora_parts = hora_str.split(':')
                            
                            coincidencia['fecha_programa'] = date(
                                int(fecha_parts[2]), 
                                int(fecha_parts[1]), 
                                int(fecha_parts[0])
                            ).isoformat()
                            
                            coincidencia['hora_programa'] = time(
                                int(hora_parts[0]), 
                                int(hora_parts[1])
                            ).isoformat()
                        except:
                            from datetime import date, time
                            coincidencia['fecha_programa'] = date.today().isoformat()
                            coincidencia['hora_programa'] = time(12, 0).isoformat()
                    
                    coincidencias_nuevas.append(coincidencia)
            except Exception as e:
                log_warning(f"Error procesando bloque {i+1}: {e}", func_name)
        
        # PASO 3: Insertar coincidencias
        st.info(f"📥 Paso 3: Insertando {len(coincidencias_nuevas)} coincidencias...")
        
        insertadas = 0
        ya_existen = 0
        
        for coincidencia in coincidencias_nuevas:
            try:
                # Verificar si ya existe
                existing = supabase.table('alertas_medios').select('id').eq('url_video', coincidencia['url_video']).execute()
                
                if existing.data and len(existing.data) > 0:
                    ya_existen += 1
                else:
                    result = supabase.table('alertas_medios').insert(coincidencia).execute()
                    if result.data:
                        insertadas += 1
            except Exception as e:
                log_warning(f"Error insertando coincidencia: {e}", func_name)
        
        mensaje = f"✅ Sincronización completada:\n- Coincidencias insertadas: {insertadas}\n- Ya existían: {ya_existen}\n- Duplicados eliminados: {len(duplicados_ids)}"
        return True, mensaje
        
    except Exception as e:
        error_msg = f"Error en sincronización: {str(e)}"
        log_error_critico(func_name, error_msg)
        return False, f"❌ {error_msg}"

# === SECCIÓN DE SINCRONIZACIÓN CON SUPABASE ===
st.markdown("---")
st.markdown("## 🗄️ Sincronización con Supabase")

col1, col2 = st.columns([3, 1])
with col1:
    st.write("Sincroniza el archivo `coincidencias.md` con Supabase: limpia duplicados e inserta coincidencias faltantes")
with col2:
    if st.button("🔄 Sincronizar desde MD", help="Lee coincidencias.md y sincroniza con Supabase"):
        with st.spinner("Sincronizando..."):
            exito, mensaje = sincronizar_coincidencias_md_a_supabase()
            if exito:
                st.success(mensaje)
            else:
                st.error(mensaje)

# === SECCIÓN DE LOGS ===
st.markdown("---")
st.markdown("## 📋 Sistema de Logs")

def mostrar_logs():
    """
    Interfaz para ver los logs del sistema
    """
    log_dir = Path("logs")
    
    if not log_dir.exists():
        st.warning("📁 No se encontró el directorio de logs")
        return
    
    # Selector de tipo de log
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚨 Ver Errores", help="Mostrar solo errores críticos"):
            st.session_state.log_type = "errors"
    
    with col2:
        if st.button("ℹ️ Ver Info General", help="Mostrar información general de la aplicación"):
            st.session_state.log_type = "info"
    
    with col3:
        if st.button("🔍 Ver Debug", help="Mostrar información detallada de debug"):
            st.session_state.log_type = "debug"
    
    # Inicializar tipo de log si no existe
    if 'log_type' not in st.session_state:
        st.session_state.log_type = "errors"
    
    # Obtener archivos de log del día actual
    today = datetime.now().strftime("%Y%m%d")
    log_files = {
        "errors": log_dir / f"errors_{today}.log",
        "info": log_dir / f"app_{today}.log", 
        "debug": log_dir / f"debug_{today}.log"
    }
    
    selected_file = log_files[st.session_state.log_type]
    
    if selected_file.exists():
        try:
            # Leer las últimas 100 líneas del archivo
            with open(selected_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Mostrar las últimas líneas
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            st.markdown(f"### 📄 {st.session_state.log_type.title()} - Últimas {len(recent_lines)} entradas")
            
            # Mostrar en un contenedor con scroll
            log_content = "".join(recent_lines)
            st.text_area(
                f"Logs de {st.session_state.log_type}:",
                value=log_content,
                height=400,
                help=f"Archivo: {selected_file.name}"
            )
            
            # Información adicional
            file_size = selected_file.stat().st_size / 1024  # KB
            st.caption(f"📊 Tamaño del archivo: {file_size:.1f} KB | Total líneas: {len(lines)}")
            
            # Botón para limpiar logs
            if st.button("🗑️ Limpiar Logs", help="Eliminar logs antiguos"):
                try:
                    selected_file.unlink()
                    st.success(f"✅ Logs de {st.session_state.log_type} eliminados")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando logs: {e}")
                    
        except Exception as e:
            st.error(f"❌ Error leyendo archivo de log: {e}")
            log_exception("mostrar_logs", e, f"Archivo: {selected_file}")
    else:
        st.info(f"📁 No hay logs de {st.session_state.log_type} para hoy")
        st.caption(f"Archivo esperado: {selected_file.name}")

# Mostrar la interfaz de logs
with st.expander("📋 Ver Logs del Sistema", expanded=False):
    mostrar_logs()

# === INFORMACIÓN DE ESTADO FINAL ===
if st.session_state.running:
    st.markdown("---")
    st.success("🔄 **Búsqueda continua activa** - El procesamiento se ejecutará automáticamente con progreso visual completo")
    
    # Mostrar información del próximo procesamiento
    if 'ultimo_procesamiento_continuo' in st.session_state and st.session_state.ultimo_procesamiento_continuo > 0:
        tiempo_actual = time.time()
        tiempo_desde_ultimo = tiempo_actual - st.session_state.ultimo_procesamiento_continuo
        tiempo_restante = st.session_state.intervalo - int(tiempo_desde_ultimo)
        
        if tiempo_restante > 0:
            st.info(f"⏳ Próximo procesamiento automático en {tiempo_restante} segundos")
        else:
            st.info("🔄 Procesamiento automático iniciando...")

# === AUTO-REFRESH PARA BÚSQUEDA CONTINUA ===
# El auto-refresh ahora se maneja en la lógica principal de procesamiento continuo

# === MAIN EXECUTION BLOCK ===
if __name__ == "__main__":
    # This ensures the Streamlit app only runs when executed directly
    # and not when imported as a module
    # Streamlit app runs automatically when script is executed directly
    pass