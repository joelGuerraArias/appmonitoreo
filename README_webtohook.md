# 📹 Sistema de Publicación Automática de Videos

Sistema web para procesar y publicar múltiples videos con títulos superpuestos, subida a Cloudinary y envío programado mediante webhooks.

## ✨ Características

- ✅ **Procesamiento por lotes**: Sube hasta 10 videos simultáneamente
- ✅ **Títulos automáticos con IA**: Usa GPT-4o-mini para generar títulos atractivos
- ✅ **Vista previa visual**: Visualiza cómo se verá el título antes de procesar
- ✅ **Validación de videos**: Verifica tamaño y formato automáticamente
- ✅ **Notificaciones Telegram**: Recibe alertas en tiempo real
- ✅ **Dos modos de publicación**: Inmediato o programado
- ✅ **Manejo robusto de errores**: Logs detallados y recuperación ante fallos
- ✅ **Seguridad mejorada**: Credenciales en archivo secrets separado

## 🚀 Instalación

### 1. Requisitos previos

```bash
# Instalar FFmpeg (Windows)
# Descarga desde: https://ffmpeg.org/download.html
# O usa Chocolatey:
choco install ffmpeg

# Instalar dependencias Python
pip install streamlit cloudinary requests pillow openai
```

### 2. Configurar credenciales

Crea el archivo `.streamlit/secrets.toml` (usa `.streamlit/secrets.toml.example` como plantilla):

```toml
[cloudinary]
cloud_name = "tu_cloud_name"
api_key = "tu_api_key"
api_secret = "tu_api_secret"

[webhook]
url = "https://hook.us1.make.com/tu_webhook_url"

[telegram]
bot_token = "tu_bot_token"
chat_id = "@tu_canal"

[openai]
api_key = "YOUR_OPENAI_API_KEY"
```

⚠️ **IMPORTANTE**: Nunca subas `secrets.toml` a Git. Está en `.gitignore` por defecto.

### 3. Ejecutar la aplicación

```bash
streamlit run webtohook.py
```

## 📖 Guía de Uso

### Paso 1: Configurar videos

1. Selecciona el número de videos a procesar (1-10)
2. Define la hora inicial de publicación
3. Para cada video:
   - Sube el archivo (MP4, MOV, AVI)
   - Escribe el caption (máx 2200 caracteres)
   - Genera el título con IA o escríbelo manualmente
   - Selecciona el hashtag predeterminado

### Paso 2: Generar títulos con IA

- Haz clic en "🎯 Generar título desde caption"
- El sistema usará GPT-4o-mini para crear un título profesional
- Verás una vista previa de cómo se verá en el video
- Puedes editarlo manualmente si lo deseas

### Paso 3: Seleccionar modo de publicación

**Modo Inmediato (todos a la vez)**
- Procesa y envía todos los videos inmediatamente
- Útil para publicación manual posterior

**Modo Programado (enviar horarios al webhook)**
- Envía al webhook la información de cuándo debe publicarse cada video
- El webhook/Make.com se encarga de publicar con intervalos de 1 hora
- Evita publicaciones nocturnas (00:00-06:00)

### Paso 4: Procesar

1. Haz clic en "🚀 Subir y procesar videos"
2. El sistema:
   - Valida cada video
   - Agrega el título superpuesto con FFmpeg
   - Sube a Cloudinary
   - Envía al webhook con horario programado
   - Notifica a Telegram
3. Ver resumen de éxitos/fallos al final

## 🔧 Mejoras Implementadas

### Seguridad
- ✅ Credenciales movidas a `st.secrets`
- ✅ Fallback a valores por defecto para desarrollo
- ✅ API keys no expuestas en código fuente

### Performance
- ✅ Eliminado `time.sleep()` que bloqueaba la UI
- ✅ Timeouts en subprocess (5 min FFmpeg, 10 min Cloudinary)
- ✅ Procesamiento inmediato sin esperas

### Confiabilidad
- ✅ Validación de videos (tamaño, formato)
- ✅ Manejo robusto de errores con try/catch
- ✅ Logging estructurado
- ✅ Limpieza automática de archivos temporales
- ✅ Resumen detallado de operaciones

### Calidad
- ✅ Actualizado a GPT-4o-mini (mejor precio/calidad)
- ✅ Timeout en llamadas OpenAI (15s)
- ✅ Docstrings en todas las funciones
- ✅ Mejora en escape de caracteres FFmpeg

## 📊 Estructura del Payload

El sistema envía al webhook un JSON con esta estructura:

```json
{
  "video_url": "https://res.cloudinary.com/...",
  "caption": "Texto del caption con hashtags",
  "title": "Título generado",
  "scheduled_time": "2025-10-16T14:00:00",
  "video_number": 1
}
```

El webhook debe usar `scheduled_time` para programar la publicación.

## 🐛 Solución de Problemas

### Error: "FFmpeg no encontrado"
```bash
# Verifica que FFmpeg esté en PATH
ffmpeg -version

# En Windows, agregar a PATH:
# Panel de Control > Sistema > Variables de entorno
```

### Error: "Video demasiado grande"
- Límite actual: 500MB por video
- Comprimir el video antes de subirlo

### Error: "Timeout procesando video"
- Videos muy largos o complejos pueden exceder el timeout de 5 minutos
- Reducir resolución o duración del video

### Notificaciones de Telegram no llegan
- Verifica que el bot tenga permisos en el canal
- Confirma que el `chat_id` sea correcto (con @ para canales públicos)

## 📝 Logs

Los logs se guardan en:
- **Console**: Nivel INFO con timestamps
- **Formato**: `YYYY-MM-DD HH:MM:SS - LEVEL - Mensaje`

## 🔐 Seguridad

- ✅ No incluir `secrets.toml` en Git
- ✅ Rotar API keys periódicamente
- ✅ Usar tokens con permisos mínimos necesarios
- ✅ Revisar logs para detectar intentos de acceso

## 📈 Roadmap Futuro

- [ ] Soporte para más formatos de video
- [ ] Preview del video procesado antes de subir
- [ ] Cola de procesamiento asíncrono
- [ ] Dashboard de estadísticas
- [ ] Integración con más plataformas sociales
- [ ] Sistema de plantillas de títulos

## 🤝 Contribuciones

Este sistema es parte del proyecto de análisis de videos. Para mejoras o reportes de bugs, contacta al equipo de desarrollo.

## 📄 Licencia

Uso interno exclusivo.







