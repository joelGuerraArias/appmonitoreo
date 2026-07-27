# -*- coding: utf-8 -*-
"""
Dataclasses para estructuras de datos del Video Analyzer

Uso:
    from models import Coincidencia, ResultadoProcesamiento
    
    coincidencia = Coincidencia(
        termino="EDESUR",
        timestamp=125.5,
        contexto="mencionaron a EDESUR en el noticiero..."
    )
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum


class EstadoArchivo(Enum):
    """Estados posibles de un archivo durante el procesamiento"""
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    ERROR = "error"
    OMITIDO = "omitido"


class NivelRelevancia(Enum):
    """Niveles de relevancia para coincidencias"""
    ALTA = "Alta"
    MEDIA = "Media"
    BAJA = "Baja"


@dataclass
class Coincidencia:
    """
    Representa una coincidencia de término encontrada en un video/audio
    
    Attributes:
        termino: El término buscado que fue encontrado
        timestamp: Posición en segundos donde se encontró
        contexto: Texto alrededor de la coincidencia
        confianza: Nivel de confianza de la detección (0.0 - 1.0)
        clip_path: Ruta al clip generado (si existe)
        url_cloudinary: URL del video en Cloudinary (si se subió)
        url_gdrive: URL del video en Google Drive (si se subió)
        idea_general: Resumen del segmento generado por IA
        fecha_deteccion: Momento en que se detectó
        relevancia: Nivel de relevancia de la coincidencia
    """
    termino: str
    timestamp: float
    contexto: str
    confianza: float = 0.0
    clip_path: Optional[Path] = None
    url_cloudinary: Optional[str] = None
    url_gdrive: Optional[str] = None
    idea_general: Optional[str] = None
    fecha_deteccion: datetime = field(default_factory=datetime.now)
    relevancia: NivelRelevancia = NivelRelevancia.MEDIA
    
    def __post_init__(self):
        """Conversión de tipos después de inicialización"""
        if isinstance(self.clip_path, str):
            self.clip_path = Path(self.clip_path)
        if isinstance(self.relevancia, str):
            self.relevancia = NivelRelevancia(self.relevancia)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización JSON"""
        return {
            'termino': self.termino,
            'timestamp': self.timestamp,
            'contexto': self.contexto,
            'confianza': self.confianza,
            'clip_path': str(self.clip_path) if self.clip_path else None,
            'url_cloudinary': self.url_cloudinary,
            'url_gdrive': self.url_gdrive,
            'idea_general': self.idea_general,
            'fecha_deteccion': self.fecha_deteccion.isoformat(),
            'relevancia': self.relevancia.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Coincidencia':
        """Crea una instancia desde un diccionario"""
        if 'fecha_deteccion' in data and isinstance(data['fecha_deteccion'], str):
            data['fecha_deteccion'] = datetime.fromisoformat(data['fecha_deteccion'])
        return cls(**data)
    
    @property
    def timestamp_formateado(self) -> str:
        """Retorna el timestamp en formato MM:SS"""
        minutos = int(self.timestamp // 60)
        segundos = int(self.timestamp % 60)
        return f"{minutos:02d}:{segundos:02d}"
    
    @property
    def tiene_clip(self) -> bool:
        """Verifica si hay un clip asociado"""
        return self.clip_path is not None and self.clip_path.exists()
    
    @property
    def tiene_url(self) -> bool:
        """Verifica si hay alguna URL de video"""
        return bool(self.url_cloudinary or self.url_gdrive)


@dataclass
class ClipInfo:
    """
    Información de un clip de video generado
    
    Attributes:
        path: Ruta al archivo del clip
        termino: Término que generó el clip
        timestamp_inicio: Segundo de inicio en el video original
        timestamp_fin: Segundo de fin en el video original
        duracion: Duración del clip en segundos
        tamaño_bytes: Tamaño del archivo en bytes
        video_origen: Nombre del video original
        transcripcion: Transcripción del audio del clip
        fecha_creacion: Fecha de creación del clip
    """
    path: Path
    termino: str
    timestamp_inicio: float
    timestamp_fin: float
    duracion: float
    tamaño_bytes: int = 0
    video_origen: str = ""
    transcripcion: str = ""
    fecha_creacion: datetime = field(default_factory=datetime.now)
    url_cloudinary: Optional[str] = None
    url_gdrive: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if self.tamaño_bytes == 0 and self.path.exists():
            self.tamaño_bytes = self.path.stat().st_size
    
    @property
    def tamaño_mb(self) -> float:
        """Retorna el tamaño en MB"""
        return self.tamaño_bytes / (1024 * 1024)
    
    @property
    def duracion_formateada(self) -> str:
        """Retorna la duración en formato MM:SS"""
        minutos = int(self.duracion // 60)
        segundos = int(self.duracion % 60)
        return f"{minutos:02d}:{segundos:02d}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': str(self.path),
            'termino': self.termino,
            'timestamp_inicio': self.timestamp_inicio,
            'timestamp_fin': self.timestamp_fin,
            'duracion': self.duracion,
            'tamaño_bytes': self.tamaño_bytes,
            'tamaño_mb': round(self.tamaño_mb, 2),
            'video_origen': self.video_origen,
            'transcripcion': self.transcripcion[:500] if self.transcripcion else "",
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'url_cloudinary': self.url_cloudinary,
            'url_gdrive': self.url_gdrive
        }


@dataclass
class ResultadoProcesamiento:
    """
    Resultado del procesamiento de un video/audio
    
    Attributes:
        archivo_origen: Ruta al archivo procesado
        nombre_archivo: Nombre del archivo
        tipo_archivo: Tipo (video, audio)
        coincidencias: Lista de coincidencias encontradas
        clips_generados: Lista de clips generados
        transcripcion: Transcripción completa
        resumen: Resumen generado por IA
        exito: Si el procesamiento fue exitoso
        error: Mensaje de error (si falló)
        duracion_total: Duración del archivo en segundos
        tiempo_procesamiento: Tiempo que tomó procesar en segundos
        fecha_procesamiento: Fecha del procesamiento
    """
    archivo_origen: Path
    nombre_archivo: str = ""
    tipo_archivo: str = "video"
    coincidencias: List[Coincidencia] = field(default_factory=list)
    clips_generados: List[ClipInfo] = field(default_factory=list)
    transcripcion: str = ""
    resumen: str = ""
    exito: bool = True
    error: Optional[str] = None
    duracion_total: float = 0.0
    tiempo_procesamiento: float = 0.0
    fecha_procesamiento: datetime = field(default_factory=datetime.now)
    api_usada: str = ""
    
    def __post_init__(self):
        if isinstance(self.archivo_origen, str):
            self.archivo_origen = Path(self.archivo_origen)
        if not self.nombre_archivo:
            self.nombre_archivo = self.archivo_origen.name
    
    @property
    def total_coincidencias(self) -> int:
        return len(self.coincidencias)
    
    @property
    def total_clips(self) -> int:
        return len(self.clips_generados)
    
    @property
    def terminos_encontrados(self) -> List[str]:
        """Lista única de términos encontrados"""
        return list(set(c.termino for c in self.coincidencias))
    
    def agregar_coincidencia(self, coincidencia: Coincidencia):
        """Agrega una coincidencia al resultado"""
        self.coincidencias.append(coincidencia)
    
    def agregar_clip(self, clip: ClipInfo):
        """Agrega un clip al resultado"""
        self.clips_generados.append(clip)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'archivo_origen': str(self.archivo_origen),
            'nombre_archivo': self.nombre_archivo,
            'tipo_archivo': self.tipo_archivo,
            'coincidencias': [c.to_dict() for c in self.coincidencias],
            'clips_generados': [c.to_dict() for c in self.clips_generados],
            'transcripcion': self.transcripcion[:1000] if self.transcripcion else "",
            'resumen': self.resumen,
            'exito': self.exito,
            'error': self.error,
            'duracion_total': self.duracion_total,
            'tiempo_procesamiento': self.tiempo_procesamiento,
            'fecha_procesamiento': self.fecha_procesamiento.isoformat(),
            'api_usada': self.api_usada,
            'total_coincidencias': self.total_coincidencias,
            'total_clips': self.total_clips,
            'terminos_encontrados': self.terminos_encontrados
        }


@dataclass
class EstadisticasEscaneo:
    """
    Estadísticas de un escaneo de carpeta
    
    Attributes:
        total_archivos: Total de archivos encontrados
        total_videos: Total de videos encontrados
        archivos_procesados: Archivos ya procesados anteriormente
        archivos_nuevos: Archivos nuevos para procesar
        archivos_muy_pequeños: Archivos omitidos por tamaño
        archivos_fallidos: Archivos que fallaron en procesamientos anteriores
    """
    total_archivos: int = 0
    total_videos: int = 0
    archivos_procesados: int = 0
    archivos_nuevos: int = 0
    archivos_muy_pequeños: int = 0
    archivos_fallidos: int = 0
    archivos_nuevos_lista: List[str] = field(default_factory=list)
    archivos_muy_pequeños_lista: List[str] = field(default_factory=list)
    fecha_escaneo: datetime = field(default_factory=datetime.now)
    
    @property
    def hay_nuevos(self) -> bool:
        return self.archivos_nuevos > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfiguracionBusqueda:
    """
    Configuración para la búsqueda de términos
    
    Attributes:
        terminos: Lista de términos a buscar
        duracion_clip: Duración de cada clip en segundos
        buffer_anterior: Segundos antes de la coincidencia
        intervalo_escaneo: Intervalo entre escaneos en segundos
        mostrar_coincidencias: Si mostrar coincidencias en UI
    """
    terminos: List[str] = field(default_factory=list)
    duracion_clip: int = 60
    buffer_anterior: int = 30
    intervalo_escaneo: int = 60
    mostrar_coincidencias: bool = True
    
    @property
    def buffer_posterior(self) -> int:
        """Calcula el buffer posterior basado en duración y buffer anterior"""
        return self.duracion_clip - self.buffer_anterior
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfiguracionBusqueda':
        return cls(**data)


@dataclass
class NotificacionPendiente:
    """
    Representa una notificación pendiente de enviar
    
    Útil para cola de notificaciones en caso de fallos de red
    """
    tipo: str  # 'telegram', 'email', 'webhook', 'supabase'
    datos: Dict[str, Any] = field(default_factory=dict)
    intentos: int = 0
    max_intentos: int = 3
    fecha_creacion: datetime = field(default_factory=datetime.now)
    ultimo_error: Optional[str] = None
    
    @property
    def puede_reintentar(self) -> bool:
        return self.intentos < self.max_intentos
    
    def registrar_intento(self, error: Optional[str] = None):
        self.intentos += 1
        self.ultimo_error = error


if __name__ == "__main__":
    # Tests básicos
    print("=== Test de Coincidencia ===")
    c = Coincidencia(
        termino="EDESUR",
        timestamp=125.5,
        contexto="Se mencionó a EDESUR en el noticiero matutino"
    )
    print(f"Coincidencia: {c.termino} en {c.timestamp_formateado}")
    print(f"Dict: {c.to_dict()}")
    
    print("\n=== Test de ClipInfo ===")
    clip = ClipInfo(
        path=Path("clips/test.mp4"),
        termino="EDESUR",
        timestamp_inicio=100,
        timestamp_fin=160,
        duracion=60
    )
    print(f"Clip: {clip.duracion_formateada} - {clip.tamaño_mb:.2f} MB")
    
    print("\n=== Test de ResultadoProcesamiento ===")
    resultado = ResultadoProcesamiento(
        archivo_origen=Path("videos/test.mp4"),
        exito=True
    )
    resultado.agregar_coincidencia(c)
    print(f"Resultado: {resultado.total_coincidencias} coincidencias")
    print(f"Términos: {resultado.terminos_encontrados}")


