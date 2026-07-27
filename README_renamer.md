# 🎬 Renombrador de Videos por Programación

Una aplicación GUI moderna para renombrar automáticamente archivos de video según la programación televisiva.

## 📋 Características

- **Interfaz moderna** con CustomTkinter (tema oscuro)
- **Soporte multi-canal**: CDN37, TELECENTRO, TELEMICRO, COLOR VISION
- **Detección automática** de carpetas con videos
- **Programación específica** por canal de TV
- **Procesamiento por lotes** con selección múltiple
- **Renombrado inteligente** basado en fecha/hora del archivo
- **Prevención de duplicados** automática
- **Log en tiempo real** del proceso

## 🚀 Instalación

### Requisitos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Instalar dependencias
```bash
pip install -r requirements.txt
```

O instalar manualmente:
```bash
pip install customtkinter
```

## 📖 Uso

1. **Ejecutar la aplicación**:
   ```bash
   python renamer.py
   ```

2. **Seleccionar carpeta base** que contiene subcarpetas de videos

3. **Revisar carpetas detectadas** - la app detecta automáticamente:
   - Carpetas con archivos de video
   - Tipo de canal (CDN37, TELECENTRO, etc.)
   - Cantidad de videos por carpeta

4. **Seleccionar carpetas** a procesar (todas seleccionadas por defecto)

5. **Ejecutar renombrado** - el proceso:
   - Busca/crea archivo `programacion.json` específico por canal
   - Extrae fecha/hora del nombre original del video
   - Busca el programa correspondiente en la programación
   - Renombra con formato: `CANAL - PROGRAMA - FECHA - HORA.ext`

## 📁 Estructura de Archivos

```
carpeta_base/
├── CDN37_videos/
│   ├── programacion.json
│   ├── video_2024-01-15_14-30-00.mp4
│   └── video_2024-01-15_15-45-00.mp4
├── TELECENTRO_videos/
│   ├── programacion.json
│   └── video_2024-01-15_12-00-00.mp4
└── ...
```

## 🎯 Formato de Programación

Cada carpeta debe tener un archivo `programacion.json`:

```json
[
    {
        "hora_inicio": "12:00 PM",
        "nombre": "Noticias al Mediodía"
    },
    {
        "hora_inicio": "1:00 PM", 
        "nombre": "Magazine Vespertino"
    }
]
```

## 📺 Canales Soportados

### CDN37
- Programación oficial completa (24 horas)
- Incluye: Enfoque Final, Tú Opinas, Noticias CDN, etc.

### TELECENTRO
- Programación base de referencia
- Incluye: Buenos Días, Noticias, programas vespertinos

### TELEMICRO
- Programación oficial Univisión
- Incluye: Despierta América, novelas, noticieros

### COLOR VISION y Otros
- Programación genérica adaptable
- Se puede personalizar por canal

## 🔧 Formatos de Video Soportados

- MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V

## 📝 Formato de Salida

```
CANAL - PROGRAMA - FECHA - HORA.ext
```

Ejemplo:
```
CDN37 - TÚ OPINAS EN CDN - 15 de enero de 2024 - 15:30:00.mp4
```

## 🛠️ Funcionalidades Avanzadas

- **Detección automática** de tipo de canal
- **Prevención de duplicados** (agrega numeración)
- **Procesamiento en hilos** (UI no se bloquea)
- **Log detallado** con estadísticas
- **Manejo de errores** robusto

## 🐛 Solución de Problemas

### Error: "CustomTkinter no está instalado"
```bash
pip install customtkinter
```

### No se detectan carpetas con videos
- Verificar que las carpetas contengan archivos de video
- Formatos soportados: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V

### Error al extraer fecha/hora
- El nombre del archivo debe contener patrón: `YYYY-MM-DD_HH-MM-SS`
- Ejemplo válido: `video_2024-01-15_14-30-00.mp4`

### Archivo programacion.json no encontrado
- La app crea automáticamente uno específico por canal
- Se puede editar manualmente para personalizar

## 📊 Estadísticas

La aplicación muestra:
- Total de archivos procesados
- Número de errores
- Porcentaje de éxito
- Log detallado por archivo

## 🔄 Actualizaciones

Para obtener la versión más reciente:
1. Descargar el archivo `renamer.py` actualizado
2. Verificar que las dependencias estén actualizadas:
   ```bash
   pip install --upgrade customtkinter
   ```

## 📞 Soporte

Si encuentras problemas:
1. Revisa el log de la aplicación
2. Verifica el formato de nombres de archivos
3. Comprueba que el archivo `programacion.json` sea válido
