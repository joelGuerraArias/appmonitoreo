import os
import sys
import glob
import subprocess
import json
import time
import re
import base64
from datetime import datetime, timedelta
from pathlib import Path
import threading
import shutil
import requests
import hashlib
from urllib.parse import urlencode

import streamlit as st
import openai
from mistralai import Mistral
from faster_whisper import WhisperModel
import pandas as pd

# Integración Cloudinary
import cloudinary
import cloudinary.uploader

# === CONFIGURA TU API KEY ===
openai_client = openai.OpenAI(api_key="YOUR_OPENAI_API_KEY")

mistral_api_key = "YOUR_MISTRAL_API_KEY"

# === ELIMINA DLLs de CUDA inválidas de Torch ===
torch_lib = os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")
for dll in glob.glob(os.path.join(torch_lib, "torch_cuda*.dll")):
    try:
        os.remove(dll)
    except OSError:
        pass

# === CONFIGURACIÓN ===
CARPETA_VIDEOS = r"C:\videograb"
PROCESADOS_LOG = os.path.join(CARPETA_VIDEOS, "procesados.log")
TERMINOS_CONFIG = os.path.join(CARPETA_VIDEOS, "terminos_guardados.json")
WEBHOOK_CONFIG = os.path.join(CARPETA_VIDEOS, "webhook_config.json")
TELEGRAM_CONFIG_FILE = os.path.join(CARPETA_VIDEOS, "telegram_config.json")
CLOUDINARY_CONFIG_FILE = os.path.join(CARPETA_VIDEOS, "cloudinary_config.json")
TAMANO_MINIMO_BYTES = 3 * 1024 * 1024  # 3 MB

# === FUNCIONES DE TELEGRAM Y CLOUDINARY ===
def cargar_config_telegram():
    """Carga configuración de Telegram"""
    default_config = {
        'enabled': False,
        'bot_token': '',
        'chat_id': '',
        'send_clips': True,
        'send_summary': True,
        'max_file_size_mb': 50
    }
    
    try:
        if os.path.exists(TELEGRAM_CONFIG_FILE):
            with open(TELEGRAM_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
    except Exception as e:
        st.warning(f"⚠️ Error cargando configuración Telegram: {e}")
    
    return default_config

def guardar_config_telegram(config):
    """Guarda configuración de Telegram"""
    try:
        with open(TELEGRAM_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración Telegram: {e}")
        return False

def cargar_config_cloudinary():
    """Carga configuración de Cloudinary"""
    default_config = {
        'enabled': False,
        'cloud_name': '',
        'api_key': '',
        'api_secret': '',
        'folder': 'video_clips'
    }
    
    try:
        if os.path.exists(CLOUDINARY_CONFIG_FILE):
            with open(CLOUDINARY_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
    except Exception as e:
        st.warning(f"⚠️ Error cargando configuración Cloudinary: {e}")
    
    return default_config

def guardar_config_cloudinary(config):
    """Guarda configuración de Cloudinary"""
    try:
        with open(CLOUDINARY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ Error guardando configuración Cloudinary: {e}")
        return False

def configurar_cloudinary():
    """Configura Cloudinary con las credenciales guardadas"""
    config = cargar_config_cloudinary()
    if config['enabled'] and all([config['cloud_name'], config['api_key'], config['api_secret']]):
        cloudinary.config(
            cloud_name=config['cloud_name'],
            api_key=config['api_key'],
            api_secret=config['api_secret'],
            secure=True
        )
        return True
    return False

def subir_video_cloudinary(video_path, folder="video_clips"):
    """Sube un video a Cloudinary y retorna la URL"""
    try:
        config = cargar_config_cloudinary()
        if not config['enabled']:
            return None, "Cloudinary no configurado"
        
        # Configurar Cloudinary
        if not configurar_cloudinary():
            return None, "Error configurando Cloudinary"
        
        # Subir el video
        timestamp = int(time.time())
        params = {
            "folder": folder,
            "timestamp": timestamp,
            "resource_type": "video"
        }
        
        # Generar firma
        params_string = urlencode(sorted(params.items()))
        to_sign = f"{params_string}{config['api_secret']}"
        signature = hashlib.sha1(to_sign.encode('utf-8')).hexdigest()
        
        # Subir archivo
        result = cloudinary.uploader.upload_large(
            video_path,
            resource_type='video',
            folder=folder,
            timestamp=timestamp,
            signature=signature
        )
        
        video_url = result.get('secure_url')
        return video_url, "✅ Subido exitosamente"
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def enviar_clip_telegram(clip_info, resumen, video_url_cloudinary=None):
    """Envía un clip específico a Telegram"""
    config_telegram = cargar_config_telegram()
    
    if not config_telegram['enabled'] or not config_telegram['bot_token'] or not config_telegram['chat_id']:
        return False, "Telegram no configurado"
    
    try:
        bot_token = config_telegram['bot_token']
        chat_id = config_telegram['chat_id']
        
        # Preparar mensaje
        mensaje = f"🎬 *Clip Detectado*\n\n"
        mensaje += f"🏷️ *Término:* {clip_info['termino']}\n"
        mensaje += f"⏱️ *Tiempo en video:* {clip_info['tiempo']}\n"
        mensaje += f"📹 *Video origen:* {clip_info.get('video_origen', 'Desconocido')}\n\n"
        
        if resumen:
            # Extraer solo los términos detectados del resumen
            if "**TÉRMINOS DETECTADOS:**" in resumen:
                lineas = resumen.split('\n')
                for linea in lineas:
                    if "TÉRMINOS DETECTADOS:" in linea:
                        mensaje += f"🔍 *{linea.replace('**', '')}*\n\n"
                        break
        
        mensaje += f"📝 *Contexto:*\n_{clip_info.get('contexto', 'No disponible')[:200]}_\n\n"
        
        # Si hay URL de Cloudinary, agregarla
        if video_url_cloudinary:
            mensaje += f"🔗 *Ver clip:* {video_url_cloudinary}\n"
        
        mensaje += f"\n⏰ _{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        # Enviar mensaje a Telegram
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        response = requests.post(telegram_url, data=data, timeout=10)
        
        if response.status_code == 200:
            return True, "✅ Enviado a Telegram"
        else:
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

def enviar_resumen_telegram(resumen, video_nombre, total_clips=0):
    """Envía un resumen del análisis a Telegram"""
    config_telegram = cargar_config_telegram()
    
    if not config_telegram['enabled']:
        return False, "Telegram deshabilitado"
    
    try:
        bot_token = config_telegram['bot_token']
        chat_id = config_telegram['chat_id']
        
        mensaje = f"📊 *Análisis Completado*\n\n"
        mensaje += f"📹 *Video:* {video_nombre}\n"
        mensaje += f"🎬 *Clips generados:* {total_clips}\n\n"
        mensaje += f"📝 *Resumen:*\n{resumen[:800]}\n\n"
        mensaje += f"⏰ _{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(telegram_url, data=data, timeout=10)
        return response.status_code == 200, f"HTTP {response.status_code}"
        
    except Exception as e:
        return False, str(e)

def enviar_clips_telegram_cloudinary(clips_generados, resumen, video_origen):
    """Sube clips a Cloudinary y envía links a Telegram"""
    config_telegram = cargar_config_telegram()
    config_cloudinary = cargar_config_cloudinary()
    
    if not config_telegram['enabled']:
        return False, "Telegram deshabilitado"
    
    if not config_cloudinary['enabled']:
        return False, "Cloudinary deshabilitado"
    
    clips_enviados = 0
    errores = []
    
    for clip in clips_generados:
        try:
            clip_path = clip.get('path', '')
            
            if os.path.exists(clip_path):
                # Verificar tamaño
                clip_size_mb = os.path.getsize(clip_path) / (1024*1024)
                
                if clip_size_mb <= config_telegram['max_file_size_mb']:
                    # Subir a Cloudinary
                    video_url, mensaje = subir_video_cloudinary(
                        clip_path, 
                        folder=f"clips/{datetime.now().strftime('%Y%m%d')}"
                    )
                    
                    if video_url:
                        # Enviar a Telegram con el link de Cloudinary
                        exito, msg = enviar_clip_telegram(clip, resumen, video_url)
                        if exito:
                            clips_enviados += 1
                        else:
                            errores.append(f"Telegram: {msg}")
                    else:
                        errores.append(f"Cloudinary: {mensaje}")
                else:
                    # Clip muy grande, enviar solo notificación
                    exito, msg = enviar_clip_telegram(clip, resumen, None)
                    if exito:
                        clips_enviados += 1
                    
        except Exception as e:
            errores.append(str(e)[:100])
    
    if clips_enviados > 0:
        # Enviar resumen final
        enviar_resumen_telegram(resumen, video_origen, len(clips_generados))
        
        if errores:
            return True, f"✅ {clips_enviados} clips enviados (con {len(errores)} errores)"
        else:
            return True, f"✅ {clips_enviados} clips enviados exitosamente"
    else:
        return False, f"❌ No se pudieron enviar clips: {', '.join(errores)}"
    
    # === FUNCIONES DE WEBHOOK ===
def cargar_webhook_config():
    """Carga configuración del webhook"""
    default_config = {
        'enabled': False,
        'url': '',
        'method': 'POST',
        'headers': {
            'Content-Type': 'application/json'
        },
        'send_video': True,
        'send_clips': True,
        'max_file_size_mb': 50,
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
    """Envía clips específicos donde se encontraron coincidencias + resumen"""
    config = cargar_webhook_config()
    
    if not config['enabled'] or not config['url']:
        return False, "Webhook no configurado o deshabilitado"
    
    try:
        # Datos básicos
        data = {
            'timestamp': datetime.now().isoformat(),
            'video_origen': video_origen,
            'terminos_detectados': terminos_detectados,
            'resumen': resumen,
            'clips_enviados': []
        }
        
        # Enviar cada clip donde se encontró una coincidencia
        for clip in clips_generados:
            clip_path = clip.get('path', '')
            
            if os.path.exists(clip_path):
                clip_size_mb = os.path.getsize(clip_path) / (1024*1024)
                
                # Verificar que el clip no sea muy grande
                if clip_size_mb <= config['max_file_size_mb']:
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
                        
                        data['clips_enviados'].append(clip_data)
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
                    data['clips_enviados'].append(clip_data)
        
        # Agregar resumen de lo enviado
        data['total_clips'] = len(clips_generados)
        data['clips_con_video'] = len([c for c in data['clips_enviados'] if c.get('video_base64')])
        
        # Enviar al webhook
        response = requests.post(
            config['url'], 
            json=data, 
            headers=config.get('headers', {}), 
            timeout=config.get('timeout', 30)
        )
        
        if response.status_code == 200:
            clips_enviados = data['clips_con_video']
            return True, f"✅ Enviados {clips_enviados} clips al webhook"
        else:
            return False, f"❌ Error HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "⏰ Timeout del webhook"
    except requests.exceptions.ConnectionError:
        return False, "🔌 Error de conexión"
    except Exception as e:
        return False, f"❌ Error: {str(e)[:100]}"

def webhook_notification_simple(video_path, resumen, terminos):
    """Notificación simple sin archivos grandes"""
    config = cargar_webhook_config()
    
    if not config['enabled'] or not config['url']:
        return False, "Webhook no configurado"
    
    try:
        # Datos básicos para notificación rápida
        data = {
            'evento': 'video_analizado',
            'timestamp': datetime.now().isoformat(),
            'video': os.path.basename(video_path),
            'terminos': terminos,
            'resumen': resumen[:500],  # Resumen truncado
            'servidor': 'analizador_videos_ia'
        }
        
        response = requests.post(config['url'], json=data, timeout=10)
        return response.status_code == 200, f"HTTP {response.status_code}"
        
    except Exception as e:
        return False, str(e)

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
        'duracion_clip': 30,
        'buffer_anterior': 15,
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

def guardar_configuracion_completa(terminos, intervalo=60, duracion_clip=30, buffer_anterior=15, mostrar_coincidencias=True):
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
        'duracion_clip': config_guardada['duracion_clip'],
        'buffer_anterior': config_guardada['buffer_anterior']
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Mostrar mensaje si se cargaron términos automáticamente
if st.session_state.terminos_continuos:
    st.success(f"✅ Se cargaron automáticamente {len(st.session_state.terminos_continuos)} términos guardados: {', '.join(st.session_state.terminos_continuos[:3])}{'...' if len(st.session_state.terminos_continuos) > 3 else ''}")

# === SETUP STREAMLIT ===
st.set_page_config(page_title="🧠 Analizador de Videos Pro", layout="wide")
st.title("🎬 Análisis Automático de Videos - Versión Completa")
st.markdown(f"📁 Carpeta: `{CARPETA_VIDEOS}`")