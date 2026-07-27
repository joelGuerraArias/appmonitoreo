#!/usr/bin/env python3
"""
Sistema de logging principal para el análisis de coincidencias
Genera un archivo de log consolidado en la raíz del proyecto
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

class SistemaCoincidenciasLogger:
    """Logger principal que consolida todos los logs del sistema"""
    
    def __init__(self, log_dir: str = "."):
        self.log_dir = log_dir
        self.setup_main_logger()
    
    def setup_main_logger(self):
        """Configura el logger principal"""
        self.main_logger = logging.getLogger('sistema_coincidencias')
        self.main_logger.setLevel(logging.INFO)
        
        # Crear directorio de logs si no existe
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configurar handler para el log principal
        timestamp = datetime.now().strftime('%Y%m%d')
        main_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'sistema_coincidencias_{timestamp}.log'),
            encoding='utf-8'
        )
        main_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.main_logger.addHandler(main_handler)
    
    def log_inicio_sistema(self):
        """Registra el inicio del sistema"""
        self.main_logger.info("🚀 SISTEMA DE COINCIDENCIAS INICIADO")
        self.main_logger.info(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.main_logger.info("=" * 80)
    
    def log_configuracion_sistema(self, config: Dict[str, Any]):
        """Registra la configuración del sistema"""
        self.main_logger.info("⚙️ CONFIGURACIÓN DEL SISTEMA:")
        for key, value in config.items():
            if 'token' in key.lower() or 'secret' in key.lower():
                # Ocultar tokens y secretos
                self.main_logger.info(f"  {key}: {'*' * 10}")
            else:
                self.main_logger.info(f"  {key}: {value}")
        self.main_logger.info("-" * 80)
    
    def log_coincidencia_procesada(self, video_path: str, termino: str, 
                                  resultados: Dict[str, Any], duracion_proceso: float):
        """Registra una coincidencia procesada"""
        self.main_logger.info(f"🎯 COINCIDENCIA PROCESADA:")
        self.main_logger.info(f"  📹 Video: {os.path.basename(video_path)}")
        self.main_logger.info(f"  🔍 Término: {termino}")
        self.main_logger.info(f"  ⏱️ Duración proceso: {duracion_proceso:.2f}s")
        self.main_logger.info(f"  📊 Resultados:")
        
        for servicio, resultado in resultados.items():
            if isinstance(resultado, dict):
                estado = "✅" if resultado.get('exito', False) else "❌"
                mensaje = resultado.get('mensaje', 'Sin mensaje')
                self.main_logger.info(f"    {estado} {servicio}: {mensaje}")
            else:
                self.main_logger.info(f"    📝 {servicio}: {resultado}")
        
        self.main_logger.info("-" * 80)
    
    def log_error_sistema(self, error: str, funcion: str, video_path: str = None, 
                         termino: str = None, detalles: str = None):
        """Registra errores del sistema"""
        self.main_logger.error(f"🚨 ERROR DEL SISTEMA:")
        self.main_logger.error(f"  🔧 Función: {funcion}")
        self.main_logger.error(f"  📹 Video: {video_path or 'N/A'}")
        self.main_logger.error(f"  🔍 Término: {termino or 'N/A'}")
        self.main_logger.error(f"  ❌ Error: {error}")
        if detalles:
            self.main_logger.error(f"  📝 Detalles: {detalles}")
        self.main_logger.error("-" * 80)
    
    def log_estadisticas_diarias(self, estadisticas: Dict[str, Any]):
        """Registra estadísticas diarias"""
        self.main_logger.info("📊 ESTADÍSTICAS DIARIAS:")
        self.main_logger.info(f"  📅 Fecha: {datetime.now().strftime('%Y-%m-%d')}")
        self.main_logger.info(f"  🎯 Total coincidencias: {estadisticas.get('total_coincidencias', 0)}")
        self.main_logger.info(f"  ✅ Exitosas: {estadisticas.get('exitosas', 0)}")
        self.main_logger.info(f"  ❌ Fallidas: {estadisticas.get('fallidas', 0)}")
        self.main_logger.info(f"  ⏱️ Tiempo promedio: {estadisticas.get('tiempo_promedio', 0):.2f}s")
        self.main_logger.info(f"  📈 Tasa de éxito: {estadisticas.get('tasa_exito', 0):.1f}%")
        self.main_logger.info("-" * 80)
    
    def log_estado_apis(self, estado_apis: Dict[str, Any]):
        """Registra el estado de las APIs"""
        self.main_logger.info("🌐 ESTADO DE LAS APIs:")
        for api, estado in estado_apis.items():
            emoji = "✅" if estado.get('activa', False) else "❌"
            self.main_logger.info(f"  {emoji} {api}: {estado.get('mensaje', 'Sin mensaje')}")
        self.main_logger.info("-" * 80)
    
    def log_resumen_procesamiento(self, resumen: Dict[str, Any]):
        """Registra un resumen del procesamiento"""
        self.main_logger.info("📋 RESUMEN DE PROCESAMIENTO:")
        self.main_logger.info(f"  🎬 Videos procesados: {resumen.get('videos_procesados', 0)}")
        self.main_logger.info(f"  🎯 Coincidencias encontradas: {resumen.get('coincidencias', 0)}")
        self.main_logger.info(f"  📤 Archivos enviados: {resumen.get('archivos_enviados', 0)}")
        self.main_logger.info(f"  ⏱️ Tiempo total: {resumen.get('tiempo_total', 0):.2f}s")
        self.main_logger.info("-" * 80)
    
    def generar_reporte_diario(self):
        """Genera un reporte diario consolidado"""
        timestamp = datetime.now().strftime('%Y%m%d')
        reporte_path = os.path.join(self.log_dir, f'reporte_diario_{timestamp}.json')
        
        # Leer logs del día
        logs_del_dia = self.leer_logs_del_dia()
        
        # Generar estadísticas
        estadisticas = self.calcular_estadisticas(logs_del_dia)
        
        # Guardar reporte
        with open(reporte_path, 'w', encoding='utf-8') as f:
            json.dump(estadisticas, f, ensure_ascii=False, indent=2)
        
        self.main_logger.info(f"📄 Reporte diario generado: {reporte_path}")
        return estadisticas
    
    def leer_logs_del_dia(self) -> List[Dict[str, Any]]:
        """Lee todos los logs del día actual"""
        logs = []
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Buscar archivos de log del día
        log_files = [
            f'coincidencias_{timestamp}.log',
            f'apis_{timestamp}.log',
            f'gdrive_{timestamp}.log',
            f'errors_{timestamp}.log'
        ]
        
        for log_file in log_files:
            log_path = os.path.join(self.log_dir, log_file)
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                logs.append({
                                    'archivo': log_file,
                                    'linea': line.strip(),
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                except Exception as e:
                    self.main_logger.error(f"Error leyendo {log_file}: {e}")
        
        return logs
    
    def calcular_estadisticas(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula estadísticas de los logs"""
        estadisticas = {
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'total_logs': len(logs),
            'coincidencias_detectadas': 0,
            'errores_criticos': 0,
            'subidas_gdrive_exitosas': 0,
            'subidas_gdrive_fallidas': 0,
            'envios_telegram_exitosos': 0,
            'envios_telegram_fallidos': 0,
            'apis_activas': 0,
            'apis_inactivas': 0
        }
        
        for log in logs:
            linea = log['linea'].lower()
            
            if 'coincidencia detectada' in linea:
                estadisticas['coincidencias_detectadas'] += 1
            elif 'error crítico' in linea:
                estadisticas['errores_criticos'] += 1
            elif 'gdrive upload success' in linea:
                estadisticas['subidas_gdrive_exitosas'] += 1
            elif 'gdrive upload error' in linea:
                estadisticas['subidas_gdrive_fallidas'] += 1
            elif 'telegram success' in linea:
                estadisticas['envios_telegram_exitosos'] += 1
            elif 'telegram error' in linea:
                estadisticas['envios_telegram_fallidos'] += 1
        
        # Calcular tasas de éxito
        total_gdrive = estadisticas['subidas_gdrive_exitosas'] + estadisticas['subidas_gdrive_fallidas']
        if total_gdrive > 0:
            estadisticas['tasa_exito_gdrive'] = (estadisticas['subidas_gdrive_exitosas'] / total_gdrive) * 100
        
        total_telegram = estadisticas['envios_telegram_exitosos'] + estadisticas['envios_telegram_fallidos']
        if total_telegram > 0:
            estadisticas['tasa_exito_telegram'] = (estadisticas['envios_telegram_exitosos'] / total_telegram) * 100
        
        return estadisticas
    
    def diagnosticar_problemas(self) -> Dict[str, Any]:
        """Diagnostica problemas comunes del sistema"""
        problemas = {
            'errores_criticos': [],
            'apis_inactivas': [],
            'problemas_gdrive': [],
            'problemas_telegram': [],
            'recomendaciones': []
        }
        
        # Leer logs de errores
        timestamp = datetime.now().strftime('%Y%m%d')
        error_log_path = os.path.join(self.log_dir, f'errors_{timestamp}.log')
        
        if os.path.exists(error_log_path):
            with open(error_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'file_size_mb' in line:
                        problemas['errores_criticos'].append("Error crítico: variable 'file_size_mb' no definida")
                        problemas['recomendaciones'].append("Verificar que todas las variables estén definidas antes de usar")
                    elif 'google drive' in line.lower() and 'error' in line.lower():
                        problemas['problemas_gdrive'].append("Problemas con Google Drive detectados")
                    elif 'telegram' in line.lower() and 'error' in line.lower():
                        problemas['problemas_telegram'].append("Problemas con Telegram detectados")
        
        return problemas

# Instancia global del logger principal
sistema_logger = SistemaCoincidenciasLogger()

def log_inicio_sistema():
    """Función helper para registrar inicio del sistema"""
    sistema_logger.log_inicio_sistema()

def log_configuracion_sistema(config: Dict[str, Any]):
    """Función helper para registrar configuración"""
    sistema_logger.log_configuracion_sistema(config)

def log_coincidencia_procesada(video_path: str, termino: str, resultados: Dict[str, Any], duracion_proceso: float):
    """Función helper para registrar coincidencia procesada"""
    sistema_logger.log_coincidencia_procesada(video_path, termino, resultados, duracion_proceso)

def log_error_sistema(error: str, funcion: str, video_path: str = None, termino: str = None, detalles: str = None):
    """Función helper para registrar errores del sistema"""
    sistema_logger.log_error_sistema(error, funcion, video_path, termino, detalles)

def generar_reporte_diario():
    """Función helper para generar reporte diario"""
    return sistema_logger.generar_reporte_diario()

def diagnosticar_problemas():
    """Función helper para diagnosticar problemas"""
    return sistema_logger.diagnosticar_problemas()

