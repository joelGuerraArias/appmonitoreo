#!/usr/bin/env python
# -*- coding: utf-8 -*-

readme_content = """# 🧠 Analizador de Videos Pro - Sistema Inteligente de Detección

## 📋 DESCRIPCIÓN GENERAL

`transmistral2.py` es un analizador inteligente de videos/audios que automáticamente:
1. 🔍 Escanea carpetas buscando archivos multimedia
2. 🎤 Los transcribe usando IA (Whisper, Mistral, OpenAI)
3. 🔎 Busca términos específicos en las transcripciones
4. ✂️ Genera clips de video cuando encuentra coincidencias
5. 📤 Envía las coincidencias a múltiples destinos automáticamente

---

## 📤 DESTINOS DE ENVÍO

Cuando se detecta una coincidencia, el sistema envía datos a **6 destinos diferentes**:

### 1. 📱 TELEGRAM
- Resumen ejecutivo en texto
- Clip de video (subido a Cloudinary)
- Información del medio y hora
- Contexto de la coincidencia

**Funciones:** `enviar_mensaje_telegram()`, `enviar_video_telegram_inteligente()`, `enviar_clips_a_telegram()`

### 2. 🌐 WEBHOOK
Envía JSON con:
- Tipo de evento
- Archivo origen
- Término detectado
- Contexto
- Resumen ejecutivo
- Timestamp

**Funciones:** `enviar_clips_a_webhook()`, `enviar_a_webhook_individual()`

### 3. ☁️ GOOGLE DRIVE
- Clips de video generados (.mp4)
- Transcripciones completas (.txt)
- Archivos de coincidencias con resumen (.txt)

**Funciones:** `subir_archivo_google_drive()`, `enviar_clips_a_google_drive()`

### 4. 🗄️ SUPABASE (Base de datos)
Tabla: `alertas_medios`

Datos enviados:
- termino_detectado
- nombre_medio
- hora_programa / fecha_programa
- **url_video** (URL de Cloudinary del CLIP)
- nombre_archivo
- contexto
- resumen_ejecutivo
- transcripcion
- relevancia

⚠️ **IMPORTANTE:** Se envía la URL del CLIP, NO del video principal.

**Funciones:** `enviar_coincidencias_a_supabase()`

### 5. 📧 BREVO (Email)
- Email HTML con resumen ejecutivo
- Enlace al clip en Google Drive
- URL de Cloudinary del video
- Información del medio y términos detectados

**API Key:** `YOUR_BREVO_API_KEY`

**Funciones:** `enviar_correo_brevo()`, `crear_plantilla_email_html()`

### 6. ☁️ CLOUDINARY (Hosting de videos)
- Sube SOLO los clips de coincidencias (no el video principal)
- Genera URLs públicas para compartir
- Estas URLs se envían a Supabase, Telegram, Email

**Funciones:** `subir_video_cloudinary()`, `configurar_cloudinary()`

---

## 🔄 FLUJO DE TRABAJO

```
1. 🔍 ESCANEO
   └─> Busca: .mp4, .mp3, .wav, .mkv, .avi
   └─> Verifica si ya fueron procesados
   └─> Verifica si están en fallidos.txt ⭐

2. 🎤 TRANSCRIPCIÓN
   └─> Extrae audio con ffmpeg
   └─> Transcribe con Mistral/OpenAI/Faster-Whisper
   └─> Obtiene timestamps precisos

3. 🔍 BÚSQUEDA
   └─> Busca términos en transcripción
   └─> Identifica timestamps exactos
   └─> Extrae contexto (30s antes + 30s después)

4. ✂️ GENERACIÓN DE CLIPS
   └─> Corta clips con ffmpeg
   └─> Verifica que el clip contenga el término
   └─> Si no lo contiene, lo descarta

5. ☁️ SUBIDA A CLOUDINARY
   └─> Sube SOLO los clips (no video principal)
   └─> Obtiene URL pública del clip

6. 📤 ENVÍO INMEDIATO (en paralelo):
   ├─> 📱 Telegram: Resumen + clip
   ├─> 🌐 Webhook: JSON con datos
   ├─> ☁️ Google Drive: Clips + transcripciones
   ├─> 🗄️ Supabase: Registro en alertas_medios
   └─> 📧 Brevo: Email con resumen

7. 📊 RESUMEN FINAL
   └─> Muestra estadísticas de la sesión
   └─> Lista archivos procesados
   └─> Muestra archivos fallidos ⭐
```

---

## 🛠️ FUNCIONES PRINCIPALES (97 funciones)

### Categorías de Funciones:

**📹 Procesamiento de Video:**
- `buscar_y_procesar_videos()` - Función principal
- `obtener_duracion()` - Duración del video
- `extraer_info_medio_hora()` - Extrae info del nombre

**🎤 Transcripción:**
- `transcribir_audio_mistral()` - Transcribe con Mistral
- `transcribir_con_openai()` - Transcribe con OpenAI
- `transcribir_audio_hibrido()` - Múltiples servicios
- `obtener_timestamps_whisper()` - Timestamps precisos

**🤖 Resúmenes IA:**
- `generar_resumen_video()` - Resumen del video
- `generar_resumen_archivo()` - Resumen ejecutivo

**📤 Envíos:**
- `enviar_coincidencia_inmediata()` - FUNCIÓN CENTRAL de envío

**🌐 Webhooks:**
- `enviar_clips_a_webhook()`
- `enviar_a_webhook_individual()`

**📱 Telegram:**
- `enviar_mensaje_telegram()`
- `enviar_video_telegram_inteligente()`
- `enviar_clips_a_telegram()`

**☁️ Cloudinary:**
- `subir_video_cloudinary()`
- `configurar_cloudinary()`

**☁️ Google Drive:**
- `subir_archivo_google_drive()`
- `enviar_clips_a_google_drive()`

**🗄️ Supabase:**
- `enviar_coincidencias_a_supabase()`

**📧 Brevo:**
- `enviar_correo_brevo()`
- `crear_plantilla_email_html()`

**❌ Archivos Fallidos ⭐:**
- `cargar_archivos_fallidos()`
- `guardar_archivo_fallido()`
- `es_archivo_fallido()`
- `limpiar_archivos_fallidos()`
- `mostrar_archivos_fallidos()`

**🔍 Búsqueda y Escaneo:**
- `buscar_videos_nuevos_optimizado()`
- `escanear_carpeta_completa()`
- `cargar_cache_escaneo()`

**📊 Gestión de Clips:**
- `buscar_todos_los_clips()`
- `mostrar_player_clips()`
- `exportar_lista_clips()`
- `borrar_clips_antiguos()`

**🔧 Configuración:**
- `cargar_terminos_guardados()`
- `cargar_configuracion_completa()`
- `init_session_state()`

**🔍 Verificación:**
- `verificar_todas_las_apis()`
- `test_google_drive_connection()`
- `test_telegram_connection()`
- `test_brevo_connection()`

**📝 Logging:**
- `configurar_logging()`
- `log_info()`, `log_debug()`, `log_warning()`, `log_exception()`

---

## ⚠️ CARACTERÍSTICAS IMPORTANTES

### ✅ Sistema de Archivos Fallidos ⭐
- Si un archivo da error, se guarda en `fallidos.txt`
- En futuras rondas, se omite automáticamente
- Se puede limpiar desde la interfaz
- Formato: `archivo|timestamp|mensaje_error`

### ✅ Verificación de Clips
- Verifica que el clip contenga el término
- Si no lo contiene, lo descarta
- Solo envía clips verificados

### ✅ Envío Solo de Clips
- NO se sube el video principal a Cloudinary
- SOLO los clips se suben
- La URL del clip se envía a Supabase

### ✅ Caché de Escaneo
- Optimiza escaneo con caché
- Evita re-escanear archivos
- Se limpia automáticamente

### ✅ Configuración Persistente
- Se guarda en archivos JSON
- Se carga automáticamente

### ✅ Envío Inmediato
- Notificaciones en tiempo real
- No espera a terminar todo

### ✅ Resúmenes con IA
- Resúmenes profesionales
- Contexto y relevancia

---

## 📦 DEPENDENCIAS

```bash
streamlit
openai
mistralai
faster-whisper
pandas
supabase
cloudinary
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
requests
```

**Software externo:**
- FFmpeg
- FFprobe

---

## 🚀 INSTALACIÓN

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar FFmpeg (agregar al PATH)

# 3. Configurar APIs (crear archivos JSON)

# 4. Ejecutar
streamlit run transmistral2.py
```

---

## 📂 ESTRUCTURA DE ARCHIVOS

```
grabaciones/
├── transmistral2.py              # Aplicación principal
├── coincidencias_logger.py       # Sistema de logging
├── requirements.txt               # Dependencias
├── README.md                      # Este archivo
├── fallidos.txt                  # Archivos fallidos ⭐
├── archivos_procesados.json      # Archivos procesados
├── cache_escaneo.json            # Caché
├── webhook_config.json           # Config webhook
├── telegram_config.json          # Config Telegram
├── cloudinary_config.json        # Config Cloudinary
├── brevo_config.json             # Config Brevo
├── correos_guardados.json        # Lista correos
├── terminos_guardados.json       # Términos búsqueda
├── configuracion.json            # Config general
├── credentials.json              # Google Drive creds
├── token.json                   # OAuth token
├── logs/                        # Logs
│   ├── app_YYYYMMDD.log
│   ├── errors_YYYYMMDD.log
│   └── debug_YYYYMMDD.log
└── clips/                       # Clips generados
    └── TERMINO_*.mp4
```

---

## 🎯 CASOS DE USO

- **Monitoreo de Medios:** Detectar menciones en TV/radio
- **Análisis de Contenido:** Analizar volúmenes grandes
- **Alertas en Tiempo Real:** Notificaciones inmediatas
- **Archivo:** Documentación con clips y transcripciones

---

## 🎓 ARQUITECTURA HÍBRIDA

**Supabase:**
- Metadatos estructurados
- Info de usuarios
- Registros de actividad

**Pinecone:**
- Vectores de embeddings
- Búsqueda semántica
- Ranking de relevancia

**Flujo RAG:**
1. Usuario pregunta → 2. Embedding → 3. Pinecone busca → 4. Supabase metadatos → 5. LLM responde → 6. Guardar historial

---

## 🏆 MEJORES PRÁCTICAS

1. No subir vectores directamente a Supabase
2. Validar vectores (no NaN) antes de Pinecone
3. Usar sistema de fallidos
4. Verificar clips antes de enviar
5. Mantener logs actualizados

---

**Desarrollado con ❤️ por el equipo de Video Analyzer IA**

**Última actualización:** 30 de Septiembre de 2025
"""

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(readme_content)

print("✅ README.md creado exitosamente!")

