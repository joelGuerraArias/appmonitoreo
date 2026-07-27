#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de menciones en X (Twitter) para @INTRANT_RD y @MiltonMorrison
Incluye términos: "rd se mueve", dekolor, Ángel/Angel Lockward (variantes y hashtags).
Conserva UI, métricas, gráficos y filtros del dashboard original.
"""

import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import os

# =========================
# Configuración de RapidAPI (usando tu key)
# =========================
RAPIDAPI_KEY = "5229dd57b0mshcfebd9eb4b486c7p1f1e97jsn2166ec53fcdf"
RAPIDAPI_HOST = "twitter-api47.p.rapidapi.com"
BASE_URL = "https://twitter-api47.p.rapidapi.com"

HEADERS = {
    'x-rapidapi-host': RAPIDAPI_HOST,
    'x-rapidapi-key': RAPIDAPI_KEY
}

# =========================
# Configuración de página
# =========================
st.set_page_config(
    page_title="Monitor @INTRANT_RD + @MiltonMorrison",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Estilos (UI)
# =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #1DA1F2 0%, #14171A 100%);
        padding: 2rem; border-radius: 20px; margin-bottom: 2rem;
        color: white; text-align: center;
        box-shadow: 0 10px 30px rgba(29, 161, 242, 0.3);
        animation: slideDown 0.8s ease-out;
    }

    .reach-card {
        background: linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%);
        color: white; padding: 1.5rem; border-radius: 16px; text-align: center;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.3); transition: transform 0.3s ease;
    }
    .reach-card:hover { transform: translateY(-3px) scale(1.02); }

    .status-success {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white; padding: 1rem; border-radius: 12px; margin: 1rem 0;
    }
    .status-warning {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white; padding: 1rem; border-radius: 12px; margin: 1rem 0;
    }

    @keyframes slideDown { from { opacity:0; transform: translateY(-30px);} to {opacity:1; transform: translateY(0);} }

    .stButton > button {
        background: linear-gradient(135deg, #1DA1F2 0%, #0d8bd9 100%) !important;
        border: none !important; border-radius: 25px !important; color: white !important;
        font-weight: 600 !important; padding: 0.6rem 2rem !important; transition: all 0.3s ease !important;
        box-shadow: 0 5px 15px rgba(29, 161, 242, 0.4) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(29, 161, 242, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Header
# =========================
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:2.5rem; font-weight:700;">🚦 Monitor @INTRANT_RD + @MiltonMorrison</h1>
    <p style="margin:0.5rem 0 0 0; font-size:1.2rem; opacity:0.9;">
        Monitoreo directo de cuentas y menciones específicas
    </p>
    <div style="margin-top:1rem; font-size:0.9rem; opacity:0.8;">
        🔍 Búsqueda • 📊 Métricas • 🎭 Sentimiento • 📈 Alcance
    </div>
</div>
""", unsafe_allow_html=True)

# =========================
# Targets: cuentas, términos y hashtags
# =========================
TARGET_HANDLES = ["@INTRANT_RD", "@MiltonMorrison"]

RELATED_TERMS = [
    # Menciones directas de las cuentas
    "INTRANT_RD", "INTRANT RD", "Milton Morrison", "MiltonMorrison",
    # Términos específicos solicitados
    "\"rd se mueve\"", "rd se mueve"
]

RELATED_HASHTAGS = [
    "#MiltonMorrison"
]

# =========================
# Helpers
# =========================
def extract_tweet_data(tweet_item):
    """Extrae datos del tweet de la estructura de la API."""
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
            'Engagement_Total': legacy.get('favorite_count', 0)
                                + legacy.get('retweet_count', 0)
                                + legacy.get('reply_count', 0),
            'URL': f"https://twitter.com/{user_legacy.get('screen_name', '')}/status/{result.get('rest_id', '')}",
            'Verificado': user_legacy.get('verified', False),
            'Seguidores_Usuario': user_legacy.get('followers_count', 0)
        }

        if tweet_data['Fecha']:
            try:
                dt = datetime.strptime(tweet_data['Fecha'], '%a %b %d %H:%M:%S %z %Y')
                tweet_data['Fecha'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass

        return tweet_data
    except Exception:
        return None

@st.cache_data(ttl=300)
def search_tweets_api(query, count=100):
    """Busca tweets usando la API de RapidAPI."""
    url = f"{BASE_URL}/v2/search"
    params = {'query': query, 'type': 'Latest'}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            tweets = []
            if 'tweets' in data:
                for tweet_item in data['tweets'][:count]:
                    tweet = extract_tweet_data(tweet_item)
                    if tweet and tweet['Texto']:
                        tweets.append(tweet)
            return tweets
        else:
            st.error(f"Error API: {r.status_code}")
            return []
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def collect_all_mentions():
    """
    Recolecta menciones de las cuentas objetivo + términos y hashtags relacionados.
    """
    search_terms = list(TARGET_HANDLES) + RELATED_TERMS + RELATED_HASHTAGS

    all_tweets = []
    progress_container = st.container()
    with progress_container:
        st.markdown("### 🔄 Recolectando datos desde X (Twitter)...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_steps = len(search_terms)

        for i, term in enumerate(search_terms):
            status_text.text(f"Paso {i + 1}/{total_steps}: Buscando '{term}'...")
            progress_bar.progress(i / total_steps)
            tweets = search_tweets_api(term, count=25)
            all_tweets.extend(tweets)
            time.sleep(0.8)  # pequeño delay para no saturar

        progress_bar.progress(1.0)
        status_text.text("✅ Recolección completada!")
        time.sleep(0.5)
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
    """Reglas simples de sentimiento (enfocado RD: tránsito/energía)."""
    if not text or pd.isna(text):
        return "Neutral", "😐"

    t = str(text).lower()

    positives = [
        'excelente','bueno','gracias','perfecto','genial','increíble','fantástico',
        'rápido','eficiente','solucionado','arreglado','restaurado','funciona',
        'mejor','buen servicio','felicidades','bien hecho','fluido','ordenado',
        'mejora','señalizado','prevención','educación vial','bien organizado',
        'control eficiente','buen trabajo','seguro','despejado','libre'
    ]
    negatives = [
        'malo','terrible','problema','falla','error','deficiente',
        'accidente','tapon','tapón','congestion','congestión','caos',
        'no funciona','pésimo','horrible','lento','atascado','embotellamiento',
        'queja','reclamo','denuncia','mal servicio','no sirve','colapsado',
        'avería','irresponsable','incompetente','abusadores','abuso',
        'sin semáforo','dañado','mal estado','bache','choque','colisión'
    ]

    p = sum(1 for w in positives if w in t)
    n = sum(1 for w in negatives if w in t)
    if p > n and p > 0:
        return "Positivo", "😊"
    elif n > p and n > 0:
        return "Negativo", "😞"
    else:
        return "Neutral", "😐"

def format_number(num):
    """Formatea 1200 -> 1.2K, etc."""
    try:
        num = int(num) if str(num).replace('.', '').isdigit() else 0
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return str(num)
    except:
        return "0"

def parse_views(views_str):
    """Convierte '1.2K' -> 1200, '3.4M' -> 3400000."""
    try:
        if not views_str or views_str == "0":
            return 0
        s = str(views_str).upper()
        if 'K' in s:
            return int(float(s.replace('K','')) * 1000)
        elif 'M' in s:
            return int(float(s.replace('M','')) * 1_000_000)
        else:
            return int(s) if s.isdigit() else 0
    except:
        return 0

# =========================
# Sidebar (controles)
# =========================
with st.sidebar:
    st.markdown("### 🎛️ Panel de Control")

    if RAPIDAPI_KEY:
        st.markdown("""
        <div class="status-success">
            <h4 style="margin:0;">✅ RapidAPI Conectada</h4>
            <p style="margin:0.5rem 0 0 0; opacity:0.9;">
                🔑 API Key configurada<br>🌐 Datos en tiempo real
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-warning">
            <h4 style="margin:0;">⚠️ Falta API Key</h4>
            <p style="margin:0.5rem 0 0 0; opacity:0.9;">
                Define RAPIDAPI_KEY para obtener resultados.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🚀 Actualizar Datos")
    if st.button("🔄 Recolectar desde API", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("#### ⚙️ Configuración")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5 min)", value=False)
    show_stats = st.checkbox("📊 Mostrar estadísticas", True)
    show_engagement = st.checkbox("💫 Mostrar métricas de engagement", True)
    show_reach = st.checkbox("📈 Mostrar análisis de alcance", True)
    max_tweets = st.slider("📱 Tweets a mostrar", 5, 100, 20)

    st.markdown("#### 🔍 Filtros")
    sentimiento_filter = st.selectbox("🎭 Sentimiento", ["Todos", "Positivo", "Negativo", "Neutral"])
    engagement_filter = st.selectbox("💫 Engagement", ["Todos", "Alto (>50)", "Medio (10-50)", "Bajo (<10)"])

# =========================
# Carga, análisis y render
# =========================
def load_and_display_data():
    df = collect_all_mentions()

    if df.empty:
        st.markdown("""
        <div style="text-align:center; padding: 3rem; background: rgba(29, 161, 242, 0.05); border-radius: 20px; margin: 2rem 0;">
            <h2>📭 No hay datos disponibles</h2>
            <p>No se encontraron menciones recientes de @INTRANT_RD, @MiltonMorrison ni de los términos específicos configurados.</p>
            <p>Presiona "🔄 Recolectar desde API" para obtener datos frescos.</p>
        </div>
        """, unsafe_allow_html=True)
        return False

    # Sentimiento
    sentimientos, emojis = [], []
    for texto in df['Texto']:
        s, e = analyze_sentiment(texto)
        sentimientos.append(s)
        emojis.append(e)
    df['Sentimiento'] = sentimientos
    df['Emoji'] = emojis

    # Métricas numéricas
    for col in ['Likes', 'Retweets', 'Replies', 'Engagement_Total', 'Seguidores_Usuario']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Filtros
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

    # ===== Resumen Ejecutivo
    st.markdown("### 📋 Resumen Ejecutivo de Menciones")

    total_menciones = len(df)
    usuarios_totales = df['Usuario'].nunique()

    total_likes = df['Likes'].sum()
    total_retweets = df['Retweets'].sum()
    total_replies = df['Replies'].sum()
    total_engagement = df['Engagement_Total'].sum()

    total_views = sum(parse_views(v) for v in df['Views'])

    sentiment_counts = pd.Series(sentimientos).value_counts()
    pos = sentiment_counts.get('Positivo', 0)
    neg = sentiment_counts.get('Negativo', 0)
    neu = sentiment_counts.get('Neutral', 0)

    pct_pos = round((pos / total_menciones) * 100, 1) if total_menciones else 0
    pct_neg = round((neg / total_menciones) * 100, 1) if total_menciones else 0
    pct_neu = round((neu / total_menciones) * 100, 1) if total_menciones else 0

    if pct_pos > 60:
        estado_general, color_estado, msg_estado = "🟢 EXCELENTE", "#10B981", "La mayoría está a favor."
    elif pct_neg > 50:
        estado_general, color_estado, msg_estado = "🔴 CRÍTICO", "#EF4444", "Requiere atención inmediata."
    elif pct_neg > 30:
        estado_general, color_estado, msg_estado = "🟡 ATENCIÓN", "#F59E0B", "Varias áreas a mejorar."
    else:
        estado_general, color_estado, msg_estado = "🔵 ESTABLE", "#1DA1F2", "Situación equilibrada."

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div style="background:{color_estado}; color:white; padding:1.5rem; border-radius:12px; text-align:center;">
            <h3 style="margin:0; font-size:1.2rem;">Estado General</h3>
            <h2 style="margin:0.5rem 0; font-size:1.8rem;">{estado_general}</h2>
            <p style="margin:0; opacity:0.9; font-size:0.9rem;">{msg_estado}</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:white; border:2px solid #1DA1F2; border-radius:12px; padding:1.5rem; text-align:center;">
            <div style="font-size:2rem; font-weight:bold; color:#1DA1F2;">{total_menciones}</div>
            <div style="font-size:0.9rem; color:#657786;">Total Menciones</div>
            <div style="margin-top:1rem; font-size:2rem; font-weight:bold; color:#1DA1F2;">{usuarios_totales}</div>
            <div style="font-size:0.9rem; color:#657786;">Usuarios Únicos</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="reach-card">
            <h3 style="margin:0; font-size:2rem;">💫</h3>
            <h2 style="margin:10px 0 5px 0;">{format_number(total_engagement)}</h2>
            <p style="margin:0; opacity:0.9;">Total Engagement</p>
            <small style="opacity:0.8;">❤️ + 🔄 + 💬</small>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="reach-card">
            <h3 style="margin:0; font-size:2rem;">👀</h3>
            <h2 style="margin:10px 0 5px 0;">{format_number(total_views)}</h2>
            <p style="margin:0; opacity:0.9;">Total Vistas (estimado)</p>
            <small style="opacity:0.8;">Parseo de 'Views'</small>
        </div>
        """, unsafe_allow_html=True)

    # ===== Distribución de Sentimientos
    st.markdown("#### 📊 Distribución de Opiniones")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="background:#10B981; color:white; padding:1rem; border-radius:8px; margin-bottom:0.5rem;">
                <div style="font-size:1.5rem; font-weight:bold;">{pos}</div>
                <div style="font-size:0.8rem; opacity:0.9;">({pct_pos}%)</div>
            </div>
            <div style="color:#10B981; font-weight:600; font-size:0.9rem;">😊 A Favor</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="background:#EF4444; color:white; padding:1rem; border-radius:8px; margin-bottom:0.5rem;">
                <div style="font-size:1.5rem; font-weight:bold;">{neg}</div>
                <div style="font-size:0.8rem; opacity:0.9;">({pct_neg}%)</div>
            </div>
            <div style="color:#EF4444; font-weight:600; font-size:0.9rem;">😞 En Contra</div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="background:#6B7280; color:white; padding:1rem; border-radius:8px; margin-bottom:0.5rem;">
                <div style="font-size:1.5rem; font-weight:bold;">{neu}</div>
                <div style="font-size:0.8rem; opacity:0.9;">({pct_neu}%)</div>
            </div>
            <div style="color:#6B7280; font-weight:600; font-size:0.9rem;">😐 Neutral</div>
        </div>
        """, unsafe_allow_html=True)

    # ===== Alcance / Impacto
    if show_reach:
        st.markdown("### 📈 Análisis de Alcance e Impacto")
        total_reach_conservative = df['Seguidores_Usuario'].sum()
        total_reach_optimistic = total_reach_conservative * 2
        viral_tweets = len(df[df['Engagement_Total'] > 100])
        viral_percentage = (viral_tweets / total_menciones * 100) if total_menciones > 0 else 0
        engagement_rate = (total_engagement / total_reach_conservative * 100) if total_reach_conservative > 0 else 0

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">🎯</h3>
                <h2 style="margin:10px 0 5px 0;">{format_number(total_reach_conservative)}–{format_number(total_reach_optimistic)}</h2>
                <p style="margin:0; opacity:0.9;">Alcance Estimado</p>
                <small style="opacity:0.8;">Basado en seguidores</small>
            </div>
            """, unsafe_allow_html=True)
        with rc2:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">📈</h3>
                <h2 style="margin:10px 0 5px 0;">{engagement_rate:.1f}%</h2>
                <p style="margin:0; opacity:0.9;">Engagement Rate</p>
                <small style="opacity:0.8;">Interacciones/Alcance</small>
            </div>
            """, unsafe_allow_html=True)
        with rc3:
            st.markdown(f"""
            <div class="reach-card">
                <h3 style="margin:0; font-size:2rem;">🚀</h3>
                <h2 style="margin:10px 0 5px 0;">{viral_percentage:.1f}%</h2>
                <p style="margin:0; opacity:0.9;">Contenido Viral</p>
                <small style="opacity:0.8;">{viral_tweets} tweets &gt; 100 interacciones</small>
            </div>
            """, unsafe_allow_html=True)

    # ===== Gráficos
    if show_stats and len(df) > 0:
        st.markdown("### 📊 Análisis Visual")
        g1, g2 = st.columns(2)

        with g1:
            sentiment_counts_df = pd.DataFrame({
                'Sentimiento': ['Positivo', 'Negativo', 'Neutral'],
                'Cantidad': [pos, neg, neu]
            })
            fig_sentiment = px.pie(
                sentiment_counts_df,
                values='Cantidad',
                names='Sentimiento',
                title="📈 Distribución de Sentimientos",
                color='Sentimiento',
                color_discrete_map={'Positivo':'#10B981','Negativo':'#EF4444','Neutral':'#6B7280'}
            )
            fig_sentiment.update_layout(font=dict(size=12), showlegend=True, height=400)
            st.plotly_chart(fig_sentiment, use_container_width=True)

        with g2:
            if len(df) > 5:
                top_users = df.groupby('Usuario').agg({
                    'Engagement_Total':'sum',
                    'Seguidores_Usuario':'first'
                }).sort_values('Engagement_Total', ascending=False).head(10).reset_index()

                fig_users = px.bar(
                    top_users,
                    x='Engagement_Total', y='Usuario',
                    title="🏆 Top Usuarios por Engagement",
                    orientation='h', color='Engagement_Total',
                    color_continuous_scale='Blues'
                )
                fig_users.update_layout(font=dict(size=12), height=400, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_users, use_container_width=True)

    # ===== Lista de tweets
    st.markdown(f"### 📱 Últimas Menciones ({len(df_display)} de {len(df)})")
    for _, tw in df_display.iterrows():
        sentimiento, emoji = analyze_sentiment(tw['Texto'])
        engagement = tw.get('Engagement_Total', 0)
        if engagement > 100:
            engagement_color, engagement_label = "#10B981", "Alto"
        elif engagement > 10:
            engagement_color, engagement_label = "#F59E0B", "Medio"
        else:
            engagement_color, engagement_label = "#6B7280", "Bajo"
        verificado_badge = "✅" if tw.get('Verificado', False) else ""

        with st.container():
            colA, colB = st.columns([3,1])
            with colA:
                st.markdown(f"**@{tw['Usuario']}** {verificado_badge} *{tw.get('Nombre_Usuario','')}*")
            with colB:
                st.markdown(
                    f"<span style='background:{engagement_color}; color:white; padding:0.2rem 0.8rem; border-radius:12px; font-size:0.8rem;'>{engagement_label} Engagement</span>",
                    unsafe_allow_html=True
                )

            st.markdown(f"📝 {tw['Texto']}")
            st.caption(f"📅 {tw.get('Fecha','')} • 👥 {format_number(tw.get('Seguidores_Usuario',0))} seguidores")

            cA, cB, cC, cD, cE, cF = st.columns(6)
            with cA: st.metric("Sentimiento", f"{emoji} {sentimiento}")
            with cB: st.metric("❤️ Likes", tw.get('Likes',0))
            with cC: st.metric("🔄 RTs", tw.get('Retweets',0))
            with cD: st.metric("💬 Replies", tw.get('Replies',0))
            with cE: st.metric("👀 Views", format_number(tw.get('Views',0)))
            with cF: st.metric("💫 Total", tw.get('Engagement_Total',0))

            st.markdown(f"[🔗 Ver en Twitter]({tw.get('URL','#')})")
            st.divider()

    # ===== Extra: métricas de engagement
    if show_engagement and len(df) > 0:
        st.markdown("### 💫 Estadísticas de Engagement")
        e1, e2, e3, e4 = st.columns(4)
        with e1: st.metric("Engagement Promedio", f"{df['Engagement_Total'].mean():.1f}")
        with e2: st.metric("Engagement Máximo", f"{df['Engagement_Total'].max()}")
        with e3: st.metric("Promedio Seguidores", f"{format_number(df['Seguidores_Usuario'].mean())}")
        with e4:
            verified_count = int(df['Verificado'].sum())
            verified_pct = (verified_count / len(df) * 100) if len(df) > 0 else 0
            st.metric("Usuarios Verificados", f"{verified_count} ({verified_pct:.1f}%)")

        if len(df) > 10:
            st.markdown("#### 📈 Timeline de Engagement")
            df_tl = df.copy()
            df_tl['Fecha_Parse'] = pd.to_datetime(df_tl['Fecha'], errors='coerce')
            df_tl = df_tl.dropna(subset=['Fecha_Parse']).sort_values('Fecha_Parse')
            if len(df_tl) > 0:
                fig_tl = px.scatter(
                    df_tl, x='Fecha_Parse', y='Engagement_Total',
                    color='Sentimiento', size='Seguidores_Usuario',
                    hover_data=['Usuario','Likes','Retweets'],
                    title="Engagement por Tiempo",
                    color_discrete_map={'Positivo':'#10B981','Negativo':'#EF4444','Neutral':'#6B7280'}
                )
                fig_tl.update_layout(height=400)
                st.plotly_chart(fig_tl, use_container_width=True)

    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center; color:#657786; padding:1rem;">
        <p><strong>🚦 Monitor @INTRANT_RD + @MiltonMorrison</strong> • RapidAPI Twitter API</p>
        <p>📊 Analizados {len(df)} tweets • 🕐 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>🔄 Actualiza desde el panel lateral</p>
    </div>
    """, unsafe_allow_html=True)

    return True

# =========================
# Ejecutar
# =========================
if __name__ == "__main__":
    ok = load_and_display_data()
    if not ok:
        st.markdown("""
        <div style="text-align:center; padding:2rem;">
            <h3>🔧 Configuración</h3>
            <p>Verifica tu conexión y cuotas de RapidAPI.</p>
            <p>Usa el botón "Recolectar desde API" para refrescar.</p>
        </div>
        """, unsafe_allow_html=True)
