import streamlit as st
import cloudinary
import cloudinary.uploader
import requests
import tempfile
import subprocess
import os
from datetime import datetime, timedelta
import time
import re
import openai
from PIL import Image, ImageDraw, ImageFont
import hashlib
from urllib.parse import urlencode
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuraciones generales usando st.secrets con fallback
try:
    CLOUDINARY_CLOUD_NAME = st.secrets.get("cloudinary", {}).get("cloud_name", "dhzxzbkmc")
    CLOUDINARY_API_KEY = st.secrets.get("cloudinary", {}).get("api_key", "149663287387673")
    CLOUDINARY_API_SECRET = st.secrets.get("cloudinary", {}).get("api_secret", "YOUR_CLOUDINARY_API_SECRET")
    WEBHOOK_URL = st.secrets.get("webhook", {}).get("url", "https://hook.us1.make.com/1nk48toiy2c64f9966yue8bwhzqnosny")
    TELEGRAM_BOT_TOKEN = st.secrets.get("telegram", {}).get("bot_token", "YOUR_TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = st.secrets.get("telegram", {}).get("chat_id", "@donfelixvictorino")
    OPENAI_API_KEY = st.secrets.get("openai", {}).get("api_key", "YOUR_OPENAI_API_KEY")
except Exception as e:
    logger.warning(f"No se pudieron cargar secrets, usando valores por defecto: {e}")
    CLOUDINARY_CLOUD_NAME = "dhzxzbkmc"
    CLOUDINARY_API_KEY = "149663287387673"
    CLOUDINARY_API_SECRET = "YOUR_CLOUDINARY_API_SECRET"
    WEBHOOK_URL = "https://hook.us1.make.com/1nk48toiy2c64f9966yue8bwhzqnosny"
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID = "@donfelixvictorino"
    OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"

# Configurar Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# Funciones auxiliares

def clean_title(titulo):
    """Limpia el título removiendo caracteres repetidos y corrigiendo espacios."""
    if not titulo:
        return ""
    titulo = re.sub(r"([a-zA-Z])\1{2,}", r"\1", titulo)
    titulo = re.sub(r':(?!\s)', ': ', titulo)
    return titulo.strip()

def generar_titulo_desde_caption(caption):
    """Genera un título básico desde el caption (primeros 100 caracteres)."""
    if not caption or not caption.strip():
        return ""
    caption = re.sub(r'\s+', ' ', caption.strip())
    return clean_title(caption[:caption.rfind(' ', 0, 100)] if ' ' in caption[:100] else caption[:100])

def generar_titulo_con_openai_desde_caption(caption, api_key):
    """
    Genera un título profesional usando OpenAI GPT-4o-mini.
    Fallback a generación básica si falla.
    """
    if not caption or not caption.strip():
        return ""
    
    try:
        openai.api_key = api_key
        prompt = f"""
        Actúa como un experto en redacción de titulares periodísticos. A partir del siguiente caption, genera un título breve (máximo 100 caracteres), informativo y atractivo para redes sociales.
        No uses hashtags, emojis, ni repitas el caption. Agrega espacios después de signos de puntuación si hace falta.

        Caption: "{caption}"
        """
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un experto en crear títulos breves, claros y periodísticos para videos de noticias."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7,
            timeout=15
        )
        titulo_generado = response.choices[0].message.content.strip()
        logger.info(f"Título generado con OpenAI: {titulo_generado}")
        return clean_title(titulo_generado[:100])
    except Exception as e:
        logger.warning(f"Error generando título con OpenAI: {e}")
        st.warning(f"⚠️ No se pudo generar el título con OpenAI: {e}")
        return generar_titulo_desde_caption(caption)

def dividir_titulo(titulo, max_largo=50):
    """Divide títulos largos en dos líneas balanceadas."""
    if not titulo or len(titulo) <= max_largo:
        return titulo
    palabras = titulo.split()
    if len(palabras) == 1:
        return titulo
    total_chars = len(titulo)
    mejor_corte = 0
    menor_diferencia = float('inf')
    acumulado = 0
    for i, palabra in enumerate(palabras[:-1]):
        acumulado += len(palabra) + 1
        diferencia = abs(acumulado - total_chars / 2)
        if diferencia < menor_diferencia:
            menor_diferencia = diferencia
            mejor_corte = i + 1
    linea1 = " ".join(palabras[:mejor_corte])
    linea2 = " ".join(palabras[mejor_corte:])
    return f"{linea1}\n{linea2}"

def escape_ffmpeg_text(text):
    """Escapa caracteres especiales para FFmpeg drawtext filter."""
    if not text:
        return ""
    text = text.strip()
    text = text.replace('\\', '\\\\')
    text = text.replace(':', '\\:')
    text = text.replace("'", "\\'")
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '')
    # Mantener caracteres alfanuméricos, espacios, puntuación y acentos
    text = re.sub(r'[^\w\s\-.,!?áéíóúüñÁÉÍÓÚÜÑ\\:]', '', text)
    return text

def validar_video(video_file):
    """
    Valida que el archivo de video sea procesable.
    Retorna (True, "") si es válido, (False, mensaje_error) si no.
    """
    if not video_file:
        return False, "No se proporcionó archivo de video"
    
    # Validar tamaño (max 500MB)
    max_size = 500 * 1024 * 1024  # 500 MB
    video_file.seek(0, 2)  # Ir al final
    size = video_file.tell()
    video_file.seek(0)  # Volver al inicio
    
    if size > max_size:
        return False, f"El video excede el tamaño máximo de 500MB (tamaño: {size / (1024*1024):.1f}MB)"
    
    if size < 1024:  # Menos de 1KB
        return False, "El archivo parece estar vacío o corrupto"
    
    return True, ""

def mostrar_preview_titulo(titulo):
    """Muestra una vista previa visual del título como aparecerá en el video."""
    try:
        ancho, alto = 720, 128
        img = Image.new('RGB', (ancho, alto), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except:
            font = ImageFont.load_default()
        lines = titulo.split("\n")
        y = (alto - (len(lines) * 40)) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.rectangle([(ancho / 2 - w / 2 - 12, y - 6), (ancho / 2 + w / 2 + 12, y + 32)], fill=(0, 0, 0))
            draw.text(((ancho - w) / 2, y), line, font=font, fill=(255, 255, 255))
            y += 40
        st.image(img, caption="🖼️ Vista previa del título renderizado")
    except Exception as e:
        logger.error(f"Error generando preview: {e}")
        st.warning(f"⚠️ No se pudo generar la vista previa: {e}")

def limpiar_archivo_temporal(filepath):
    """Elimina un archivo temporal de forma segura."""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
            logger.info(f"Archivo temporal eliminado: {filepath}")
    except Exception as e:
        logger.warning(f"No se pudo eliminar archivo temporal {filepath}: {e}")

# Interfaz Streamlit
st.set_page_config(page_title="Batch de videos cada hora", layout="centered")
st.title("📆 Subir múltiples videos y publicarlos cada 1 hora automáticamente")

usar_openai = st.sidebar.checkbox("Usar OpenAI para generar títulos desde caption", value=True)
st.sidebar.info("OpenAI ayudará a generar títulos atractivos a partir del caption")

num_videos = st.number_input("¿Cuántos videos quieres subir?", min_value=1, max_value=10, step=1)
videos = []

start_hour = st.time_input("🕒 Hora inicial de publicación", value=datetime.now().time())

for i in range(num_videos):
    st.subheader(f"🎬 Video #{i+1}")
    video_file = st.file_uploader(f"Selecciona el video #{i+1}", type=["mp4", "mov", "avi"], key=f"video_{i}")
    caption = st.text_area(f"Caption para el video #{i+1}", max_chars=2200, key=f"caption_{i}")

    title_key = f"title_{i}"
    session_title_key = f"generated_{title_key}"

    if session_title_key not in st.session_state:
        st.session_state[session_title_key] = ""

    st.text_input(f"Título para el video #{i+1} (opcional)",
                  value=st.session_state[session_title_key], key=f"input_{title_key}")

    if st.button("🎯 Generar título desde caption", key=f"generate_button_{i}"):
        if caption.strip():
            with st.spinner("🧠 Generando título..."):
                nuevo_titulo = (
                    generar_titulo_con_openai_desde_caption(caption, OPENAI_API_KEY)
                    if usar_openai else generar_titulo_desde_caption(caption)
                )
                st.session_state[session_title_key] = nuevo_titulo
                st.success("✅ Título generado con éxito")
                mostrar_preview_titulo(nuevo_titulo)
        else:
            st.warning("⚠️ Escribe un caption primero para generar un título.")

    char_count = len(st.session_state[session_title_key].strip())
    st.caption(f"🔤 {char_count}/100 caracteres")
    if char_count > 100:
        st.warning("⚠️ El título excede los 100 caracteres recomendados.")

    hashtag = st.selectbox(f"Hashtag predeterminado para el video #{i+1}", options=["#fvdigital", "#formula1rd"], index=0, key=f"hashtag_{i}")

    if video_file and caption:
        title_input_field_key = f"input_{title_key}"
        if title_input_field_key in st.session_state:
            title_raw = st.session_state[title_input_field_key].strip()
        else:
            title_raw = st.session_state.get(session_title_key, "").strip()

        title = clean_title(title_raw)
        videos.append((video_file, f"{caption}\n\n{hashtag}", title))

modo_publicacion = st.radio(
    "Modo de publicación:",
    ["Inmediato (todos a la vez)", "Programado (enviar horarios al webhook)"],
    help="Modo inmediato: procesa todos los videos ahora. Modo programado: envía al webhook con horarios para que publique gradualmente."
)

if st.button("🚀 Subir y procesar videos"):
    if not videos:
        st.warning("Debes subir al menos un video con caption.")
    else:
        now = datetime.now().replace(second=0, microsecond=0)
        start_time = now.replace(hour=start_hour.hour, minute=start_hour.minute)
        
        if modo_publicacion == "Inmediato (todos a la vez)":
            st.success(f"Iniciando procesamiento inmediato de {len(videos)} videos")
        else:
            st.success(f"Iniciando batch de {len(videos)} videos desde las {start_time.strftime('%H:%M')}")

        videos_exitosos = 0
        videos_fallidos = 0

        for idx, (video_file, caption, title) in enumerate(videos):
            # Calcular hora programada
            scheduled_time = start_time + timedelta(hours=idx)
            if 0 <= scheduled_time.hour < 6:
                scheduled_time = scheduled_time.replace(hour=6, minute=0)
                if scheduled_time < datetime.now():
                    scheduled_time += timedelta(days=1)

            st.info(f"⏳ Procesando video #{idx+1} de {len(videos)} - Hora programada: {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            
            # Validar video
            video_file.seek(0)  # Resetear posición
            es_valido, mensaje_error = validar_video(video_file)
            if not es_valido:
                st.error(f"❌ Video #{idx+1} inválido: {mensaje_error}")
                videos_fallidos += 1
                continue

            input_path = None
            output_path = None

            try:
                # Guardar video temporal
                with st.spinner("🎞️ Procesando video con FFmpeg..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
                        video_file.seek(0)
                        tmp_input.write(video_file.read())
                        input_path = tmp_input.name

                    output_path = input_path.replace(".mp4", "_titled.mp4")

                    titulo_final = dividir_titulo(title) if title else ""
                    titulo_ffmpeg = escape_ffmpeg_text(titulo_final)

                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-i", input_path,
                        "-vf", f"drawtext=text='{titulo_ffmpeg}':fontcolor=white:fontsize=18:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=h-(text_h*1.2)-30",
                        "-c:a", "copy", output_path
                    ]

                    logger.info(f"Ejecutando FFmpeg para video #{idx+1}")
                    process = subprocess.run(
                        ffmpeg_cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        timeout=300  # Timeout de 5 minutos
                    )
                    
                    if process.returncode != 0:
                        error_msg = process.stderr.decode('utf-8', errors='ignore')
                        logger.error(f"Error FFmpeg video #{idx+1}: {error_msg}")
                        st.error(f"❌ Error procesando video #{idx+1}. Verifica que FFmpeg esté instalado.")
                        videos_fallidos += 1
                        continue

                # Subir a Cloudinary
                with st.spinner("☁️ Subiendo a Cloudinary..."):
                    try:
                        logger.info(f"Subiendo video #{idx+1} a Cloudinary")
                        result = cloudinary.uploader.upload_large(
                            output_path, 
                            resource_type='video', 
                            folder="webhook_batch",
                            timeout=600  # 10 minutos timeout
                        )
                        video_url = result.get('secure_url')
                        logger.info(f"Video #{idx+1} subido: {video_url}")
                    except Exception as e:
                        logger.error(f"Error subiendo video #{idx+1} a Cloudinary: {e}")
                        st.error(f"❌ Error subiendo video #{idx+1} a Cloudinary: {e}")
                        videos_fallidos += 1
                        continue

                # Enviar al webhook
                payload = {
                    "video_url": video_url, 
                    "caption": caption, 
                    "title": title,
                    "scheduled_time": scheduled_time.isoformat(),
                    "video_number": idx + 1
                }
                
                st.subheader(f"📦 Payload para video #{idx+1}:")
                st.json(payload)

                try:
                    logger.info(f"Enviando video #{idx+1} al webhook")
                    response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        st.success(f"✅ Video #{idx+1} enviado con éxito al webhook")
                        videos_exitosos += 1
                        
                        # Notificar a Telegram
                        telegram_message = (
                            f"📹 *Video #{idx+1} procesado exitosamente*\n\n"
                            f"*Título:* {title}\n"
                            f"*Programado para:* {scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"
                            f"*Link:* {video_url}\n"
                            f"*Caption:* {caption[:100]}..."
                        )
                        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        telegram_data = {
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": telegram_message, 
                            "parse_mode": "Markdown"
                        }
                        
                        try:
                            telegram_response = requests.post(telegram_url, data=telegram_data, timeout=10)
                            if telegram_response.status_code == 200:
                                st.info("📬 Notificación enviada a Telegram")
                            else:
                                logger.warning(f"Error en respuesta de Telegram: {telegram_response.status_code}")
                        except Exception as tel_error:
                            logger.warning(f"Error enviando a Telegram: {tel_error}")
                    else:
                        logger.error(f"Error webhook video #{idx+1}: {response.status_code} - {response.text}")
                        st.error(f"❌ Fallo al enviar video #{idx+1} al webhook (código {response.status_code})")
                        videos_fallidos += 1
                        
                except Exception as e:
                    logger.error(f"Error enviando video #{idx+1} al webhook: {e}")
                    st.error(f"❌ Error enviando video #{idx+1}: {e}")
                    videos_fallidos += 1

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout procesando video #{idx+1}")
                st.error(f"❌ Timeout procesando video #{idx+1}. El video puede ser demasiado grande o complejo.")
                videos_fallidos += 1
                
            except Exception as e:
                logger.error(f"Error inesperado procesando video #{idx+1}: {e}")
                st.error(f"❌ Error inesperado con video #{idx+1}: {e}")
                videos_fallidos += 1
                
            finally:
                # Limpiar archivos temporales
                limpiar_archivo_temporal(input_path)
                limpiar_archivo_temporal(output_path)
        
        # Resumen final
        st.markdown("---")
        st.subheader("📊 Resumen del procesamiento")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", len(videos))
        with col2:
            st.metric("✅ Exitosos", videos_exitosos)
        with col3:
            st.metric("❌ Fallidos", videos_fallidos)
        
        if videos_exitosos == len(videos):
            st.balloons()
            st.success("🎉 ¡Todos los videos fueron procesados exitosamente!")
        elif videos_exitosos > 0:
            st.info(f"✅ Se procesaron {videos_exitosos} de {len(videos)} videos.")
        else:
            st.error("❌ No se pudo procesar ningún video. Revisa los errores arriba.")
