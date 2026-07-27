# 🎥 Guía de Instalación - Generador de Videos con IA

## 📋 Requisitos del Sistema

### 1. Python 3.8 o superior
```bash
python --version  # Debe mostrar 3.8+
```

### 2. FFmpeg (OBLIGATORIO)
**Windows:**
1. Descargar desde: https://ffmpeg.org/download.html
2. Extraer a `C:\ffmpeg`
3. Agregar `C:\ffmpeg\bin` al PATH del sistema

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Verificar instalación:**
```bash
ffmpeg -version
```

### 3. API Key de Google Gemini
1. Ir a: https://aistudio.google.com/
2. Crear cuenta y obtener API key
3. Configurar variable de entorno:

**Windows:**
```cmd
set GEMINI_API_KEY=tu_api_key_aquí
```

**macOS/Linux:**
```bash
export GEMINI_API_KEY=tu_api_key_aquí
```

## 🚀 Instalación

### 1. Instalar dependencias
```bash
cd "C:\Users\Administrador\Desktop\grabaciones"
pip install -r requirements.txt
```

### 2. Verificar instalación
```bash
python -c "import customtkinter, google.genai, moviepy.editor; print('✅ Todo instalado correctamente')"
```

## 🎬 Uso del Programa

### 1. Ejecutar la aplicación
```bash
python makevid.py
```

### 2. Preparar materiales
- **1 foto del actor** (JPG/PNG, mínimo 1024x1024)
- **5 fotos del auto** (EXTERIOR únicamente, buena calidad)

### 3. Configurar en la interfaz
1. **Datos básicos**: Nombre del actor y modelo del auto
2. **Archivos**: Seleccionar foto del actor y 5 fotos del auto
3. **Textos**: Personalizar mensajes (opcional)
4. **Generar**: Hacer clic en "Generar Video (24s)"

## ⚠️ Solución de Problemas

### Error: "FFmpeg no está instalado"
- Instalar FFmpeg y agregarlo al PATH
- Reiniciar la terminal/aplicación

### Error: "API key no configurada"
- Verificar que GEMINI_API_KEY esté configurada
- Reiniciar la aplicación después de configurarla

### Error: "Imagen no válida"
- Usar formatos JPG, PNG, BMP, TIFF
- Verificar que las imágenes no estén corruptas
- Usar resolución mínima 512x512

### Error de memoria
- Usar imágenes de menor resolución (máximo 2048x2048)
- Cerrar otras aplicaciones que consuman memoria

### Video no se genera
- Verificar espacio en disco (mínimo 2GB libres)
- Revisar el archivo `makevid.log` para detalles

## 📊 Especificaciones del Video

- **Duración total**: 24 segundos
- **Formato**: MP4 (H.264 + AAC)
- **Resolución**: 1080x1920 (9:16 vertical)
- **FPS**: 24
- **Estructura**:
  1. Bienvenida (8s) - Video IA del actor
  2. Desarrollo (8s) - Slideshow de 5 fotos
  3. Despedida (8s) - Video IA con el auto

## 🎯 Consejos para Mejores Resultados

### Foto del actor:
- Fondo limpio y neutro
- Buena iluminación frontal
- Expresión natural y amigable
- Resolución mínima: 1024x1024

### Fotos del auto:
- SOLO EXTERIORES (no interior/cabina)
- Diferentes ángulos: frontal, lateral, trasero, detalles
- Buena calidad y resolución
- Iluminación uniforme
- Auto limpio y bien presentado

### Textos personalizados:
- Mensajes concisos y claros
- Mencionar el modelo específico
- Mantener tono profesional y amigable
- Evitar texto muy largo (máximo 2-3 oraciones)

## 📝 Archivos Generados

- **Video final**: `spot_modelo_24s_vertical.mp4`
- **Log de proceso**: `makevid.log`
- **Archivos temporales**: Se eliminan automáticamente

## 🆘 Soporte

Si encuentras problemas:
1. Revisar el archivo `makevid.log`
2. Verificar que todos los requisitos estén instalados
3. Probar con imágenes de prueba más pequeñas
4. Verificar conexión a internet (para API de Gemini)


