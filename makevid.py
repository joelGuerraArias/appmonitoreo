# archivo: app_veo3_customtkinter_3x8s.py
import os
import time
import math
import tempfile
import subprocess
import textwrap
import threading
import shutil
import logging
from typing import List, Optional
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Gemini (Veo 3)
from google import genai
from google.genai import types

# Slideshow desarrollo - replaced with ffmpegop
# from moviepy.editor import ImageClip, concatenate_videoclips, AudioClip

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('makevid.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================
# CONFIGURACIÓN GLOBAL
# =========================
ASPECT_RATIO = "9:16"   # vertical
RESOLUTION   = "720p"   # vertical 720p = buena compatibilidad
MODEL        = "veo-3.0-generate-001"   # o "veo-3.0-fast-generate-001"
SEED         = 1234
FPS          = 24

# Duraciones (TOTAL = 24 s, 3x8)
SEG_DURATIONS = {
    "bienvenida": 8,
    "desarrollo": 8,
    "despedida": 8
}

# Reglas (exterior-only, auto inmóvil, fidelidad total)
NEGATIVE_PROMPT = (
    "interior, cabina, tablero, asientos, volante, sunroof, "
    "cambios de color o forma, deformaciones, tuning, vinilos, body kits, "
    "texto en pantalla, subtítulos, letreros, watermark, logotipos inventados, "
    "auto en movimiento, auto corriendo, wheels spinning, ruedas girando, "
    "motion blur de vehículo, burnouts, humo de escape, carretera con desplazamiento, "
    "rolling shots, persecuciones, estelas de velocidad"
)

SYSTEM_STYLE = (
    "Fidelidad absoluta al auto de las imágenes de referencia. "
    "No inventes ni modifiques líneas, proporciones, color o accesorios. "
    "Muestra únicamente el EXTERIOR. Prohibido interior o cabina. "
    "El auto NUNCA aparece en movimiento; ninguna rueda girando ni desplazamiento de carretera. "
    "Estilo cinematográfico natural, sin texto en pantalla."
)

# =========================
# FUNCIONES DE VALIDACIÓN
# =========================
def check_ffmpeg_availability() -> bool:
    """Verifica si FFmpeg está disponible en el sistema."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def validate_image_file(file_path: str) -> bool:
    """Valida que el archivo sea una imagen válida."""
    if not file_path or not os.path.exists(file_path):
        return False
    
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext not in valid_extensions:
        return False
    
    # Verificar que el archivo no esté corrupto
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception as e:
        logger.error(f"Error validando imagen {file_path}: {e}")
        return False

def check_disk_space(required_gb: float = 2.0) -> bool:
    """Verifica que hay suficiente espacio en disco."""
    try:
        free_bytes = shutil.disk_usage('.').free
        free_gb = free_bytes / (1024**3)
        logger.info(f"Espacio libre en disco: {free_gb:.2f} GB")
        return free_gb >= required_gb
    except Exception as e:
        logger.error(f"Error verificando espacio en disco: {e}")
        return False

def validate_api_key(api_key: str) -> bool:
    """Valida formato básico de API key."""
    if not api_key or len(api_key) < 20:
        return False
    return True

# =========================
# FUNCIONES DE VIDEO
# =========================
def load_image_bytes(path: str) -> Optional[bytes]:
    """Carga bytes de imagen con validación mejorada."""
    if not validate_image_file(path):
        logger.error(f"Archivo de imagen inválido: {path}")
        return None
    
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error cargando imagen {path}: {e}")
        return None

def ffmpeg(*args):
    """Ejecuta FFmpeg con manejo de errores mejorado."""
    if not check_ffmpeg_availability():
        raise RuntimeError("FFmpeg no está instalado o no está disponible en el PATH del sistema")
    
    cmd = ["ffmpeg", "-y"] + list(args)
    logger.info(f"Ejecutando FFmpeg: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("FFmpeg ejecutado exitosamente")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en FFmpeg: {e.stderr}")
        raise RuntimeError(f"Error en FFmpeg: {e.stderr}")
    except Exception as e:
        logger.error(f"Error inesperado en FFmpeg: {e}")
        raise

def ensure_exact_duration(input_path: str, seconds: int, output_path: str):
    """Fuerza exactamente N segundos (recorte si sobra)."""
    ffmpeg("-i", input_path, "-t", str(seconds), "-r", str(FPS),
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", output_path)

def concat_clips(clips: List[str], output: str):
    """Concatena los clips manteniendo codecs."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in clips:
            f.write(f"file '{os.path.abspath(p)}'\n")
        listfile = f.name
    ffmpeg("-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", output)

def build_prompt_vertical(block_text: str, block_role: str, car_hint: Optional[str]=None) -> str:
    role2cam = {
        "bienvenida": "Primerísimo primer plano vertical del actor, cámara fija; fondo limpio. El auto NO se muestra aún.",
        "desarrollo": "Planos EXTERIORES verticales y estáticos: parrilla, faros, llantas y emblemas. NO mostrar interior ni movimiento.",
        "despedida": "Plano 3/4 TRASERO del EXTERIOR en vertical, leve dolly-out de cámara; auto inmóvil para cierre elegante."
    }
    movement_rules = (
        "El auto debe permanecer inmóvil. No mostrar ruedas girando ni desplazamiento en carretera. "
        "El único movimiento permitido es el de la cámara (paneo corto/push-in/dolly-out)."
    )
    spoken = block_text.strip()
    cam = role2cam.get(block_role, "Plano exterior vertical, sujeto centrado, cámara estable.")
    sfx = "Ambiente sutil; cama musical ligera; efectos discretos del motor detenido."
    carline = f" Enfatiza: {car_hint}." if car_hint else ""

    return textwrap.dedent(f"""
        {SYSTEM_STYLE} {movement_rules}
        {cam}{carline}
        Diálogo: "{spoken}"
        Sonido: {sfx}
        Evita texto en pantalla y saltos de continuidad.
    """).strip()

def generate_veo_video(client: genai.Client, prompt: str, image_bytes: Optional[bytes], out_path: str, console=lambda *_: None):
    """Genera video con Veo 3 con manejo de errores mejorado."""
    try:
        logger.info(f"Iniciando generación de video con Veo 3: {out_path}")
        
        cfg = types.GenerateVideosConfig(
            aspect_ratio=ASPECT_RATIO,
            resolution=RESOLUTION,
            seed=SEED,
            negative_prompt=NEGATIVE_PROMPT,
            # Si tu SDK/cuenta no soporta system_prompt, elimina esta línea.
            system_prompt=SYSTEM_STYLE
        )
        
        op = client.models.generate_videos(
            model=MODEL,
            prompt=prompt,
            image=types.Image(image_bytes=image_bytes, mime_type="image/jpeg") if image_bytes else None,
            config=cfg,
        )
        
        # Timeout para evitar esperas infinitas
        max_wait_time = 600  # 10 minutos
        start_time = time.time()
        
        while not hasattr(op, "done") or not op.done:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                raise TimeoutError(f"Timeout esperando generación de video después de {max_wait_time} segundos")
            
            console(f"Esperando clip... ({elapsed_time:.0f}s)", getattr(op, "name", ""))
            logger.info(f"Esperando generación de video... {elapsed_time:.0f}s")
            time.sleep(8)
            op = client.operations.get(op)

        if not op.response or not op.response.generated_videos:
            raise RuntimeError("No se generó ningún video")
            
        video = op.response.generated_videos[0].video
        client.files.download(file=video).save(out_path)
        
        # Verificar que el archivo se creó correctamente
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError(f"El archivo de video no se creó correctamente: {out_path}")
            
        logger.info(f"Video generado exitosamente: {out_path}")
        console("Clip generado:", out_path)
        
    except Exception as e:
        logger.error(f"Error generando video con Veo 3: {e}")
        console(f"ERROR: {e}")
        raise

# ---------- Slideshow (Desarrollo 8s con 5 fotos) ----------
def make_silent_audio_ffmpeg(duration: int) -> str:
    """Crea un archivo de audio silencioso usando ffmpeg."""
    import tempfile
    temp_audio = tempfile.mktemp(suffix='.aac')

    # Crear audio silencioso de duración especificada
    (
        ffmpeg
        .input('anullsrc', f='lavfi', t=duration)
        .output(temp_audio, acodec='aac', ar='44100', ac='1')
        .run(capture_stdout=True, capture_stderr=True)
    )

    return temp_audio

def make_development_slideshow(auto_paths: List[str], out_path: str, total_seconds: int = 8, fps: int = FPS):
    """
    Crea un slideshow vertical 1080x1920 (9:16) de 'total_seconds' con 5 imágenes,
    usando un zoom sutil (Ken Burns). Exporta con audio silencioso para facilitar concat.
    """
    try:
        logger.info(f"Iniciando creación de slideshow: {out_path}")

        if len(auto_paths) != 5:
            raise RuntimeError("Debes seleccionar exactamente 5 fotos del auto (EXTERIOR).")

        # Validar todas las imágenes antes de procesarlas
        for i, img_path in enumerate(auto_paths):
            if not validate_image_file(img_path):
                raise RuntimeError(f"La imagen #{i+1} no es válida: {img_path}")

        W, H = 1080, 1920
        per = total_seconds / 5.0  # ~1.6s por foto

        # Crear clips individuales con zoom Ken Burns
        clips = []
        for i, img in enumerate(auto_paths):
            logger.info(f"Procesando imagen {i+1}/5: {img}")

            try:
                # Crear clip con zoom Ken Burns
                temp_output = tempfile.mktemp(suffix=f'_clip_{i}.mp4')

                # Calcular zoom parameters para Ken Burns effect
                zoom_factor = 1.05  # Zoom sutil

                # Crear video con Ken Burns effect usando ffmpeg
                (
                    ffmpeg
                    .input(img, loop=1, t=per)
                    .filter('scale', f'iw*{zoom_factor}', f'ih*{zoom_factor}')
                    .filter('crop', W, H)
                    .filter('zoompan',
                           f'd={fps*per}:x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):z=zoom')
                    .output(temp_output, r=fps, vcodec='libx264', pix_fmt='yuv420p')
                    .run(capture_stdout=True, capture_stderr=True)
                )

                clips.append(temp_output)

            except Exception as e:
                logger.error(f"Error procesando imagen {img}: {e}")
                raise RuntimeError(f"Error procesando imagen {i+1}: {e}")

        # Concatenar clips
        logger.info("Concatenando clips del slideshow")

        # Crear archivo temporal para concatenación
        concat_file = tempfile.mktemp(suffix='.txt')
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        # Concatenar videos
        temp_video = tempfile.mktemp(suffix='_slideshow.mp4')
        (
            ffmpeg
            .input(concat_file, format='concat', safe=0)
            .output(temp_video, c='copy')
            .run(capture_stdout=True, capture_stderr=True)
        )

        # Crear audio silencioso
        silent_audio = make_silent_audio_ffmpeg(total_seconds)

        # Combinar video con audio silencioso
        (
            ffmpeg
            .input(temp_video)
            .input(silent_audio)
            .output(out_path, vcodec='copy', acodec='aac', shortest=None)
            .run(capture_stdout=True, capture_stderr=True)
        )

        # Limpiar archivos temporales
        try:
            os.unlink(concat_file)
            os.unlink(temp_video)
            os.unlink(silent_audio)
            for clip in clips:
                if os.path.exists(clip):
                    os.unlink(clip)
        except:
            pass

        # Verificar que el archivo se creó correctamente
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError(f"El slideshow no se creó correctamente: {out_path}")

        logger.info(f"Slideshow creado exitosamente: {out_path}")

    except Exception as e:
        logger.error(f"Error creando slideshow: {e}")
        raise

# =========================
# INTERFAZ CUSTOMTKINTER
# =========================
class VeoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("Generador Veo3 (9:16) — 8s + 8s + 8s (24s total)")
        self.geometry("900x760")

        # Variables
        self.actor_path = ctk.StringVar()
        self.auto_paths = []
        self.actor_name = ctk.StringVar()
        self.modelo_auto = ctk.StringVar()

        self.bienvenida_text = ctk.StringVar()
        self.desarrollo_text = ctk.StringVar()
        self.despedida_text = ctk.StringVar()

        self.out_name = ctk.StringVar(value="spot_modelo_24s_vertical.mp4")

        self._build_ui()

    def _build_ui(self):
        # Datos básicos
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(top, text="Actor:").grid(row=0, column=0, sticky="w", padx=6)
        ctk.CTkEntry(top, textvariable=self.actor_name, width=200).grid(row=0, column=1, padx=6)
        ctk.CTkLabel(top, text="Modelo Auto:").grid(row=0, column=2, sticky="w", padx=6)
        ctk.CTkEntry(top, textvariable=self.modelo_auto, width=200).grid(row=0, column=3, padx=6)

        # Selección de archivos
        files_frame = ctk.CTkFrame(self)
        files_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(files_frame, text="Foto Actor:").grid(row=0, column=0, padx=6, sticky="w")
        ctk.CTkEntry(files_frame, textvariable=self.actor_path, width=400).grid(row=0, column=1, padx=6)
        ctk.CTkButton(files_frame, text="Elegir...", command=self.select_actor).grid(row=0, column=2, padx=6)

        ctk.CTkLabel(files_frame, text="Fotos Auto (EXTERIOR, exactamente 5):").grid(row=1, column=0, padx=6, sticky="w")
        self.auto_list = ctk.CTkTextbox(files_frame, height=90, width=400)
        self.auto_list.grid(row=1, column=1, padx=6)
        ctk.CTkButton(files_frame, text="Elegir 5...", command=self.select_autos).grid(row=1, column=2, padx=6)

        # Textos
        text_frame = ctk.CTkFrame(self)
        text_frame.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(text_frame, text="Bienvenida (8s):").grid(row=0, column=0, padx=6, sticky="w")
        ctk.CTkEntry(text_frame, textvariable=self.bienvenida_text, width=600).grid(row=0, column=1, padx=6)

        ctk.CTkLabel(text_frame, text="Desarrollo (8s, 5 fotos):").grid(row=1, column=0, padx=6, sticky="w")
        ctk.CTkEntry(text_frame, textvariable=self.desarrollo_text, width=600).grid(row=1, column=1, padx=6)

        ctk.CTkLabel(text_frame, text="Despedida (8s):").grid(row=2, column=0, padx=6, sticky="w")
        ctk.CTkEntry(text_frame, textvariable=self.despedida_text, width=600).grid(row=2, column=1, padx=6)

        # Salida
        outf = ctk.CTkFrame(self)
        outf.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(outf, text="Archivo de salida:").pack(side="left", padx=6)
        ctk.CTkEntry(outf, textvariable=self.out_name, width=280).pack(side="left", padx=6)

        # Botón
        ctk.CTkButton(self, text="Generar Video (24s)", command=self.run_thread).pack(pady=10)

        # Consola
        self.console = ctk.CTkTextbox(self, height=240)
        self.console.pack(fill="both", expand=True, padx=16, pady=10)
        self.log("Listo. 3 clips de 8s (total 24s). El desarrollo usa exactamente 5 fotos.")

    # UI helpers
    def log(self, *args):
        msg = " ".join(str(a) for a in args)
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        print(msg)

    def select_actor(self):
        path = filedialog.askopenfilename(title="Selecciona foto del actor",
                                          filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if path:
            self.actor_path.set(path)
            self.log("Actor seleccionado:", path)

    def select_autos(self):
        paths = filedialog.askopenfilenames(title="Selecciona EXACTAMENTE 5 fotos del auto (EXTERIOR)",
                                            filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if paths:
            if len(paths) != 5:
                messagebox.showerror("Error", "Debes seleccionar exactamente 5 fotos del auto (EXTERIOR).")
                return
            self.auto_paths = list(paths)
            self.auto_list.delete("1.0", "end")
            for p in paths:
                self.auto_list.insert("end", p + "\n")
            self.log("5 fotos de auto cargadas.")

    def run_thread(self):
        threading.Thread(target=self.generate_video, daemon=True).start()

    # =========================
    # LÓGICA PRINCIPAL (3 CLIPS X 8s)
    # =========================
    def generate_video(self):
        try:
            logger.info("=== INICIANDO GENERACIÓN DE VIDEO ===")
            self.log("🚀 Iniciando generación de video...")
            
            # ===== VALIDACIONES PREVIAS =====
            self.log("🔍 Realizando validaciones previas...")
            
            # Verificar FFmpeg
            if not check_ffmpeg_availability():
                raise RuntimeError("❌ FFmpeg no está instalado o no está disponible en el PATH del sistema.\n"
                                 "Instala FFmpeg desde: https://ffmpeg.org/download.html")
            
            # Verificar espacio en disco
            if not check_disk_space(2.0):
                raise RuntimeError("❌ Espacio insuficiente en disco (se requieren al menos 2GB libres)")
            
            # Verificar API key
            api_key = os.getenv("GEMINI_API_KEY")
            if not validate_api_key(api_key):
                raise RuntimeError("❌ API key de Gemini no configurada o inválida.\n"
                                 "Configura la variable de entorno GEMINI_API_KEY")

            # Validar datos básicos
            actor_name = self.actor_name.get().strip()
            modelo = self.modelo_auto.get().strip()
            if not actor_name or not modelo:
                raise RuntimeError("❌ Falta nombre de actor o modelo de auto")

            # Validar imagen del actor
            actor_path = self.actor_path.get().strip()
            if not validate_image_file(actor_path):
                raise RuntimeError(f"❌ La imagen del actor no es válida: {actor_path}")

            # Validar imágenes del auto
            if len(self.auto_paths) != 5:
                raise RuntimeError("❌ Debes seleccionar exactamente 5 fotos del auto (EXTERIOR)")
            
            for i, auto_path in enumerate(self.auto_paths):
                if not validate_image_file(auto_path):
                    raise RuntimeError(f"❌ La imagen del auto #{i+1} no es válida: {auto_path}")

            self.log("✅ Todas las validaciones pasaron correctamente")

            # ===== PREPARACIÓN DE TEXTOS =====
            bienvenida = self.bienvenida_text.get().strip() or f"¡Hola! Soy {actor_name}. Hoy te presento el {modelo}."
            if modelo.lower() not in bienvenida.lower():
                bienvenida = f"¡Hola! Soy {actor_name}. Hoy te presento el {modelo}. " + bienvenida

            desarrollo = self.desarrollo_text.get().strip() or \
                "Observa el EXTERIOR: parrilla, faros, llantas y emblemas. Auto inmóvil, sin interior."
            despedida = self.despedida_text.get().strip() or \
                f"Gracias por ver el EXTERIOR del {modelo}. ¡Nos vemos pronto!"

            # ===== INICIALIZACIÓN =====
            self.log("🔧 Inicializando cliente de Gemini...")
            client = genai.Client(api_key=api_key)

            # Cargar imágenes
            self.log("📷 Cargando imágenes...")
            actor_img_bytes = load_image_bytes(actor_path)
            if not actor_img_bytes:
                raise RuntimeError("❌ No se pudo cargar la foto del actor")

            car_imgs_bytes = [load_image_bytes(p) for p in self.auto_paths]
            if not all(car_imgs_bytes):
                raise RuntimeError("❌ No se pudieron cargar todas las fotos del auto")

            # Crear directorio temporal
            temp_dir = tempfile.mkdtemp(prefix="veo3_3x8s_")
            logger.info(f"Directorio temporal: {temp_dir}")
            clips_final = []

            # ===== GENERACIÓN DE CLIPS =====
            
            # 1) Bienvenida (8s) con Veo 3
            self.log("🎬 [1/3] Generando Bienvenida con IA (8s)...")
            prompt_b = build_prompt_vertical(bienvenida, "bienvenida")
            raw_b = os.path.join(temp_dir, "bienvenida_raw.mp4")
            out_b = os.path.join(temp_dir, "bienvenida_8s.mp4")
            
            generate_veo_video(client, prompt_b, actor_img_bytes, raw_b, console=self.log)
            self.log("⏱️ Ajustando Bienvenida a 8s exactos...")
            ensure_exact_duration(raw_b, SEG_DURATIONS["bienvenida"], out_b)
            clips_final.append(out_b)

            # 2) Desarrollo (8s) slideshow con 5 fotos (sin Veo 3)
            self.log("🖼️ [2/3] Creando Desarrollo (slideshow 5 fotos, 8s)...")
            dev_path = os.path.join(temp_dir, "desarrollo_8s.mp4")
            make_development_slideshow(self.auto_paths, dev_path, total_seconds=SEG_DURATIONS["desarrollo"], fps=FPS)
            clips_final.append(dev_path)

            # 3) Despedida (8s) con Veo 3 (usa última foto del auto como referencia)
            self.log("🎬 [3/3] Generando Despedida con IA (8s)...")
            prompt_d = build_prompt_vertical(despedida, "despedida", "3/4 trasero, luces inmóviles")
            raw_d = os.path.join(temp_dir, "despedida_raw.mp4")
            out_d = os.path.join(temp_dir, "despedida_8s.mp4")
            
            generate_veo_video(client, prompt_d, car_imgs_bytes[-1], raw_d, console=self.log)
            self.log("⏱️ Ajustando Despedida a 8s exactos...")
            ensure_exact_duration(raw_d, SEG_DURATIONS["despedida"], out_d)
            clips_final.append(out_d)

            # ===== CONCATENACIÓN FINAL =====
            out_file = (self.out_name.get() or "spot_modelo_24s_vertical.mp4").strip()
            if not out_file.endswith(".mp4"):
                out_file += ".mp4"

            self.log("🔗 Concatenando clips finales (8 + 8 + 8 = 24s)...")
            concat_clips(clips_final, out_file)

            # Verificar archivo final
            if not os.path.exists(out_file) or os.path.getsize(out_file) == 0:
                raise RuntimeError(f"❌ El video final no se creó correctamente: {out_file}")

            # ===== ÉXITO =====
            file_size_mb = os.path.getsize(out_file) / (1024 * 1024)
            self.log(f"✅ ¡VIDEO GENERADO EXITOSAMENTE!")
            self.log(f"📁 Archivo: {out_file}")
            self.log(f"📏 Tamaño: {file_size_mb:.2f} MB")
            self.log(f"⏱️ Duración: 24 segundos (3x8s)")
            self.log("🎯 Reglas aplicadas: EXTERIOR only, auto inmóvil, fidelidad total")
            
            logger.info(f"=== VIDEO GENERADO EXITOSAMENTE: {out_file} ===")
            
            # Mostrar mensaje de éxito
            messagebox.showinfo("¡Éxito!", 
                              f"Video generado exitosamente:\n\n"
                              f"📁 {out_file}\n"
                              f"📏 {file_size_mb:.2f} MB\n"
                              f"⏱️ 24 segundos")

        except subprocess.CalledProcessError as e:
            error_msg = f"❌ Error en FFmpeg: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            self.log(error_msg)
            messagebox.showerror("Error de FFmpeg", error_msg)
            
        except MemoryError as e:
            error_msg = "❌ Memoria insuficiente para procesar las imágenes"
            logger.error(error_msg)
            self.log(error_msg)
            messagebox.showerror("Error de Memoria", 
                               "Memoria insuficiente.\n"
                               "Intenta usar imágenes de menor resolución.")
            
        except TimeoutError as e:
            error_msg = f"❌ Timeout: {e}"
            logger.error(error_msg)
            self.log(error_msg)
            messagebox.showerror("Timeout", str(e))
            
        except FileNotFoundError as e:
            error_msg = f"❌ Archivo no encontrado: {e}"
            logger.error(error_msg)
            self.log(error_msg)
            messagebox.showerror("Archivo No Encontrado", str(e))
            
        except Exception as e:
            error_msg = f"❌ ERROR: {type(e).__name__}: {e}"
            logger.error(error_msg)
            self.log(error_msg)
            messagebox.showerror("Error Inesperado", 
                               f"Se produjo un error inesperado:\n\n"
                               f"{type(e).__name__}: {str(e)}\n\n"
                               f"Revisa el archivo 'makevid.log' para más detalles.")


if __name__ == "__main__":
    app = VeoApp()
    app.mainloop()
