# Renamer de videos con customtkinter, extracción de frame y OpenAI
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import cv2
import numpy as np
from PIL import Image
import io
import base64
import threading
import datetime
import json
try:
	from openai import OpenAI
except ImportError:
	OpenAI = None

# Configuración
API_KEY = "YOUR_OPENAI_API_KEY"
EXTS = (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v")

class RenamerApp:
	def __init__(self):
		ctk.set_appearance_mode("dark")
		ctk.set_default_color_theme("blue")
		self.root = ctk.CTk()
		self.root.title("Renombrador de Videos IA")
		self.root.geometry("900x700")

		self.dir_var = tk.StringVar()
		self.checks = {}

		ctk.CTkLabel(self.root, text="Renombrador de Videos IA", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)
		main = ctk.CTkFrame(self.root)
		main.pack(fill="both", expand=True, padx=16, pady=10)

		# Selección de carpeta
		top = ctk.CTkFrame(main)
		top.pack(fill="x", padx=10, pady=8)
		ctk.CTkLabel(top, text="Carpeta de videos:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=8, pady=(8, 4))
		row = ctk.CTkFrame(top, fg_color="transparent")
		row.pack(fill="x", padx=8, pady=(0,8))
		ctk.CTkEntry(row, textvariable=self.dir_var, placeholder_text="Selecciona la carpeta...", width=600).pack(side="left", fill="x", expand=True, padx=(0,8))
		ctk.CTkButton(row, text="Explorar", command=self.pick_folder, width=100).pack(side="left")

		# Listado de videos
		box = ctk.CTkFrame(main)
		box.pack(fill="both", expand=True, padx=10, pady=8)
		self.scroll = ctk.CTkScrollableFrame(box)
		self.scroll.pack(fill="both", expand=True)
		self.empty = ctk.CTkLabel(self.scroll, text="Selecciona una carpeta con videos.", text_color="gray")
		self.empty.pack(pady=20)

		# Botonera
		btns = ctk.CTkFrame(main, fg_color="transparent")
		btns.pack(fill="x", padx=10, pady=6)
		ctk.CTkButton(btns, text="Seleccionar todos", command=self.select_all).pack(side="left", padx=(0,8))
		ctk.CTkButton(btns, text="Deseleccionar", command=self.unselect_all).pack(side="left")
		self.run_btn = ctk.CTkButton(btns, text="Renombrar videos", command=self.run_process)
		self.run_btn.pack(side="right")

		# Log en pantalla
		ctk.CTkLabel(main, text="Log:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10)
		self.log = ctk.CTkTextbox(main, height=200)
		self.log.pack(fill="x", padx=10, pady=(4,10))

	def pick_folder(self):
		d = filedialog.askdirectory(title="Selecciona carpeta con videos")
		if not d:
			return
		self.dir_var.set(d)
		self.list_videos(d)

	def list_videos(self, folder):
		for w in self.scroll.winfo_children():
			w.destroy()
		self.checks.clear()
		files = []
		try:
			items = os.listdir(folder)
			for f in items:
				if os.path.isfile(os.path.join(folder, f)) and os.path.splitext(f)[1].lower() in EXTS:
					files.append(f)
		except Exception as e:
			self.ui_log(f"Error al listar carpeta: {e}")
			return
		if not files:
			self.empty = ctk.CTkLabel(self.scroll, text="No hay videos en esta carpeta.", text_color="orange")
			self.empty.pack(pady=20)
			self.ui_log("No se encontraron videos.")
			return
		for f in files:
			row = ctk.CTkFrame(self.scroll)
			row.pack(fill="x", padx=6, pady=3)
			v = tk.BooleanVar(value=True)
			ctk.CTkCheckBox(row, text=f, variable=v).pack(side="left", anchor="w")
			self.checks[os.path.join(folder, f)] = v
		self.ui_log(f"Encontrados {len(files)} videos.")

	def select_all(self):
		for v in self.checks.values():
			v.set(True)
		self.ui_log("Todos seleccionados.")

	def unselect_all(self):
		for v in self.checks.values():
			v.set(False)
		self.ui_log("Todos deseleccionados.")

	def run_process(self):
		paths = [p for p, v in self.checks.items() if v.get()]
		if not paths:
			self.ui_log("Selecciona al menos un video.")
			return
		
		# Verificar conexión con OpenAI antes de procesar
		if not self._test_openai_connection():
			self.ui_log("Error: No se puede conectar con OpenAI. Verifica tu API Key y conexión.")
			return
			
		self.run_btn.configure(state="disabled", text="Procesando...")
		threading.Thread(target=self._worker, args=(paths,), daemon=True).start()

	def _test_openai_connection(self):
		"""Prueba la conexión con OpenAI con una imagen de prueba simple"""
		if OpenAI is None:
			self.ui_log("Error: Librería OpenAI no instalada.")
			return False
			
		if not API_KEY or API_KEY == "PON_AQUI_TU_API_KEY_OPENAI":
			self.ui_log("Error: API Key de OpenAI no configurada.")
			return False
		
		try:
			client = OpenAI(api_key=API_KEY.strip())
			
			# Crear una imagen de prueba simple (100x100 píxeles negros)
			test_image = np.zeros((100, 100, 3), dtype=np.uint8)
			b64 = self._img_b64(test_image)
			
			self.ui_log("Probando conexión con OpenAI...")
			
			resp = client.chat.completions.create(
				model="gpt-4o",
				messages=[{
					"role":"user",
					"content":[
						{"type":"text","text":"Describe brevemente esta imagen en una palabra."},
						{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}","detail":"low"}}
					]
				}],
				max_tokens=10,
				temperature=0
			)
			
			if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
				self.ui_log("✓ Conexión con OpenAI exitosa.")
				return True
			else:
				self.ui_log("✗ OpenAI no devolvió respuesta válida.")
				return False
				
		except Exception as e:
			error_msg = str(e)
			if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
				self.ui_log(f"✗ Error de API Key: Verifica que tu clave sea válida.")
			elif "rate_limit" in error_msg.lower():
				self.ui_log(f"✗ Límite de velocidad excedido. Espera un momento.")
			elif "quota" in error_msg.lower():
				self.ui_log(f"✗ Cuota de OpenAI excedida. Verifica tu plan.")
			elif "network" in error_msg.lower() or "connection" in error_msg.lower():
				self.ui_log(f"✗ Error de conexión. Verifica tu internet.")
			else:
				self.ui_log(f"✗ Error OpenAI: {e}")
			return False

	def _worker(self, paths):
		ok = err = 0
		for i, path in enumerate(paths, 1):
			self.ui_log(f"[{i}/{len(paths)}] Procesando: {os.path.basename(path)}")
			try:
				if self.process_one(path):
					ok += 1
				else:
					err += 1
			except Exception as e:
				self.ui_log(f"Error inesperado: {e}")
				err += 1
		self.ui_log(f"Fin. OK: {ok} | Errores: {err}")
		self.run_btn.configure(state="normal", text="Renombrar videos")

	def process_one(self, video_path):
		# 1. Extraer frame (5s, 1s, 0s)
		frame = self._grab_frame(video_path)
		if frame is None:
			self.ui_log("No se pudo extraer frame.")
			return False
		# 2. Guardar frame (opcional)
		try:
			frame_path = os.path.splitext(video_path)[0] + "_frame.jpg"
			Image.fromarray(frame).save(frame_path, format="JPEG", quality=92)
			self.ui_log(f"Frame guardado: {os.path.basename(frame_path)}")
		except Exception as e:
			self.ui_log(f"No se pudo guardar el frame: {e}")
		# 3. Analizar con OpenAI
		info = self._ask_openai(frame)
		if not info:
			self.ui_log("OpenAI no devolvió datos válidos.")
			return False
		# 4. Formar nuevo nombre en formato: Canal_Calidad_Fecha_Hora_segXXX
		canal = self._s(info.get("canal"))
		hora = self._s(info.get("hora"))
		
		if not canal or canal.upper() == "DESCONOCIDO":
			self.ui_log("Canal no identificado. No se puede renombrar.")
			return False
			
		if not hora or hora.upper() == "DESCONOCIDO":
			self.ui_log("Hora no identificada. No se puede renombrar.")
			return False
		
		# Obtener calidad del video
		calidad = self._get_video_quality(video_path)
		
		# Obtener fecha actual
		fecha = datetime.datetime.now().strftime("%Y-%m-%d")
		
		# Limpiar y formatear hora (convertir HH:MM a HH-MM-SS)
		hora_formateada = self._format_time(hora)
		
		# Limpiar nombre del canal
		canal_limpio = self._clean_channel_name(canal)
		
		# Generar número de segmento
		seg_num = self._get_next_segment_number(os.path.dirname(video_path), canal_limpio, calidad, fecha, hora_formateada)
		
		# Formar nombre: Canal_Calidad_Fecha_Hora_segXXX.ext
		nuevo_nombre = f"{canal_limpio}_{calidad}_{fecha}_{hora_formateada}_seg{seg_num:03d}{os.path.splitext(video_path)[1]}"
		new_path = os.path.join(os.path.dirname(video_path), nuevo_nombre)
		
		# Renombrar
		try:
			os.rename(video_path, new_path)
			self.ui_log(f"✅ Renombrado: {os.path.basename(video_path)} → {nuevo_nombre}")
			
			# Mostrar modal informativo después del renombrado exitoso
			self._show_rename_info(os.path.basename(video_path), nuevo_nombre)
			
			return True
		except Exception as e:
			self.ui_log(f"Error al renombrar: {e}")
			return False

	def _grab_frame(self, video_path):
		try:
			cap = cv2.VideoCapture(video_path)
			if not cap.isOpened():
				return None
			for ms in (5000, 1000, 0):
				cap.set(cv2.CAP_PROP_POS_MSEC, ms)
				ok, f = cap.read()
				if ok and f is not None:
					cap.release()
					return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
			cap.release()
			return None
		except Exception:
			return None

	def _img_b64(self, arr):
		img = Image.fromarray(arr)
		max_side = 1024
		if max(img.size) > max_side:
			r = max_side / max(img.size)
			img = img.resize((int(img.size[0]*r), int(img.size[1]*r)), Image.Resampling.LANCZOS)
		buf = io.BytesIO()
		img.save(buf, format="JPEG", quality=85)
		return base64.b64encode(buf.getvalue()).decode("utf-8")

	def _ask_openai(self, frame_rgb, max_retries=2):
		if OpenAI is None:
			self.ui_log("Error: Librería OpenAI no instalada. Instala con: pip install openai")
			return None
			
		if not API_KEY or API_KEY == "PON_AQUI_TU_API_KEY_OPENAI":
			self.ui_log("Error: API Key de OpenAI no configurada.")
			return None
		
		for attempt in range(max_retries + 1):
			try:
				client = OpenAI(api_key=API_KEY.strip())
				b64 = self._img_b64(frame_rgb)
				
				if attempt == 0:
					self.ui_log(f"Imagen codificada: {len(b64)} caracteres")
				else:
					self.ui_log(f"Reintentando... (intento {attempt + 1}/{max_retries + 1})")
				
				prompt = (
					"Analiza esta imagen de TV y extrae la información visible. "
					"Responde SOLO en formato JSON válido:\n"
					'{"hora": "HH:MM", "canal": "nombre del canal", "programa": "nombre del programa"}\n\n'
					"Reglas:\n"
					"- Usa EXACTAMENTE el texto visible en pantalla\n"
					"- Si algo no es visible o legible, usa 'DESCONOCIDO'\n"
					"- NO agregues información externa\n"
					"- SOLO responde con JSON válido, sin texto adicional"
				)
				
				self.ui_log("Enviando petición a OpenAI...")
				resp = client.chat.completions.create(
					model="gpt-4o",
					messages=[{
						"role":"user",
						"content":[
							{"type":"text","text":prompt},
							{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}","detail":"high"}}
						]
					}],
					max_tokens=300,
					temperature=0
				)
				
				if not resp.choices or not resp.choices[0].message:
					self.ui_log("Error: OpenAI no devolvió respuesta válida")
					if attempt < max_retries:
						continue
					return None
					
				text = (resp.choices[0].message.content or "").strip()
				self.ui_log(f"Respuesta OpenAI: {text}")
				
				if not text:
					self.ui_log("Error: Respuesta vacía de OpenAI")
					if attempt < max_retries:
						continue
					return None
				
				# Intentar extraer JSON de la respuesta
				json_text = self._extract_json_from_text(text)
				if not json_text:
					self.ui_log("Error: No se encontró JSON válido en la respuesta")
					if attempt < max_retries:
						continue
					return None
				
				try:
					data = json.loads(json_text)
					if isinstance(data, dict):
						# Validar que tiene las claves esperadas
						required_keys = {"hora", "canal", "programa"}
						if not required_keys.issubset(data.keys()):
							self.ui_log(f"Error: JSON no tiene las claves requeridas. Recibido: {list(data.keys())}")
							if attempt < max_retries:
								continue
							return None
						self.ui_log(f"JSON parseado correctamente: {data}")
						return data
					else:
						self.ui_log(f"Error: La respuesta no es un diccionario: {type(data)}")
						if attempt < max_retries:
							continue
						return None
				except json.JSONDecodeError as je:
					self.ui_log(f"Error al parsear JSON: {je}")
					self.ui_log(f"Texto JSON extraído: '{json_text}'")
					if attempt < max_retries:
						continue
					return None
					
			except Exception as e:
				error_msg = str(e)
				if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
					self.ui_log(f"Error de API Key: {e}")
					return None  # No reintentar errores de autenticación
				elif "rate_limit" in error_msg.lower():
					self.ui_log(f"Error de límite de velocidad: {e}")
					if attempt < max_retries:
						import time
						time.sleep(5)  # Esperar 5 segundos antes de reintentar
						continue
				elif "quota" in error_msg.lower():
					self.ui_log(f"Error de cuota excedida: {e}")
					return None  # No reintentar errores de cuota
				else:
					self.ui_log(f"Error OpenAI: {e}")
					if attempt < max_retries:
						continue
				
				if attempt == max_retries:
					return None
		
		return None

	def _extract_json_from_text(self, text):
		"""Extrae JSON válido de una respuesta de texto que puede tener contenido adicional"""
		import re
		
		# Buscar JSON que comience con { y termine con }
		json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
		matches = re.findall(json_pattern, text)
		
		for match in matches:
			try:
				# Verificar si es JSON válido
				json.loads(match)
				return match
			except json.JSONDecodeError:
				continue
		
		# Si no encuentra JSON con regex, intentar limpiar la respuesta
		lines = text.split('\n')
		for line in lines:
			line = line.strip()
			if line.startswith('{') and line.endswith('}'):
				try:
					json.loads(line)
					return line
				except json.JSONDecodeError:
					continue
		
		return None

	def _get_video_quality(self, video_path):
		"""Detecta la calidad del video analizando sus propiedades"""
		try:
			cap = cv2.VideoCapture(video_path)
			if not cap.isOpened():
				return "480p"  # Default
			
			width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
			height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
			cap.release()
			
			# Determinar calidad basada en resolución
			if height >= 2160:
				return "4K"
			elif height >= 1440:
				return "1440p"
			elif height >= 1080:
				return "1080p"
			elif height >= 720:
				return "720p"
			elif height >= 480:
				return "480p"
			else:
				return "360p"
		except Exception:
			return "480p"  # Default en caso de error

	def _format_time(self, hora_str):
		"""Convierte hora de formato HH:MM a HH-MM-SS"""
		try:
			import re
			# Buscar patrón HH:MM
			match = re.search(r'(\d{1,2}):(\d{2})', hora_str)
			if match:
				hh, mm = match.groups()
				return f"{hh.zfill(2)}-{mm}-00"  # Agregar segundos como 00
			else:
				# Si no encuentra el patrón, usar hora actual
				return datetime.datetime.now().strftime("%H-%M-%S")
		except Exception:
			return datetime.datetime.now().strftime("%H-%M-%S")

	def _clean_channel_name(self, canal):
		"""Limpia el nombre del canal para uso en nombres de archivo"""
		import re
		
		# Limpiar términos no deseados primero
		canal = canal.strip()
		
		# Remover "NUEVA CARPETA" y términos similares
		unwanted_terms = [
			r'NUEVA\s*CARPETA\s*-?\s*',
			r'nueva\s*carpeta\s*-?\s*', 
			r'New\s*Folder\s*-?\s*',
			r'Carpeta\s*-?\s*',
			r'folder\s*-?\s*'
		]
		
		for term in unwanted_terms:
			canal = re.sub(term, '', canal, flags=re.IGNORECASE)
		
		# Limpiar guiones y espacios extra al inicio/final
		canal = re.sub(r'^[-\s]+|[-\s]+$', '', canal)
		
		# Remover caracteres especiales pero mantener espacios temporalmente
		canal_temp = re.sub(r'[<>:"/\\|?*]+', '', canal)
		
		# Convertir espacios a formato camelCase o sin espacios
		# Ejemplo: "El Despertador" -> "ElDespertador"
		words = canal_temp.split()
		if len(words) > 1:
			# Capitalizar primera letra de cada palabra y unir
			canal_limpio = ''.join(word.capitalize() for word in words)
		else:
			canal_limpio = canal_temp.replace(' ', '')
		
		# Remover acentos y caracteres especiales
		replacements = {
			'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
			'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
			'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'
		}
		for old, new in replacements.items():
			canal_limpio = canal_limpio.replace(old, new)
		
		# Si queda vacío después de limpiar, usar default
		if not canal_limpio or len(canal_limpio) < 2:
			canal_limpio = "Canal"
			
		return canal_limpio

	def _get_next_segment_number(self, directory, canal, calidad, fecha, hora):
		"""Genera el próximo número de segmento disponible"""
		try:
			# Buscar archivos existentes con el mismo patrón
			pattern = f"{canal}_{calidad}_{fecha}_{hora}_seg"
			existing_files = []
			
			for filename in os.listdir(directory):
				if filename.startswith(pattern):
					# Extraer número de segmento
					import re
					match = re.search(r'seg(\d+)', filename)
					if match:
						existing_files.append(int(match.group(1)))
			
			# Devolver el siguiente número disponible
			if existing_files:
				return max(existing_files) + 1
			else:
				return 1
		except Exception:
			return 1

	def _show_rename_info(self, old_name, new_name):
		"""Muestra modal informativo con el renombrado realizado"""
		# Crear ventana modal
		modal = ctk.CTkToplevel(self.root)
		modal.title("Archivo Renombrado")
		modal.geometry("800x350")
		modal.transient(self.root)
		modal.grab_set()
		
		# Centrar modal
		modal.update_idletasks()
		x = (modal.winfo_screenwidth() // 2) - (800 // 2)
		y = (modal.winfo_screenheight() // 2) - (350 // 2)
		modal.geometry(f"800x350+{x}+{y}")
		
		# Título
		title_label = ctk.CTkLabel(modal, text="✅ Archivo Renombrado Exitosamente", 
								 font=ctk.CTkFont(size=20, weight="bold"),
								 text_color="#51cf66")
		title_label.pack(pady=20)
		
		# Frame principal
		main_frame = ctk.CTkFrame(modal)
		main_frame.pack(fill="both", expand=True, padx=20, pady=10)
		
		# Nombre viejo
		old_frame = ctk.CTkFrame(main_frame)
		old_frame.pack(fill="x", padx=15, pady=10)
		
		ctk.CTkLabel(old_frame, text="📁 NOMBRE ANTERIOR:", 
					font=ctk.CTkFont(size=14, weight="bold"), 
					text_color="#ff6b6b").pack(anchor="w", padx=10, pady=(10,5))
		
		old_text = ctk.CTkTextbox(old_frame, height=50, wrap="word")
		old_text.pack(fill="x", padx=10, pady=(0,10))
		old_text.insert("1.0", old_name)
		old_text.configure(state="disabled")
		
		# Flecha
		arrow_label = ctk.CTkLabel(main_frame, text="⬇️ RENOMBRADO A ⬇️", 
								 font=ctk.CTkFont(size=16, weight="bold"),
								 text_color="#4ecdc4")
		arrow_label.pack(pady=8)
		
		# Nombre nuevo
		new_frame = ctk.CTkFrame(main_frame)
		new_frame.pack(fill="x", padx=15, pady=10)
		
		ctk.CTkLabel(new_frame, text="✨ NOMBRE NUEVO:", 
					font=ctk.CTkFont(size=14, weight="bold"), 
					text_color="#51cf66").pack(anchor="w", padx=10, pady=(10,5))
		
		new_text = ctk.CTkTextbox(new_frame, height=50, wrap="word")
		new_text.pack(fill="x", padx=10, pady=(0,10))
		new_text.insert("1.0", new_name)
		new_text.configure(state="disabled")
		
		# Botón OK centrado
		button_frame = ctk.CTkFrame(modal, fg_color="transparent")
		button_frame.pack(fill="x", padx=20, pady=15)
		
		def on_ok():
			modal.destroy()
		
		ok_btn = ctk.CTkButton(button_frame, text="✅ OK", 
							  command=on_ok, width=120,
							  fg_color="#51cf66", hover_color="#40c057")
		ok_btn.pack(anchor="center")
		
		# Hacer que Enter y Escape cierren el modal
		def on_key(event):
			if event.keysym in ["Return", "Escape"]:
				on_ok()
		
		modal.bind("<Key>", on_key)
		modal.focus_set()
		
		# Auto-cerrar después de 3 segundos (opcional)
		modal.after(3000, on_ok)
		
		# Esperar a que se cierre el modal
		modal.wait_window()

	def _clean(self, s):
		import re
		return re.sub(r'[<>:"/\\|?*]+', "", s).strip()

	def _s(self, v):
		try:
			return str(v or "").strip()
		except Exception:
			return ""

	def ui_log(self, msg):
		ts = datetime.datetime.now().strftime("%H:%M:%S")
		self.log.insert("end", f"[{ts}] {msg}\n")
		self.log.see("end")
		self.root.update_idletasks()

	def run(self):
		self.root.mainloop()

if __name__ == "__main__":
	RenamerApp().run()
