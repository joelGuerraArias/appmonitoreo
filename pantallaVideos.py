# app.py
import math
import streamlit as st
from cloudinary import config as cld_config
from cloudinary.api import resources

# ========= CREDENCIALES (LOCAL) =========
CLOUD_NAME = "dhzxzbkmc"
API_KEY    = "149663287387673"
API_SECRET = "YOUR_CLOUDINARY_API_SECRET"
FOLDER     = "video_analyzer_clips"   # carpeta
RESOURCE   = "video"                  # tipo
TRANSFORM  = "q_auto,f_mp4"           # calidad/formato

# ========= CONFIG CLOUDINARY =========
cld_config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True
)

# ========= STREAMLIT UI =========
st.set_page_config(page_title="Cloudinary Video Gallery", layout="wide")
st.title("🎬 Cloudinary Video Gallery")
st.caption(f"Cloud: `{CLOUD_NAME}` • Carpeta: `{FOLDER}` • Recurso: `{RESOURCE}` • Transform: `{TRANSFORM}`")

# Controles
c1, c2, c3 = st.columns([1,1,2])
with c1:
    page_size = st.selectbox("Items por página", [12, 24, 48], index=1)
with c2:
    sort_desc = st.toggle("Nuevos primero", value=True)
with c3:
    q = st.text_input("Filtrar por nombre (public_id contiene...)", "")

# Estado de paginación
if "next_cursor" not in st.session_state:
    st.session_state.next_cursor = None
if "pages" not in st.session_state:
    st.session_state.pages = []
if "done" not in st.session_state:
    st.session_state.done = False

# Botones
b1, b2, _ = st.columns([1,1,6])
with b1:
    if st.button("🔄 Recargar", use_container_width=True):
        st.session_state.next_cursor = None
        st.session_state.pages = []
        st.session_state.done = False
        st.experimental_rerun()
with b2:
    load_more_clicked = st.button("⬇️ Cargar más", use_container_width=True, disabled=st.session_state.done)

# Helpers de entrega
def video_url(public_id: str) -> str:
    return f"https://res.cloudinary.com/{CLOUD_NAME}/video/upload/{TRANSFORM}/{public_id}.mp4"

def poster_url(public_id: str) -> str:
    return f"https://res.cloudinary.com/{CLOUD_NAME}/video/upload/so_1/{public_id}.jpg"

def thumb_url(public_id: str) -> str:
    return f"https://res.cloudinary.com/{CLOUD_NAME}/video/upload/so_0,du_1,w_480,h_270,c_fill/{public_id}.jpg"

# Fetch página
def fetch_page(limit: int, next_cursor: str | None):
    params = dict(
        resource_type=RESOURCE,
        type="upload",
        prefix=f"{FOLDER}/",      # por carpeta
        max_results=limit,
        direction="desc" if sort_desc else "asc",
        context=True,
    )
    if next_cursor:
        params["next_cursor"] = next_cursor
    return resources(**params)

# Cargar datos (primera vez o botón)
if load_more_clicked or not st.session_state.pages:
    if not st.session_state.done:
        try:
            result = fetch_page(page_size, st.session_state.next_cursor)
            items = result.get("resources", [])
            if items:
                st.session_state.pages.append(items)
                st.session_state.next_cursor = result.get("next_cursor")
                if not st.session_state.next_cursor:
                    st.session_state.done = True
            else:
                st.session_state.done = True
        except Exception as e:
            st.error(f"Error listando videos: {e}")
            st.stop()

# Flatten + filtro por public_id
all_items = [it for page in st.session_state.pages for it in page]
if q:
    q_low = q.lower()
    all_items = [r for r in all_items if q_low in r.get("public_id","").lower()]

st.write(f"Total cargados: **{len(all_items)}** {'(completo)' if st.session_state.done else ''}")

# Grid
cols_per_row = 3 if page_size >= 24 else 2
rows = math.ceil(len(all_items) / cols_per_row)

for i in range(rows):
    cols = st.columns(cols_per_row)
    for j in range(cols_per_row):
        idx = i*cols_per_row + j
        if idx >= len(all_items):
            break
        r = all_items[idx]
        public_id = r.get("public_id")
        size_mb = (r.get("bytes", 0) / (1024*1024))
        duration = r.get("duration", 0.0)
        created_at = r.get("created_at", "")

        with cols[j]:
            st.image(thumb_url(public_id), use_container_width=True)
            st.markdown(f"**{public_id.replace(FOLDER + '/', '')}**")
            st.caption(f"{created_at} • {duration:.1f}s • {size_mb:.1f} MB")
            st.video(video_url(public_id))
            st.markdown(f"[⬇️ Descargar MP4]({video_url(public_id)})")

st.divider()
st.caption("⚠️ Estas credenciales están embebidas para uso local. No las publiques ni las subas a repositorios.")
