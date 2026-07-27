#!/usr/bin/env python3
"""
Dashboard @EdesurRD COMPLETO adaptado para tu API específica de RapidAPI
Versión completa con todas las características del original
"""

import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# Configuración de RapidAPI
RAPIDAPI_KEY = "5229dd57b0mshcfebd9eb4b486c7p1f1e97jsn2166ec53fcdf"
RAPIDAPI_HOST = "twitter-api47.p.rapidapi.com"
BASE_URL = "https://twitter-api47.p.rapidapi.com"

HEADERS = {
    'x-rapidapi-host': RAPIDAPI_HOST,
    'x-rapidapi-key': RAPIDAPI_KEY
}

# Configuración de página
st.set_page_config(
    page_title="Monitor @EdesurRD Pro", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS completo del original
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1DA1F2 0%, #14171A 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px rgba(29, 161, 242, 0.3);
        animation: slideDown 0.8s ease-out;
    }
    
    .tweet-card {
        background: white;
        border: 1px solid #e1e8ed;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        position: relative;
        overflow: hidden;
    }
    
    .tweet-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #1DA1F2, #14171A);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .tweet-card:hover::before {
        opacity: 1;
    }
    
    .tweet-card:hover {
        transform: translateY(-5px) scale(1.01);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
        border-color: #1DA1F2;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #1DA1F2 0%, #0d8bd9 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(29, 161, 242, 0.3);
        transition: transform 0.3s ease;
    }
    
    .stats-card:hover {
        transform: translateY(-3px) scale(1.02);
    }
    
    .engagement-metric {
        background: rgba(29, 161, 242, 0.1);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.2rem;
        font-size: 0.9rem;
        color: #1DA1F2;
        font-weight: 600;
    }
    
    .user-handle {
        color: #1DA1F2;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .tweet-text {
        color: #14171A;
        line-height: 1.6;
        margin: 1rem 0;
        font-size: 1rem;
    }
    
    .tweet-meta {
        color: #657786;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    
    .tweet-link {
        background: linear-gradient(135deg, #1DA1F2 0%, #0d8bd9 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        text-decoration: none;
        font-weight: 500;
        display: inline-block;
        transition: all 0.3s ease;
        border: none;
    }
    
    .tweet-link:hover {
        transform: scale(1.05);
        text-decoration: none;
        color: white;
        box-shadow: 0 5px 15px rgba(29, 161, 242, 0.4);
    }
    
    .reach-card {
        background: linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.3);
        transition: transform 0.3s ease;
    }
    
    .reach-card:hover {
        transform: translateY(-3px) scale(1.02);
    }
    
    .status-success {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .status-warning {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1DA1F2 0%, #0d8bd9 100%) !important;
        border: none !important;
        border-radius: 25px !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 5px 15px rgba(29, 161, 242, 0.4) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(29, 161, 242, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# Header principal completo
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:2.5rem; font-weight:700;">⚡ Monitor @EdesurRD Pro</h1>
    <p style="margin:0.5rem 0 0 0; font-size:1.2rem; opacity:0.9;">
        Dashboard Avanzado de Menciones en X (Twitter) - Análisis de Sentimientos & Alcance
    </p>
    <div style="margin-top:1rem; font-size:0.9rem; opacity:0.8;">
        🔍 Análisis • 📊 Métricas • 🎭 Sentimientos • 📈 Alcance • ⚡ Tiempo Real
    </div>
</div>
""", unsafe_allow_html=True)

def extract_tweet_data(tweet_item):
    """Extrae datos del tweet de la estructura compleja de tu API"""
    try:
        content = tweet_item.get('content', {})
        item_content = content.get('itemContent', {})
        tweet_results = item_content.get('tweet_results', {})
        result = tweet_results.get('result', {})
        
        legacy = result.get('legacy', {})
        core = result.get('core', {})
        user_results = core.get('user_results', {})
        user_result = user_results.get('result', {})
        user_legacy = user_result.get('legacy', {})
        
        # Obtener vistas si están disponibles
        views_data = result.get('views', {})
        views_count = views_data.get('count', '0') if views_data else '0'
        
        tweet_data = {
            'Texto': legacy.get('full_text', ''),
            'Usuario': user_legacy.get('screen_name', ''),
            'Nombre_Usuario': user_legacy.get('name', ''),
            'Fecha': legacy.get('created_at', ''),
            'Likes': legacy.get('favorite_count', 0),
            'Retweets': legacy.get('retweet_count', 0),
            'Replies': legacy.get('reply_count', 0),
            'Views': views_count,
            'Engagement_Total': (
                legacy.get('favorite_count', 0) + 
                legacy.get('retweet_count', 0) + 
                legacy.get('reply_count', 0)
            ),
            'URL': f"https://twitter.com/{user_legacy.get('screen_name', '')}/status/{result.get('rest_id', '')}",
            'Verificado': user_legacy.get('verified', False),
            'Seguidores_Usuario': user_legacy.get('followers_count', 0)
        }
        
        # Formatear fecha
        if tweet_data['Fecha']:
            try:
                dt = datetime.strptime(tweet_data['Fecha'], '%a %b %d %H:%M:%S %z %Y')
                tweet_data['Fecha'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        return tweet_data
        
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def search_tweets_api(query, count=100):
    """Busca tweets usando tu API específica"""
    url = f"{BASE_URL}/v2/search"
    params = {
        'query': query,
        'type': 'Latest'
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            tweets = []
            
            if 'tweets' in data:
                for tweet_item in data['tweets'][:count]:
                    tweet = extract_tweet_data(tweet_item)
                    if tweet and tweet['Texto']:
                        tweets.append(tweet)
            
            return tweets
        else:
            st.error(f"Error API: {response.status_code}")
            return []
            
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def collect_all_mentions():
    """Recolecta todas las menciones de @EdesurRD"""
    search_terms = [
        "@EdesurRD",
        "EdesurRD", 
        "Edesur",
        "sin luz República Dominicana",
        "apagón RD"
    ]
    
    all_tweets = []
    progress_container = st.container()
    
    with progress_container:
        st.markdown("### 🔄 Recolectando datos desde Twitter API...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_steps = len(search_terms)
        
        for i, term in enumerate(search_terms):
            status_text.text(f"Paso {i + 1}/{total_steps}: Buscando '{term}'...")
            progress_bar.progress(i / total_steps)
            
            tweets = search_tweets_api(term, count=25)
            all_tweets.extend(tweets)
            time.sleep(1)
        
        progress_bar.progress(1.0)
        status_text.text("✅ Recolección completada!")
        time.sleep(1)
        progress_container.empty()
    
    if all_tweets:
        df = pd.DataFrame(all_tweets)
        df = df.drop_duplicates(subset=['Texto'], keep='first')
        df['Fecha_Sort'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.sort_values('Fecha_Sort', ascending=False)
        df = df.drop('Fecha_Sort', axis=1)
        return df
    
    return pd.DataFrame()

def analyze_sentiment(text):
    """Analiza el sentimiento del texto y retorna sentimiento y emoji"""
    if not text or pd.isna(text):
        return "Neutral", "😐"
    
    text_lower = str(text).lower()
    
    positive_words = [
        'excelente', 'bueno', 'gracias', 'perfecto', 'genial', 'increíble', 'fantástico',
        'rápido', 'eficiente', 'solucionado', 'arreglado', 'restaurado', 'funciona',
        'mejor', 'buena atención', 'buen servicio', 'felicidades', 'bravo', 'bien hecho',
        'funciona bien', 'sin problemas', 'todo bien', 'gracias por', 'buen trabajo',
        'excelente trabajo', 'muy bien', 'perfecto servicio', 'rápida respuesta'
    ]
    
    negative_words = [
        'malo', 'terrible', 'problema', 'falla', 'error', 'deficiente', 'sin luz', 'apagón',
        'corte', 'interrupción', 'daño', 'roto', 'no funciona', 'pésimo', 'horrible',
        'molesto', 'furioso', 'enojado', 'indignado', 'cansado', 'harto', 'fastidiado',
        'queja', 'reclamo', 'denuncia', 'mal servicio', 'mala atención', 'no sirve',
        'se fue la luz', 'sin energía', 'blackout', 'fallo eléctrico', 'avería',
        'cuándo van a arreglar', 'cuándo vuelve', 'llevo horas sin luz', 'desde ayer',
        'ineficiente', 'lento', 'tardío', 'irresponsable', 'incompetente', 'abusadores', 'abuso'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count and positive_count > 0:
        return "Positivo", "😊"
    elif negative_count > positive_count and negative_count > 0:
        return "Negativo", "😞"
    else:
        return "Neutral", "😐"

def format_number(num):
    """Formatea números para mostrar K, M, etc."""
    try:
        num = int(num) if str(num).replace('.', '').isdigit() else 0
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)
    except:
        return "0"

def parse_views(views_str):
    """Convierte strings como '1.2K' a números"""
    try:
        if not views_str or views_str == "0":
            return 0
        views_str = str(views_str).upper()
        if 'K' in views_str:
            return int(float(views_str.replace('K', '')) * 1000)
        elif 'M' in views_str:
            return int(float(views_str.replace('M', '')) * 1000000)
        else:
            return int(views_str) if views_str.isdigit() else 0
    except:
        return 0

# Sidebar completo como el original
with st.sidebar:
    st.markdown("### 🎛️ Panel de Control Pro")
    
    st.markdown(f"""
    <div class="status-success">
        <h4 style="margin:0;">✅ RapidAPI Conectada</h4>
        <p style="margin:0.5rem 0 0 0; opacity:0.9;">
            🔑 API Key configurada<br>
            🌐 Datos en tiempo real
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Botones de control
    st.markdown("#### 🚀 Actualizar Datos")
    if st.button("🔄 Recolectar desde API", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("#### 💻 Información")
    st.info("Los datos se obtienen directamente de Twitter API via RapidAPI")
    
    st.markdown("---")
    
    # Configuración completa
    st.markdown("#### ⚙️ Configuración")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5min)", value=False)
    show_stats = st.checkbox("📊 Mostrar estadísticas", True)
    show_engagement = st.checkbox("💫 Mostrar métricas de engagement", True)
    show_reach = st.checkbox("📈 Mostrar análisis de alcance", True)
    max_tweets = st.slider("📱 Tweets a mostrar", 5, 100, 20)
    
    # Filtros avanzados
    st.markdown("#### 🔍 Filtros")
    sentimiento_filter = st.selectbox("🎭 Sentimiento", ["Todos", "Positivo", "Negativo", "Neutral"])
    engagement_filter = st.selectbox("💫 Engagement", ["Todos", "Alto (>50)", "Medio (10-50)", "Bajo (<10)"])

# Función principal completa
def load_and_display_data():
    # Recolectar datos de la API
    df = collect_all_mentions()
    
    if df.empty:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: rgba(29, 161, 242, 0.05); border-radius: 20px; margin: 2rem 0;">
            <h2>📭 No hay datos disponibles</h2>
            <p>No se encontraron menciones recientes de @EdesurRD</p>
            <p>Presiona "🔄 Recolectar desde API" para obtener datos frescos</p>
        </div>
        """, unsafe_allow_html=True)
        return False
    
    # Agregar análisis de sentimientos
    sentimientos = []
    emojis = []
    for texto in df['Texto']:
        sentiment, emoji = analyze_sentiment(texto)
        sentimientos.append(sentiment)
        emojis.append(emoji)
    
    df['Sentimiento'] = sentimientos
    df['Emoji'] = emojis
    
    # Convertir métricas a numéricas
    for col in ['Likes', 'Retweets', 'Replies', 'Engagement_Total']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Aplicar filtros
    df_filtered = df.copy()
    
    if sentimiento_filter != "Todos":
        df_filtered = df_filtered[df_filtered['Sentimiento'] == sentimiento_filter]
    
    if engagement_filter != "Todos":
        if engagement_filter == "Alto (>50)":
            df_filtered = df_filtered[df_filtered['Engagement_Total'] > 50]
        elif engagement_filter == "Medio (10-50)":
            df_filtered = df_filtered[(df_filtered['Engagement_Total'] >= 10) & (df_filtered['Engagement_Total'] <= 50)]
        elif engagement_filter == "Bajo (<10)":
            df_filtered = df_filtered[df_filtered['Engagement_Total'] < 10]
    
    df_display = df_filtered.head(max_tweets)
    
    # RESUMEN EJECUTIVO COMPLETO
    st.markdown("### 📋 Resumen Ejecutivo de Menciones")
    
    # Calcular estadísticas
    total_menciones = len(df)
    usuarios_totales = df['Usuario'].nunique()
    
    # Métricas de engagement
    total_likes = df['Likes'].sum()
    total_retweets = df['Retweets'].sum()
    total_replies = df['Replies'].sum()
    total_engagement = df['Engagement_Total'].sum()
    
    # Análisis de vistas/alcance
    total_views = 0
    for view in df['Views']:
        total_views += parse_views(view)
    
    sentiment_counts = pd.Series(sentimientos).value_counts()
    
    positivos_total = sentiment_counts.get('Positivo', 0)
    negativos_total = sentiment_counts.get('Negativo', 0)
    neutrales_total = sentiment_counts.get('Neutral', 0)
    
    pct_positivo_total = round((positivos_total / total_menciones) * 100, 1) if total_menciones > 0 else 0
    pct_negativo_total = round((negativos_total / total_menciones) * 100, 1) if total_menciones > 0 else 0
    pct_neutral_total = round((neutrales_total / total_menciones) * 100, 1) if total_menciones > 0 else 0
    
    # Determinar estado general
    if pct_positivo_total > 60:
        estado_general = "🟢 EXCELENTE"
        color_estado = "#10B981"
        mensaje_estado = "La mayoría de usuarios están satisfechos"
    elif pct_negativo_total > 50:
        estado_general = "🔴 CRÍTICO"
        color_estado = "#EF4444"
        mensaje_estado = "Requiere atención inmediata"
    elif pct_negativo_total > 30:
        estado_general = "🟡 ATENCIÓN"
        color_estado = "#F59E0B"
        mensaje_estado = "Hay áreas que necesitan mejora"
    else:
        estado_general = "🔵 ESTABLE"
        color_estado = "#1DA1F2"
        mensaje_estado = "Situación equilibrada"
    
    # Métricas principales en 4 columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background: {color_estado}; color: white; padding: 1.5rem; border-radius: 12px; text-align: center;">
            <h3 style="margin: 0; font-size: 1.2rem;">Estado General</h3>
            <h2 style="margin: 0.5rem 0; font-size: 1.8rem;">{estado_general}</h2>
            <p style="margin: 0; opacity: 0.9; font-size: 0.9rem;">{mensaje_estado}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: white; border: 2px solid #1DA1F2; border-radius: 12px; padding: 1.5rem; text-align: center;">
            <div style="margin-bottom: 1rem;">
                <div style="font-size: 2rem; font-weight: bold; color: #1DA1F2;">{total_menciones}</div>
                <div style="font-size: 0.9rem; color: #657786;">Total Menciones</div>
            </div>
            <div>
                <div style="font-size: 2rem; font-weight: bold; color: #1DA1F2;">{usuarios_totales}</div>
                <div style="font-size: 0.9rem; color: #657786;">Usuarios Únicos</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center;">
            <div style="margin-bottom: 1rem;">
                <div style="font-size: 2rem; font-weight: bold;">{format_number(total_engagement)}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Total Engagement</div>
            </div>
            <div>
                <div style="font-size: 2rem; font-weight: bold;">{format_number(total_views)}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Total Vistas</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: white; padding: 1.5rem; border-radius: 12px; text-align: center;">
            <div style="font-size: 0.9rem; margin-bottom: 0.5rem; opacity: 0.9;">Engagement Breakdown</div>
            <div style="display: flex; justify-content: space-around; margin: 0.5rem 0;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">❤️{format_number(total_likes)}</div>
                    <div style="font-size: 0.7rem; opacity: 0.8;">Likes</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">🔄{format_number(total_retweets)}</div>
                    <div style="font-size: 0.7rem; opacity: 0.8;">RTs</div>
                </div>
                <div>
                    <div style="font-size: 1.5rem; font-weight: bold;">💬{format_number(total_replies)}</div>
                    <div style="font-size: 0.7rem; opacity: 0.8;">Replies</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Distribución de Sentimientos
    st.markdown("#### 📊 Distribución de Opiniones")
    subcol1, subcol2, subcol3 = st.columns(3)
    
    with subcol1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="background: #10B981; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <div style="font-size: 1.5rem; font-weight: bold;">{positivos_total}</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">({pct_positivo_total}%)</div>
            </div>
            <div style="color: #10B981; font-weight: 600; font-size: 0.9rem;">😊 A Favor</div>
        </div>
        """, unsafe_allow_html=True)
    
    with subcol2:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="background: #EF4444; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <div style="font-size: 1.5rem; font-weight: bold;">{negativos_total}</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">({pct_negativo_total}%)</div>
            </div>
            <div style="color: #EF4444; font-weight: 600; font-size: 0.9rem;">😞 En Contra</div>
        </div>
        """, unsafe_allow_html=True)
    
    with subcol3:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="background: #6B7280; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
                <div style="font-size: 1.5rem; font-weight: bold;">{neutrales_total}</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">({pct_neutral_total}%)</div>
            </div>
            <div style="color: #6B7280; font-weight: 600; font-size: 0.9rem;">😐 Neutral</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ANÁLISIS DE ALCANCE
    if show_reach:
        st.markdown("### 📈 Análisis de Alcance y Impacto")
        
        # Calcular métricas de alcance
        total_reach_conservative = df['Seguidores_Usuario'].sum()
        total_reach_optimistic = total_reach_conservative * 2
        viral_tweets = len(df[df['Engagement_Total'] > 100])
        viral_percentage = (viral_tweets / total_menciones * 100) if total_menciones > 0 else 0
        engagement_rate = (total_engagement / total_reach_conservative * 100) if total_reach_conservative > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">🎯</h3>
                <h2 style="margin:10px 0 5px 0;">{format_number(total_reach_conservative)}-{format_number(total_reach_optimistic)}</h2>
                <p style="margin:0; opacity:0.9;">Alcance Estimado</p>
                <small style="opacity:0.8;">Basado en seguidores</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">💫</h3>
                <h2 style="margin:10px 0 5px 0;">{engagement_rate:.1f}%</h2>
                <p style="margin:0; opacity:0.9;">Engagement Rate</p>
                <small style="opacity:0.8;">Interacciones/Alcance</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">🚀</h3>
                <h2 style="margin:10px 0 5px 0;">{viral_percentage:.1f}%</h2>
                <p style="margin:0; opacity:0.9;">Contenido Viral</p>
                <small style="opacity:0.8;">{viral_tweets} tweets >100 interacciones</small>
            </div>
            """, unsafe_allow_html=True)
    
    # GRÁFICOS
    if show_stats and len(df) > 0:
        st.markdown("### 📊 Análisis Visual")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de sentimientos
            sentiment_data = sentiment_counts.reset_index()
            sentiment_data.columns = ['Sentimiento', 'Cantidad']
            
            colors = {'Positivo': '#10B981', 'Negativo': '#EF4444', 'Neutral': '#6B7280'}
            
            fig_sentiment = px.pie(
                sentiment_data, 
                values='Cantidad', 
                names='Sentimiento',
                title="📈 Distribución de Sentimientos",
                color='Sentimiento',
                color_discrete_map=colors
            )
            fig_sentiment.update_layout(
                font=dict(size=12),
                showlegend=True,
                height=400
            )
            st.plotly_chart(fig_sentiment, use_container_width=True)
        
        with col2:
            # Top usuarios por engagement
            if len(df) > 5:
                top_users = df.groupby('Usuario').agg({
                    'Engagement_Total': 'sum',
                    'Seguidores_Usuario': 'first'
                }).sort_values('Engagement_Total', ascending=False).head(10)
                
                top_users = top_users.reset_index()
                
                fig_users = px.bar(
                    top_users, 
                    x='Engagement_Total', 
                    y='Usuario',
                    title="🏆 Top Usuarios por Engagement",
                    orientation='h',
                    color='Engagement_Total',
                    color_continuous_scale='Blues'
                )
                fig_users.update_layout(
                    font=dict(size=12),
                    height=400,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig_users, use_container_width=True)
    
    # TWEETS INDIVIDUALES
    st.markdown(f"### 📱 Últimas Menciones ({len(df_display)} de {len(df)})")
    
    for idx, tweet in df_display.iterrows():
        sentimiento, emoji = analyze_sentiment(tweet['Texto'])
        
        # Determinar color de engagement
        engagement = tweet.get('Engagement_Total', 0)
        if engagement > 100:
            engagement_color = "#10B981"
            engagement_label = "Alto"
        elif engagement > 10:
            engagement_color = "#F59E0B" 
            engagement_label = "Medio"
        else:
            engagement_color = "#6B7280"
            engagement_label = "Bajo"
        
        # Determinar si es usuario verificado
        verificado_badge = "✅" if tweet.get('Verificado', False) else ""
        
        # Usar container de Streamlit en lugar de HTML
        with st.container():
            # Header del tweet
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**@{tweet['Usuario']}** {verificado_badge} *{tweet.get('Nombre_Usuario', '')}*")
            with col2:
                st.markdown(f"<span style='background: {engagement_color}; color: white; padding: 0.2rem 0.8rem; border-radius: 12px; font-size: 0.8rem;'>{engagement_label} Engagement</span>", unsafe_allow_html=True)
            
            # Contenido del tweet
            st.markdown(f"📝 {tweet['Texto']}")
            
            # Metadatos
            st.caption(f"📅 {tweet.get('Fecha', 'Fecha no disponible')} • 👥 {format_number(tweet.get('Seguidores_Usuario', 0))} seguidores")
            
            # Métricas en columnas
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Sentimiento", f"{emoji} {sentimiento}")
            with col2:
                st.metric("❤️ Likes", tweet.get('Likes', 0))
            with col3:
                st.metric("🔄 RTs", tweet.get('Retweets', 0))
            with col4:
                st.metric("💬 Replies", tweet.get('Replies', 0))
            with col5:
                st.metric("👀 Views", format_number(tweet.get('Views', 0)))
            with col6:
                st.metric("💫 Total", tweet.get('Engagement_Total', 0))
            
            # Link al tweet
            st.markdown(f"[🔗 Ver en Twitter]({tweet.get('URL', '#')})")
            
            # Separador
            st.divider()
    
    # ESTADÍSTICAS ADICIONALES
    if show_engagement and len(df) > 0:
        st.markdown("### 💫 Estadísticas de Engagement")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_engagement = df['Engagement_Total'].mean()
            st.metric("Engagement Promedio", f"{avg_engagement:.1f}")
        
        with col2:
            max_engagement = df['Engagement_Total'].max()
            st.metric("Engagement Máximo", f"{max_engagement}")
        
        with col3:
            avg_followers = df['Seguidores_Usuario'].mean()
            st.metric("Promedio Seguidores", f"{format_number(avg_followers)}")
        
        with col4:
            verified_count = df['Verificado'].sum()
            verified_pct = (verified_count / len(df) * 100) if len(df) > 0 else 0
            st.metric("Usuarios Verificados", f"{verified_count} ({verified_pct:.1f}%)")
        
        # Timeline de engagement
        if len(df) > 10:
            st.markdown("#### 📈 Timeline de Engagement")
            df_timeline = df.copy()
            df_timeline['Fecha_Parse'] = pd.to_datetime(df_timeline['Fecha'], errors='coerce')
            df_timeline = df_timeline.dropna(subset=['Fecha_Parse'])
            df_timeline = df_timeline.sort_values('Fecha_Parse')
            
            if len(df_timeline) > 0:
                fig_timeline = px.scatter(
                    df_timeline,
                    x='Fecha_Parse',
                    y='Engagement_Total',
                    color='Sentimiento',
                    size='Seguidores_Usuario',
                    hover_data=['Usuario', 'Likes', 'Retweets'],
                    title="Engagement por Tiempo",
                    color_discrete_map={'Positivo': '#10B981', 'Negativo': '#EF4444', 'Neutral': '#6B7280'}
                )
                fig_timeline.update_layout(height=400)
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    # PIE DE PÁGINA CON INFO
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #657786; padding: 1rem;">
        <p><strong>⚡ Monitor @EdesurRD Pro</strong> • Powered by RapidAPI Twitter API</p>
        <p>📊 Analizados {len(df)} tweets • 🕐 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>🔄 Los datos se actualizan desde la API oficial de Twitter</p>
    </div>
    """, unsafe_allow_html=True)
    
    return True

# Ejecutar la aplicación
if __name__ == "__main__":
    success = load_and_display_data()
    
    if not success:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h3>🔧 Configuración Inicial</h3>
            <p>Para usar este dashboard, asegúrate de tener:</p>
            <ul style="text-align: left; max-width: 500px; margin: 0 auto;">
                <li>✅ Tu API key de RapidAPI configurada</li>
                <li>✅ Conexión a internet estable</li>
                <li>✅ Cuota disponible en tu plan de RapidAPI</li>
            </ul>
            <p style="margin-top: 1rem;">
                <strong>💡 Tip:</strong> Presiona "Recolectar desde API" para obtener datos frescos
            </p>
        </div>
        """, unsafe_allow_html=True)