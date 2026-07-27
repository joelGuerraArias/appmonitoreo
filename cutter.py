import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox, scrolledtext
# from moviepy.editor import VideoFileClip
# replaced with ffmpegop
import ffmpeg
import threading
from queue import Queue
import time
import logging
import subprocess

class VideoCutterWindow:
    def __init__(self):
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        
        self.root = ctk.CTk()
        self.root.title('Video Cutter - Procesador de Carpetas (5 min clips)')
        self.root.geometry('700x600')
        self.root.resizable(False, False)
        
        self.video_queue = Queue()
        self.processing = False
        self.selected_videos = []
        self.output_base_dir = r'C:\Users\Administrador\Desktop\grabaciones\videos procesados'
        
        self.setup_ui()
        
    def setup_ui(self):
        # Título principal
        title_label = ctk.CTkLabel(
            self.root,
            text='📁 Video Cutter - Procesador de Carpetas (5 min clips)',
            font=ctk.CTkFont(size=18, weight='bold')
        )
        title_label.pack(pady=15)
        
        # Botón seleccionar carpeta
        self.select_btn = ctk.CTkButton(
            self.root,
            text='📁 Seleccionar Carpeta con Videos',
            command=self.select_videos,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.select_btn.pack(pady=10, padx=30, fill='x')
        
        # Lista de videos seleccionados
        list_frame = ctk.CTkScrollableFrame(self.root, height=200)
        list_frame.pack(pady=10, padx=30, fill='x')
        
        self.videos_label = ctk.CTkLabel(
            list_frame,
            text='Videos en cola:',
            font=ctk.CTkFont(size=12, weight='bold')
        )
        self.videos_label.pack(anchor='w', pady=5)
        
        self.videos_listbox = ctk.CTkTextbox(
            list_frame,
            height=150,
            wrap='none'
        )
        self.videos_listbox.pack(pady=5)
        self.videos_listbox.configure(state='disabled')
        
        # Botón procesar
        self.process_btn = ctk.CTkButton(
            self.root,
            text='✂️ Cortar Videos en Bloques de 5 Minutos',
            command=self.start_processing,
            height=50,
            font=ctk.CTkFont(size=16, weight='bold'),
            state='disabled'
        )
        self.process_btn.pack(pady=15, padx=30, fill='x')
        
        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(self.root)
        self.progress_bar.pack(pady=10, padx=30, fill='x')
        self.progress_bar.set(0)
        
        # Label de estado
        self.status_label = ctk.CTkLabel(
            self.root,
            text='Selecciona una carpeta con videos para procesar',
            font=ctk.CTkFont(size=12),
            text_color='gray'
        )
        self.status_label.pack(pady=5)

        # Botón de debug
        self.debug_btn = ctk.CTkButton(
            self.root,
            text='🔧 Debug Info',
            command=self.show_debug_info,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color='gray'
        )
        self.debug_btn.pack(pady=5, padx=30, fill='x')
    
    def select_videos(self):
        folder_path = filedialog.askdirectory(
            title='Seleccionar carpeta con videos'
        )

        if folder_path:
            # Buscar archivos de video en la carpeta seleccionada y subcarpetas
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg']
            video_files = []

            # Función recursiva para buscar en subcarpetas
            def find_videos(directory):
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)

                    if os.path.isfile(item_path):
                        file_ext = os.path.splitext(item)[1].lower()
                        if file_ext in video_extensions:
                            video_files.append(item_path)
                    elif os.path.isdir(item_path):
                        # Recursivamente buscar en subcarpetas
                        find_videos(item_path)

            find_videos(folder_path)

            if video_files:
                self.selected_videos = video_files
                self.selected_folder = folder_path
                self.update_video_list()
                self.process_btn.configure(state='normal')
            else:
                messagebox.showwarning('Advertencia', 'No se encontraron archivos de video en la carpeta seleccionada ni sus subcarpetas.')
    
    def update_video_list(self):
        self.videos_listbox.configure(state='normal')
        self.videos_listbox.delete('0.0', 'end')
        
        if self.selected_videos:
            text = '\n'.join([f' {os.path.basename(video)}' for video in self.selected_videos])
            self.videos_listbox.insert('0.0', text)
            self.status_label.configure(
                text=f'{len(self.selected_videos)} videos seleccionados',
                text_color='blue'
            )
        else:
            self.videos_listbox.insert('0.0', 'Ningún video seleccionado')
            self.status_label.configure(text='Selecciona una carpeta con videos para procesar', text_color='gray')
        
        self.videos_listbox.configure(state='disabled')
    
    def start_processing(self):
        if not self.selected_videos:
            messagebox.showerror('Error', 'Por favor selecciona una carpeta con videos primero.')
            return
        
        # Preparar cola de videos
        for video_path in self.selected_videos:
            self.video_queue.put(video_path)
        
        # Deshabilitar controles
        self.select_btn.configure(state='disabled')
        self.process_btn.configure(state='disabled')
        self.processing = True
        
        # Mostrar progreso
        self.status_label.configure(text='Procesando videos...', text_color='orange')
        
        # Crear directorio base si no existe
        if not os.path.exists(self.output_base_dir):
            os.makedirs(self.output_base_dir)
        
        # Iniciar procesamiento en hilo
        processing_thread = threading.Thread(target=self.process_queue, daemon=True)
        processing_thread.start()
    
    def process_queue(self):
        total_videos = len(self.selected_videos)
        processed_count = 0
        
        while not self.video_queue.empty() and self.processing:
            video_path = self.video_queue.get()
            
            try:
                self.root.after(0, lambda: self.status_label.configure(
                    text=f'Procesando: {os.path.basename(video_path)}',
                    text_color='orange'
                ))
                
                # Procesar el video
                self.cut_video_segments(video_path)
                
                processed_count += 1
                progress = processed_count / total_videos
                self.root.after(0, lambda p=progress: self.progress_bar.set(p))
                
            except Exception as e:
                self.root.after(0, lambda msg=f'Error procesando {os.path.basename(video_path)}':
                    messagebox.showerror('Error', msg))
                continue
        
        # Finalizar
        self.finish_processing(processed_count)
    
    def cut_video_segments(self, video_path):
        try:
            # Obtener nombre base del video sin extensión
            base_name = os.path.splitext(os.path.basename(video_path))[0]

            # Obtener fecha actual en formato YYYY-MM-DD
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')

            # Usar directamente la carpeta base sin subcarpetas
            output_folder = self.output_base_dir

            # Obtener duración del video usando ffprobe
            try:
                probe = ffmpeg.probe(video_path)
                duration_seconds = float(probe['format']['duration'])
            except Exception as e:
                raise Exception(f'Error obteniendo duración del video: {str(e)}')

            # Calcular número de segmentos de 5 minutos (300 segundos)
            segment_duration = 300
            num_segments = int(duration_seconds // segment_duration)
            remainder = duration_seconds % segment_duration

            # Si hay resto menor que un minuto, agregar al último segmento
            if remainder < 60 and num_segments > 0:
                num_segments -= 1
                remainder += segment_duration

            # Si no hay segmentos completos, crear un segmento con toda la duración
            if num_segments == 0:
                segment_duration = duration_seconds
                num_segments = 1

            # Crear cada segmento
            for i in range(num_segments):
                start_time = i * 300
                end_time = min((i + 1) * 300, duration_seconds)

                if i == num_segments - 1 and remainder >= 60:
                    end_time = duration_seconds

                # Crear nombre del segmento con fecha para evitar conflictos
                if num_segments == 1:
                    segment_name = f'{base_name}_{current_date}_clip.mp4'
                else:
                    segment_name = f'{base_name}_{current_date}_clip_{i+1:02d}.mp4'

                output_path = os.path.join(output_folder, segment_name)

                # Extraer segmento usando ffmpeg
                try:
                    (
                        ffmpeg
                        .input(video_path, ss=start_time, t=end_time-start_time)
                        .output(output_path, vcodec='libx264', acodec='aac')
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                except ffmpeg.Error as e:
                    raise Exception(f'Error extrayendo segmento con ffmpeg: {str(e)}')

            self.root.after(0, lambda msg=f'{base_name}: {num_segments} subclips creados':
                self.show_success_message(msg))

        except Exception as e:
            raise Exception(f'Error cortando video: {str(e)}')
    
    def show_debug_info(self):
        """Mostrar información de debug del sistema"""
        debug_window = ctk.CTkToplevel(self.root)
        debug_window.title('🔧 Información de Debug')
        debug_window.geometry('800x600')
        debug_window.resizable(True, True)

        # Hacer la ventana modal
        debug_window.transient(self.root)
        debug_window.grab_set()

        # Crear área de texto con scroll
        text_area = scrolledtext.ScrolledText(
            debug_window,
            wrap='word',
            font=('Consolas', 10),
            bg='#2b2b2b',
            fg='white'
        )
        text_area.pack(padx=10, pady=10, fill='both', expand=True)

        # Recopilar información de debug
        debug_info = self.get_debug_info()
        text_area.insert('1.0', debug_info)
        text_area.configure(state='disabled')

        # Botón cerrar
        close_btn = ctk.CTkButton(
            debug_window,
            text='Cerrar',
            command=debug_window.destroy,
            width=100
        )
        close_btn.pack(pady=10)

    def get_debug_info(self):
        """Obtener información detallada del sistema para debug"""
        info = []
        info.append("=" * 60)
        info.append("🔧 INFORMACIÓN DE DEBUG - VIDEO CUTTER")
        info.append("=" * 60)
        info.append("")

        # Información del sistema
        info.append("📊 INFORMACIÓN DEL SISTEMA:")
        info.append(f"   Sistema Operativo: {sys.platform}")
        info.append(f"   Versión de Python: {sys.version}")
        info.append(f"   Ejecutable Python: {sys.executable}")
        info.append(f"   Directorio actual: {os.getcwd()}")
        info.append("")

        # Información de dependencias
        info.append("📦 DEPENDENCIAS INSTALADAS:")
        try:
            import customtkinter
            info.append(f"   ✓ CustomTkinter: {customtkinter.__version__}")
        except ImportError as e:
            info.append(f"   ✗ CustomTkinter: No instalado - {e}")

        try:
            import ffmpeg
            info.append("   ✓ ffmpeg-python: Instalado")
        except ImportError as e:
            info.append(f"   ✗ ffmpeg-python: No instalado - {e}")

        # Verificar ffmpeg del sistema
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                info.append(f"   ✓ FFmpeg sistema: {version_line}")
            else:
                info.append("   ✗ FFmpeg sistema: No encontrado o error")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            info.append(f"   ✗ FFmpeg sistema: Error al verificar - {e}")

        # Verificar ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                info.append(f"   ✓ FFprobe sistema: {version_line}")
            else:
                info.append("   ✗ FFprobe sistema: No encontrado o error")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            info.append(f"   ✗ FFprobe sistema: Error al verificar - {e}")

        info.append("")

        # Información de archivos
        info.append("📁 INFORMACIÓN DE ARCHIVOS:")
        info.append(f"   Directorio de salida: {self.output_base_dir}")
        info.append(f"   Existe directorio salida: {os.path.exists(self.output_base_dir)}")

        if hasattr(self, 'selected_videos') and self.selected_videos:
            info.append(f"   Videos seleccionados: {len(self.selected_videos)}")
            for i, video in enumerate(self.selected_videos[:3]):  # Mostrar primeros 3
                size = os.path.getsize(video) / (1024*1024)  # MB
                info.append(f"     • {os.path.basename(video)} ({size:.1f}MB)")
            if len(self.selected_videos) > 3:
                info.append(f"     ... y {len(self.selected_videos) - 3} más")
        else:
            info.append("   Videos seleccionados: Ninguno")

        info.append("")

        # Información de entorno
        info.append("🌍 VARIABLES DE ENTORNO RELEVANTES:")
        relevant_vars = ['PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'USER', 'HOME']
        for var in relevant_vars:
            value = os.environ.get(var, 'No definida')
            if var == 'PATH':
                # Truncar PATH para no hacer muy largo el output
                paths = value.split(os.pathsep) if value != 'No definida' else []
                if len(paths) > 5:
                    value = os.pathsep.join(paths[:3] + ['...'] + paths[-2:])
            info.append(f"   {var}: {value}")

        info.append("")

        # Información de errores comunes
        info.append("🔍 VERIFICACIONES ADICIONALES:")
        common_issues = []

        # Verificar permisos de escritura
        try:
            test_file = os.path.join(self.output_base_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            common_issues.append("   ✓ Permisos de escritura: OK")
        except Exception as e:
            common_issues.append(f"   ✗ Permisos de escritura: Error - {e}")

        # Verificar espacio en disco
        try:
            stat = os.statvfs(self.output_base_dir)
            free_space_gb = (stat.f_available * stat.f_frsize) / (1024**3)
            common_issues.append(f"   ✓ Espacio libre: {free_space_gb:.1f}GB")
        except Exception as e:
            common_issues.append(f"   ✗ Espacio en disco: Error al verificar - {e}")

        info.extend(common_issues)
        info.append("")

        # Consejos de solución de problemas
        info.append("💡 CONSEJOS PARA SOLUCIONAR PROBLEMAS:")
        info.append("   • Asegúrate de que FFmpeg esté instalado en el sistema")
        info.append("   • Verifica que los videos no estén corruptos")
        info.append("   • Comprueba que hay suficiente espacio en disco")
        info.append("   • Asegúrate de tener permisos de escritura en el directorio de salida")
        info.append("   • Si usas un entorno virtual, activa todas las dependencias necesarias")

        info.append("")
        info.append("=" * 60)
        info.append(f"Debug generado el: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        info.append("=" * 60)

        return '\n'.join(info)

    def show_success_message(self, message):
        self.status_label.configure(text=message, text_color='green')
    
    def finish_processing(self, processed_count):
        self.processing = False
        
        self.root.after(0, lambda: self.select_btn.configure(state='normal'))
        self.root.after(0, lambda: self.process_btn.configure(state='normal'))
        
        if processed_count == len(self.selected_videos):
            message = f' ¡Procesamiento completado! {processed_count} videos procesados.'
        else:
            message = f' Procesamiento finalizado. {processed_count}/{len(self.selected_videos)} videos completados.'
        
        self.root.after(0, lambda msg=message: self.status_label.configure(text=msg, text_color='green'))
        self.root.after(0, lambda: self.progress_bar.set(processed_count / len(self.selected_videos)))
    
    def run(self):
        self.root.mainloop()

def main():
    try:
        app = VideoCutterWindow()
        app.run()
    except Exception as e:
        messagebox.showerror('Error', f'Error iniciando aplicación: {str(e)}')

if __name__ == '__main__':
    main()
