# 📊 Monitor @EdesurRD Pro Dashboard

Un dashboard avanzado de monitoreo en tiempo real para menciones de @EdesurRD en Twitter/X, con análisis de sentimientos, métricas de engagement y visualizaciones interactivas.

![Dashboard](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Twitter API](https://img.shields.io/badge/Twitter%20API-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)

## 🚀 Características Principales

### 📈 Análisis en Tiempo Real
- **Recolección automática** de menciones desde Twitter API
- **Múltiples términos de búsqueda**: @EdesurRD, EdesurRD, Edesur, "sin luz República Dominicana", "apagón RD"
- **Actualización automática** cada 5 minutos (opcional)
- **Filtrado inteligente** de duplicados

### 🎭 Análisis de Sentimientos
- **Clasificación automática** en Positivo, Negativo y Neutral
- **Diccionario especializado** para el sector eléctrico dominicano
- **Indicadores visuales** con emojis y colores
- **Distribución porcentual** de opiniones

### 💫 Métricas de Engagement
- **Likes, Retweets, Replies** por tweet
- **Views/Vistas** cuando están disponibles
- **Engagement total** calculado automáticamente
- **Clasificación** de engagement (Alto >50, Medio 10-50, Bajo <10)

### 📊 Análisis de Alcance
- **Alcance estimado** basado en seguidores
- **Engagement rate** calculado
- **Contenido viral** identificado (>100 interacciones)
- **Top usuarios** por engagement

### 📱 Interfaz Moderna
- **Diseño responsive** con CSS personalizado
- **Cards interactivas** con efectos hover
- **Gradientes y animaciones** profesionales
- **Tipografía Inter** para mejor legibilidad

## 🛠️ Instalación y Configuración

### Requisitos Previos
```bash
pip install streamlit pandas requests plotly
```

### Configuración de API
1. **Obtener API Key de RapidAPI**:
   - Registrarse en [RapidAPI](https://rapidapi.com/)
   - Suscribirse a "Twitter API v2"
   - Copiar tu API Key

2. **Configurar credenciales** en `scrapeboard2.py`:
```python
RAPIDAPI_KEY = "tu_api_key_aqui"
RAPIDAPI_HOST = "twitter-api47.p.rapidapi.com"
```

### Ejecución
```bash
streamlit run scrapeboard2.py
```

El dashboard estará disponible en: `http://localhost:8501`

## 📋 Estructura del Dashboard

### 1. 🎛️ Panel de Control (Sidebar)
- **Estado de conexión** API
- **Botón de actualización** manual
- **Configuraciones**:
  - Auto-refresh (5 minutos)
  - Mostrar estadísticas
  - Mostrar métricas de engagement
  - Mostrar análisis de alcance
  - Número de tweets a mostrar (5-100)

### 2. 🔍 Filtros Avanzados
- **Por sentimiento**: Todos, Positivo, Negativo, Neutral
- **Por engagement**: Todos, Alto (>50), Medio (10-50), Bajo (<10)

### 3. 📋 Resumen Ejecutivo
#### Métricas Principales (4 columnas):
- **Estado General**: Indicador visual del sentimiento global
- **Total Menciones** y Usuarios Únicos
- **Total Engagement** y Vistas
- **Breakdown de Engagement** (Likes, RTs, Replies)

#### Distribución de Opiniones (3 columnas):
- **😊 A Favor**: Menciones positivas
- **😞 En Contra**: Menciones negativas  
- **😐 Neutral**: Menciones neutrales

### 4. 📈 Análisis de Alcance y Impacto
- **Alcance Estimado**: Rango conservador-optimista
- **Engagement Rate**: Porcentaje de interacciones
- **Contenido Viral**: Tweets con alta interacción

### 5. 📊 Análisis Visual
- **Gráfico de torta**: Distribución de sentimientos
- **Gráfico de barras**: Top usuarios por engagement
- **Timeline**: Engagement por tiempo (scatter plot)

### 6. 📱 Menciones Individuales
Para cada tweet se muestra:
- **Header**: Usuario, verificación, nivel de engagement
- **Contenido**: Texto completo del tweet
- **Metadatos**: Fecha, seguidores del usuario
- **Métricas**: Sentimiento, likes, RTs, replies, views, total
- **Link directo** al tweet original

### 7. 💫 Estadísticas de Engagement
- **Engagement Promedio** y Máximo
- **Promedio de Seguidores**
- **Usuarios Verificados** (cantidad y porcentaje)

## 🎯 Estados del Sistema

### 🟢 EXCELENTE (>60% positivo)
- La mayoría de usuarios están satisfechos
- Color verde en indicadores

### 🔴 CRÍTICO (>50% negativo)  
- Requiere atención inmediata
- Color rojo en indicadores

### 🟡 ATENCIÓN (>30% negativo)
- Hay áreas que necesitan mejora  
- Color amarillo en indicadores

### 🔵 ESTABLE (equilibrado)
- Situación equilibrada
- Color azul en indicadores

## 🔧 Funcionalidades Técnicas

### Extracción de Datos
```python
def extract_tweet_data(tweet_item):
    """Extrae datos del tweet de la estructura compleja de la API"""
```
- Maneja la estructura JSON compleja de Twitter API v2
- Extrae metadatos de usuario y tweet
- Calcula engagement total automáticamente

### Análisis de Sentimientos
```python
def analyze_sentiment(text):
    """Analiza el sentimiento del texto"""
```
- **Diccionario positivo**: 'excelente', 'gracias', 'solucionado', etc.
- **Diccionario negativo**: 'sin luz', 'apagón', 'problema', etc.
- **Lógica de puntuación** por frecuencia de palabras

### Formateo de Números
```python
def format_number(num):
    """Formatea números para mostrar K, M, etc."""
```
- Convierte números grandes a formato legible
- Soporte para K (miles) y M (millones)

### Cache de Datos
- **@st.cache_data(ttl=300)**: Cache de 5 minutos para optimizar rendimiento
- **Invalidación manual** con botón de actualización

## 📊 Métricas Calculadas

### Engagement Total
```
Engagement = Likes + Retweets + Replies
```

### Engagement Rate  
```
Rate = (Total Engagement / Total Alcance) × 100
```

### Alcance Estimado
```
Conservador = Suma de seguidores de usuarios
Optimista = Conservador × 2
```

### Contenido Viral
```
Viral = Tweets con Engagement > 100
```

## 🎨 Personalización Visual

### Colores del Sistema
- **Azul Twitter**: `#1DA1F2` (principal)
- **Verde Éxito**: `#10B981` (positivo)
- **Rojo Crítico**: `#EF4444` (negativo)  
- **Amarillo Atención**: `#F59E0B` (advertencia)
- **Púrpura Alcance**: `#7C3AED` (métricas especiales)

### Efectos Interactivos
- **Hover effects** en cards
- **Animaciones CSS** suaves
- **Gradientes** en botones y métricas
- **Sombras dinámicas** en elementos

## 🚦 Manejo de Errores

### Errores de API
- **Rate limiting**: Manejo automático con delays
- **Errores HTTP**: Mensajes informativos al usuario
- **Timeouts**: 15 segundos por request

### Datos Faltantes
- **Tweets vacíos**: Filtrado automático
- **Fechas inválidas**: Manejo con `errors='coerce'`
- **Métricas faltantes**: Valores por defecto (0)

## 📈 Optimizaciones de Rendimiento

### Caching Estratégico
- **API calls**: Cache de 5 minutos
- **Procesamiento**: Cache de transformaciones
- **Invalidación**: Manual y automática

### Procesamiento Paralelo
- **Búsquedas múltiples**: Términos procesados secuencialmente con delays
- **Análisis batch**: Sentimientos procesados en lote

### UI Responsiva
- **Lazy loading**: Contenido cargado según necesidad
- **Progressive disclosure**: Información mostrada gradualmente

## 🔐 Consideraciones de Seguridad

### API Keys
- **Almacenamiento**: En variables del código (⚠️ considera variables de entorno)
- **Rotación**: Cambiar keys periódicamente
- **Límites**: Respetar rate limits de la API

### Datos Sensibles
- **No almacenamiento**: Datos no se guardan localmente
- **Cache temporal**: Solo en memoria durante ejecución
- **Privacidad**: Respeto a términos de Twitter API

## 🐛 Solución de Problemas

### Error "Script file not present"
```bash
# Instalar Streamlit correctamente
pip install streamlit

# O usar python -m
python -m streamlit run scrapeboard2.py
```

### API Key Inválida
1. Verificar key en RapidAPI dashboard
2. Confirmar suscripción activa
3. Revivar límites de cuota

### Sin Datos
1. Verificar conexión a internet
2. Confirmar términos de búsqueda
3. Revisar logs de API

### Performance Lenta
1. Reducir número de tweets mostrados
2. Desactivar auto-refresh
3. Limpiar cache manualmente

## 📞 Soporte y Contribución

### Reportar Bugs
- Crear issue con descripción detallada
- Incluir logs de error
- Especificar ambiente (OS, Python version)

### Solicitar Features
- Describir funcionalidad deseada
- Justificar caso de uso
- Proponer implementación si es posible

### Contribuir Código
1. Fork del repositorio
2. Crear rama feature
3. Implementar cambios
4. Crear pull request

## 📜 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- **Streamlit** por el framework de dashboards
- **Plotly** por las visualizaciones interactivas
- **RapidAPI** por el acceso a Twitter API
- **Twitter** por la plataforma de datos sociales

---

**⚡ Monitor @EdesurRD Pro** - Desarrollado para monitoreo profesional de redes sociales en el sector eléctrico dominicano.

*Última actualización: Enero 2025*

