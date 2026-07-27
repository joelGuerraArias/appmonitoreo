#!/usr/bin/env python3
"""
Sistema de logging detallado para coincidencias y APIs
Registra todo el proceso de detección, envío y respuestas de APIs
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class CoincidenciasLogger:
    """Logger especializado para el sistema de coincidencias"""
    
    def __init__(self, log_dir: str = "."):
        self.log_dir = log_dir
        self.setup_loggers()
    
    def setup_loggers(self):
        """Configura los loggers para diferentes tipos de eventos"""
        
        # Logger principal de coincidencias
        self.coincidencias_logger = logging.getLogger('coincidencias')
        self.coincidencias_logger.setLevel(logging.INFO)
        
        # Logger de APIs
        self.apis_logger = logging.getLogger('apis')
        self.apis_logger.setLevel(logging.INFO)
        
        # Logger de Google Drive
        self.gdrive_logger = logging.getLogger('gdrive')
        self.gdrive_logger.setLevel(logging.INFO)
        
        # Logger de errores críticos
        self.errors_logger = logging.getLogger('errors')
        self.errors_logger.setLevel(logging.ERROR)
        
        # Crear directorio de logs si no existe
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configurar handlers para cada logger
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura los handlers para cada logger"""
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Handler para coincidencias
        coincidencias_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'coincidencias_{timestamp}.log'),
            encoding='utf-8'
        )
        coincidencias_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.coincidencias_logger.addHandler(coincidencias_handler)
        
        # Handler para APIs
        apis_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'apis_{timestamp}.log'),
            encoding='utf-8'
        )
        apis_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.apis_logger.addHandler(apis_handler)
        
        # Handler para Google Drive
        gdrive_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'gdrive_{timestamp}.log'),
            encoding='utf-8'
        )
        gdrive_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.gdrive_logger.addHandler(gdrive_handler)
        
        # Handler para errores críticos
        errors_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'errors_{timestamp}.log'),
            encoding='utf-8'
        )
        errors_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.errors_logger.addHandler(errors_handler)
    
    def log_coincidencia_detectada(self, video_path: str, termino: str, timestamp: str, 
                                 duracion: float, confianza: float = None):
        """Registra cuando se detecta una coincidencia"""
        self.coincidencias_logger.info(
            f"🎯 COINCIDENCIA DETECTADA | Video: {os.path.basename(video_path)} | "
            f"Término: {termino} | Timestamp: {timestamp} | Duración: {duracion}s | "
            f"Confianza: {confianza or 'N/A'}"
        )
    
    def log_proceso_iniciado(self, video_path: str, termino: str):
        """Registra cuando inicia el procesamiento de una coincidencia"""
        self.coincidencias_logger.info(
            f"🚀 PROCESO INICIADO | Video: {os.path.basename(video_path)} | Término: {termino}"
        )
    
    def log_transcripcion_completada(self, video_path: str, duracion_transcripcion: float):
        """Registra cuando se completa la transcripción"""
        self.coincidencias_logger.info(
            f"📝 TRANSCRIPCIÓN COMPLETADA | Video: {os.path.basename(video_path)} | "
            f"Duración: {duracion_transcripcion:.2f}s"
        )
    
    def log_resumen_generado(self, video_path: str, longitud_resumen: int):
        """Registra cuando se genera el resumen"""
        self.coincidencias_logger.info(
            f"📋 RESUMEN GENERADO | Video: {os.path.basename(video_path)} | "
            f"Longitud: {longitud_resumen} caracteres"
        )
    
    def log_api_request(self, api_name: str, endpoint: str, method: str, 
                       payload_size: int = None, headers: Dict = None):
        """Registra una petición a una API"""
        self.apis_logger.info(
            f"🌐 API REQUEST | {api_name} | {method} {endpoint} | "
            f"Payload: {payload_size or 'N/A'} bytes | Headers: {len(headers or {})} items"
        )
    
    def log_api_response(self, api_name: str, status_code: int, response_time: float,
                        response_size: int = None, success: bool = True):
        """Registra la respuesta de una API"""
        status_emoji = "✅" if success else "❌"
        self.apis_logger.info(
            f"{status_emoji} API RESPONSE | {api_name} | Status: {status_code} | "
            f"Time: {response_time:.2f}s | Size: {response_size or 'N/A'} bytes"
        )
    
    def log_api_error(self, api_name: str, error: str, status_code: int = None):
        """Registra un error de API"""
        self.apis_logger.error(
            f"❌ API ERROR | {api_name} | Status: {status_code or 'N/A'} | Error: {error}"
        )
    
    def log_gdrive_upload_start(self, filename: str, file_size: int, mime_type: str):
        """Registra el inicio de subida a Google Drive"""
        self.gdrive_logger.info(
            f"☁️ GDRIVE UPLOAD START | File: {filename} | Size: {file_size} bytes | Type: {mime_type}"
        )
    
    def log_gdrive_upload_success(self, filename: str, file_id: str, web_view_link: str = None):
        """Registra subida exitosa a Google Drive"""
        self.gdrive_logger.info(
            f"✅ GDRIVE UPLOAD SUCCESS | File: {filename} | ID: {file_id} | "
            f"Link: {web_view_link or 'N/A'}"
        )
    
    def log_gdrive_upload_error(self, filename: str, error: str, status_code: int = None):
        """Registra error en subida a Google Drive"""
        self.gdrive_logger.error(
            f"❌ GDRIVE UPLOAD ERROR | File: {filename} | Status: {status_code or 'N/A'} | "
            f"Error: {error}"
        )
    
    def log_telegram_send(self, chat_id: str, message_length: int, has_media: bool = False):
        """Registra envío a Telegram"""
        self.apis_logger.info(
            f"📱 TELEGRAM SEND | Chat: {chat_id} | Message: {message_length} chars | "
            f"Media: {'Yes' if has_media else 'No'}"
        )
    
    def log_telegram_success(self, chat_id: str, message_id: str):
        """Registra envío exitoso a Telegram"""
        self.apis_logger.info(
            f"✅ TELEGRAM SUCCESS | Chat: {chat_id} | Message ID: {message_id}"
        )
    
    def log_telegram_error(self, chat_id: str, error: str):
        """Registra error en Telegram"""
        self.apis_logger.error(
            f"❌ TELEGRAM ERROR | Chat: {chat_id} | Error: {error}"
        )
    
    def log_brevo_send(self, to_email: str, subject: str, has_attachment: bool = False):
        """Registra envío de correo con Brevo"""
        self.apis_logger.info(
            f"📧 BREVO SEND | To: {to_email} | Subject: {subject} | "
            f"Attachment: {'Yes' if has_attachment else 'No'}"
        )
    
    def log_brevo_success(self, to_email: str, message_id: str):
        """Registra envío exitoso con Brevo"""
        self.apis_logger.info(
            f"✅ BREVO SUCCESS | To: {to_email} | Message ID: {message_id}"
        )
    
    def log_brevo_error(self, to_email: str, error: str, status_code: int = None):
        """Registra error en Brevo"""
        self.apis_logger.error(
            f"❌ BREVO ERROR | To: {to_email} | Status: {status_code or 'N/A'} | Error: {error}"
        )
    
    def log_webhook_send(self, webhook_url: str, payload_size: int):
        """Registra envío a webhook"""
        self.apis_logger.info(
            f"🌐 WEBHOOK SEND | URL: {webhook_url} | Payload: {payload_size} bytes"
        )
    
    def log_webhook_success(self, webhook_url: str, status_code: int, response_time: float):
        """Registra respuesta exitosa de webhook"""
        self.apis_logger.info(
            f"✅ WEBHOOK SUCCESS | URL: {webhook_url} | Status: {status_code} | "
            f"Time: {response_time:.2f}s"
        )
    
    def log_webhook_error(self, webhook_url: str, error: str, status_code: int = None):
        """Registra error en webhook"""
        self.apis_logger.error(
            f"❌ WEBHOOK ERROR | URL: {webhook_url} | Status: {status_code or 'N/A'} | "
            f"Error: {error}"
        )
    
    def log_error_critico(self, funcion: str, error: str, video_path: str = None, 
                         termino: str = None, info_adicional: str = None):
        """Registra errores críticos que impiden el funcionamiento"""
        self.errors_logger.error(
            f"🚨 ERROR CRÍTICO | Función: {funcion} | Video: {video_path or 'N/A'} | "
            f"Término: {termino or 'N/A'} | Error: {error} | Info: {info_adicional or 'N/A'}"
        )
    
    def log_proceso_completado(self, video_path: str, termino: str, 
                             resultados: Dict[str, Any]):
        """Registra cuando se completa todo el proceso de una coincidencia"""
        self.coincidencias_logger.info(
            f"🎉 PROCESO COMPLETADO | Video: {os.path.basename(video_path)} | "
            f"Término: {termino} | Resultados: {json.dumps(resultados, ensure_ascii=False)}"
        )
    
    def log_estadisticas_diarias(self, total_coincidencias: int, exitosas: int, 
                               fallidas: int, tiempo_promedio: float):
        """Registra estadísticas diarias del sistema"""
        self.coincidencias_logger.info(
            f"📊 ESTADÍSTICAS DIARIAS | Total: {total_coincidencias} | "
            f"Exitosas: {exitosas} | Fallidas: {fallidas} | "
            f"Tiempo promedio: {tiempo_promedio:.2f}s"
        )

# Instancia global del logger
coincidencias_logger = CoincidenciasLogger()

def log_coincidencia_detectada(video_path: str, termino: str, timestamp: str, 
                             duracion: float, confianza: float = None):
    """Función helper para registrar coincidencias detectadas"""
    coincidencias_logger.log_coincidencia_detectada(video_path, termino, timestamp, duracion, confianza)

def log_api_request(api_name: str, endpoint: str, method: str, 
                   payload_size: int = None, headers: Dict = None):
    """Función helper para registrar peticiones a APIs"""
    coincidencias_logger.log_api_request(api_name, endpoint, method, payload_size, headers)

def log_api_response(api_name: str, status_code: int, response_time: float,
                    response_size: int = None, success: bool = True):
    """Función helper para registrar respuestas de APIs"""
    coincidencias_logger.log_api_response(api_name, status_code, response_time, response_size, success)

def log_api_error(api_name: str, error: str, status_code: int = None):
    """Función helper para registrar errores de APIs"""
    coincidencias_logger.log_api_error(api_name, error, status_code)

def log_error_critico(funcion: str, error: str, video_path: str = None, 
                     termino: str = None, info_adicional: str = None):
    """Función helper para registrar errores críticos"""
    coincidencias_logger.log_error_critico(funcion, error, video_path, termino, info_adicional)

def log_gdrive_upload_start(filename: str, file_size: int, mime_type: str):
    """Función helper para registrar inicio de subida a Google Drive"""
    coincidencias_logger.log_gdrive_upload_start(filename, file_size, mime_type)

def log_gdrive_upload_success(filename: str, file_id: str, web_view_link: str = None):
    """Función helper para registrar subida exitosa a Google Drive"""
    coincidencias_logger.log_gdrive_upload_success(filename, file_id, web_view_link)

def log_gdrive_upload_error(filename: str, error: str, status_code: int = None):
    """Función helper para registrar error en subida a Google Drive"""
    coincidencias_logger.log_gdrive_upload_error(filename, error, status_code)

def log_proceso_completado(video_path: str, termino: str, resultados: Dict[str, Any]):
    """Función helper para registrar proceso completado"""
    coincidencias_logger.log_proceso_completado(video_path, termino, resultados)

