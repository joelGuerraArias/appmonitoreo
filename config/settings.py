# -*- coding: utf-8 -*-
"""
Configuración centralizada para Video Analyzer

Carga credenciales desde variables de entorno o archivo .env
Nunca hardcodear API keys en el código!
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from functools import lru_cache

# Intentar cargar python-dotenv si está disponible
try:
    from dotenv import load_dotenv
    # Buscar .env en el directorio del proyecto
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Intentar en el directorio actual
        load_dotenv()
except ImportError:
    pass  # Si no está instalado, usar solo variables de entorno del sistema


@dataclass
class OpenAIConfig:
    """Configuración de OpenAI"""
    api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    api_key_backup: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY_BACKUP', ''))
    model: str = "whisper-1"
    
    def get_active_key(self) -> str:
        """Retorna la API key activa (principal o backup)"""
        return self.api_key or self.api_key_backup
    
    def is_configured(self) -> bool:
        return bool(self.get_active_key())


@dataclass
class MistralConfig:
    """Configuración de Mistral AI"""
    api_key: str = field(default_factory=lambda: os.getenv('MISTRAL_API_KEY', ''))
    model: str = "voxtral-mini-latest"
    
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class GoogleDriveConfig:
    """Configuración de Google Drive"""
    client_id: str = field(default_factory=lambda: os.getenv('GOOGLE_CLIENT_ID', ''))
    client_secret: str = field(default_factory=lambda: os.getenv('GOOGLE_CLIENT_SECRET', ''))
    refresh_token: str = field(default_factory=lambda: os.getenv('GOOGLE_REFRESH_TOKEN', ''))
    folder_id: str = field(default_factory=lambda: os.getenv('GOOGLE_DRIVE_FOLDER_ID', ''))
    
    def is_configured(self) -> bool:
        return all([self.client_id, self.client_secret, self.refresh_token, self.folder_id])


@dataclass
class SupabaseConfig:
    """Configuración de Supabase"""
    url: str = field(default_factory=lambda: os.getenv('SUPABASE_URL', ''))
    anon_key: str = field(default_factory=lambda: os.getenv('SUPABASE_ANON_KEY', ''))
    
    def is_configured(self) -> bool:
        return bool(self.url and self.anon_key)


@dataclass
class CloudinaryConfig:
    """Configuración de Cloudinary"""
    cloud_name: str = field(default_factory=lambda: os.getenv('CLOUDINARY_CLOUD_NAME', ''))
    api_key: str = field(default_factory=lambda: os.getenv('CLOUDINARY_API_KEY', ''))
    api_secret: str = field(default_factory=lambda: os.getenv('CLOUDINARY_API_SECRET', ''))
    folder: str = "video_analyzer_clips"
    resource_type: str = "video"
    
    def is_configured(self) -> bool:
        return all([self.cloud_name, self.api_key, self.api_secret])


def _default_carpeta_videos() -> Path:
    """Ruta por defecto: usa variable de entorno o directorio del proyecto"""
    if os.getenv('CARPETA_VIDEOS'):
        return Path(os.getenv('CARPETA_VIDEOS'))
    # Usar directorio del proyecto (donde está config/)
    project_root = Path(__file__).parent.parent
    return project_root / "grabaciones" if (project_root / "grabaciones").exists() else project_root

def _default_carpeta_procesados() -> Path:
    """Ruta por defecto: usa variable de entorno o directorio del proyecto"""
    if os.getenv('CARPETA_PROCESADOS'):
        return Path(os.getenv('CARPETA_PROCESADOS'))
    project_root = Path(__file__).parent.parent
    return project_root / "videos procesados"

@dataclass
class PathsConfig:
    """Configuración de rutas"""
    carpeta_videos: Path = field(default_factory=_default_carpeta_videos)
    carpeta_procesados: Path = field(default_factory=_default_carpeta_procesados)
    
    def __post_init__(self):
        """Crear carpetas si no existen (solo si tenemos permisos)"""
        try:
            self.carpeta_videos.mkdir(parents=True, exist_ok=True)
            self.carpeta_procesados.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            # Si no hay permisos, no fallar - las carpetas podrían existir
            if not self.carpeta_videos.exists() or not self.carpeta_procesados.exists():
                raise RuntimeError(
                    f"No se pueden crear las carpetas de trabajo. "
                    f"Configura CARPETA_VIDEOS y CARPETA_PROCESADOS en .env con rutas donde tengas permisos. Error: {e}"
                ) from e
    
    @property
    def terminos_config(self) -> Path:
        return self.carpeta_procesados / "terminos_guardados.json"
    
    @property
    def procesados_json(self) -> Path:
        return self.carpeta_procesados / "procesados.json"
    
    @property
    def coincidencias_md(self) -> Path:
        return self.carpeta_procesados / "coincidencias.md"
    
    @property
    def webhook_config(self) -> Path:
        return self.carpeta_procesados / "webhook_config.json"
    
    @property
    def telegram_config(self) -> Path:
        return self.carpeta_procesados / "telegram_config.json"
    
    @property
    def cloudinary_config(self) -> Path:
        return self.carpeta_procesados / "cloudinary_config.json"
    
    @property
    def brevo_config(self) -> Path:
        return self.carpeta_procesados / "brevo_config.json"
    
    @property
    def correos_guardados(self) -> Path:
        return self.carpeta_procesados / "correos_guardados.json"


@dataclass
class ProcessingConfig:
    """Configuración de procesamiento"""
    tamano_minimo_bytes: int = 8 * 1024 * 1024  # 8 MB
    duracion_clip_default: int = 60  # segundos
    buffer_anterior_default: int = 30  # segundos
    max_reintentos: int = 3
    timeout_api: int = 30
    intervalo_escaneo: int = 60  # segundos


@dataclass
class Settings:
    """
    Configuración principal de la aplicación
    
    Uso:
        from config import get_settings
        settings = get_settings()
        
        # Acceder a configuraciones
        openai_key = settings.openai.get_active_key()
        mistral_key = settings.mistral.api_key
    """
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    mistral: MistralConfig = field(default_factory=MistralConfig)
    google_drive: GoogleDriveConfig = field(default_factory=GoogleDriveConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    cloudinary: CloudinaryConfig = field(default_factory=CloudinaryConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    def validate(self) -> List[str]:
        """
        Valida la configuración y retorna lista de errores/advertencias
        
        Returns:
            Lista de mensajes de error (vacía si todo está OK)
        """
        errors = []
        
        if not self.openai.is_configured():
            errors.append("⚠️ OpenAI API Key no configurada")
        
        if not self.mistral.is_configured():
            errors.append("⚠️ Mistral API Key no configurada")
        
        if not self.google_drive.is_configured():
            errors.append("⚠️ Google Drive no configurado completamente")
        
        if not self.supabase.is_configured():
            errors.append("⚠️ Supabase no configurado")
        
        if not self.cloudinary.is_configured():
            errors.append("⚠️ Cloudinary no configurado")
        
        return errors
    
    def print_status(self):
        """Imprime el estado de configuración"""
        print("\n" + "="*50)
        print("ESTADO DE CONFIGURACION")
        print("="*50)
        print(f"[OK] OpenAI: {'Configurado' if self.openai.is_configured() else '[X] No configurado'}")
        print(f"[OK] Mistral: {'Configurado' if self.mistral.is_configured() else '[X] No configurado'}")
        print(f"[OK] Google Drive: {'Configurado' if self.google_drive.is_configured() else '[X] No configurado'}")
        print(f"[OK] Supabase: {'Configurado' if self.supabase.is_configured() else '[X] No configurado'}")
        print(f"[OK] Cloudinary: {'Configurado' if self.cloudinary.is_configured() else '[X] No configurado'}")
        print("="*50 + "\n")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Obtiene la instancia de configuración (singleton)
    
    Returns:
        Settings: Instancia de configuración
    """
    return Settings()


# Alias para compatibilidad
def load_settings() -> Settings:
    """Alias de get_settings para compatibilidad"""
    return get_settings()


if __name__ == "__main__":
    # Test de configuración
    settings = get_settings()
    settings.print_status()
    
    errors = settings.validate()
    if errors:
        print("⚠️ Advertencias de configuración:")
        for error in errors:
            print(f"  {error}")

