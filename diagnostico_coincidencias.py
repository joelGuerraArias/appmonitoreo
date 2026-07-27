#!/usr/bin/env python3
"""
Script de diagnóstico para el sistema de coincidencias
Analiza logs existentes y genera reportes detallados
"""

import os
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

class DiagnosticoCoincidencias:
    """Diagnostica problemas en el sistema de coincidencias"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.resultados = {
            'errores_criticos': [],
            'problemas_gdrive': [],
            'problemas_telegram': [],
            'problemas_apis': [],
            'estadisticas': {},
            'recomendaciones': []
        }
    
    def analizar_logs_errores(self):
        """Analiza los logs de errores para identificar problemas"""
        print("🔍 Analizando logs de errores...")
        
        # Buscar archivos de error recientes
        archivos_error = [f for f in os.listdir(self.log_dir) if f.startswith('errors_') and f.endswith('.log')]
        archivos_error.sort(reverse=True)
        
        if not archivos_error:
            print("⚠️ No se encontraron archivos de error")
            return
        
        # Analizar los últimos 3 archivos de error
        for archivo in archivos_error[:3]:
            ruta_archivo = os.path.join(self.log_dir, archivo)
            print(f"📄 Analizando: {archivo}")
            
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                for linea_num, linea in enumerate(f, 1):
                    if 'file_size_mb' in linea and 'not defined' in linea:
                        self.resultados['errores_criticos'].append({
                            'archivo': archivo,
                            'linea': linea_num,
                            'error': 'Variable file_size_mb no definida',
                            'descripcion': 'Error crítico que impide el procesamiento de coincidencias',
                            'solucion': 'Verificar que la variable esté definida antes de usar'
                        })
                    
                    elif 'google drive' in linea.lower() and 'error' in linea.lower():
                        self.resultados['problemas_gdrive'].append({
                            'archivo': archivo,
                            'linea': linea_num,
                            'error': linea.strip(),
                            'tipo': 'Google Drive'
                        })
                    
                    elif 'telegram' in linea.lower() and 'error' in linea.lower():
                        self.resultados['problemas_telegram'].append({
                            'archivo': archivo,
                            'linea': linea_num,
                            'error': linea.strip(),
                            'tipo': 'Telegram'
                        })
    
    def analizar_logs_aplicacion(self):
        """Analiza los logs de aplicación para estadísticas"""
        print("📊 Analizando logs de aplicación...")
        
        archivos_app = [f for f in os.listdir(self.log_dir) if f.startswith('app_') and f.endswith('.log')]
        archivos_app.sort(reverse=True)
        
        if not archivos_app:
            print("⚠️ No se encontraron archivos de aplicación")
            return
        
        # Analizar el archivo más reciente
        archivo_reciente = archivos_app[0]
        ruta_archivo = os.path.join(self.log_dir, archivo_reciente)
        
        estadisticas = {
            'total_lineas': 0,
            'coincidencias_detectadas': 0,
            'procesos_completados': 0,
            'errores': 0,
            'warnings': 0
        }
        
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            for linea in f:
                estadisticas['total_lineas'] += 1
                
                if 'coincidencia detectada' in linea.lower():
                    estadisticas['coincidencias_detectadas'] += 1
                elif 'proceso completado' in linea.lower():
                    estadisticas['procesos_completados'] += 1
                elif 'error' in linea.lower():
                    estadisticas['errores'] += 1
                elif 'warning' in linea.lower():
                    estadisticas['warnings'] += 1
        
        self.resultados['estadisticas'] = estadisticas
    
    def generar_recomendaciones(self):
        """Genera recomendaciones basadas en el análisis"""
        print("💡 Generando recomendaciones...")
        
        # Recomendaciones basadas en errores críticos
        if self.resultados['errores_criticos']:
            self.resultados['recomendaciones'].append({
                'prioridad': 'ALTA',
                'problema': 'Error crítico: file_size_mb no definida',
                'solucion': 'Verificar y corregir la definición de variables en enviar_coincidencia_inmediata',
                'archivos_afectados': ['transmistral2.py']
            })
        
        # Recomendaciones basadas en problemas de Google Drive
        if self.resultados['problemas_gdrive']:
            self.resultados['recomendaciones'].append({
                'prioridad': 'MEDIA',
                'problema': 'Problemas con Google Drive',
                'solucion': 'Verificar credenciales y permisos de Google Drive',
                'archivos_afectados': ['transmistral2.py - funciones de Google Drive']
            })
        
        # Recomendaciones basadas en problemas de Telegram
        if self.resultados['problemas_telegram']:
            self.resultados['recomendaciones'].append({
                'prioridad': 'MEDIA',
                'problema': 'Problemas con Telegram',
                'solucion': 'Verificar token del bot y chat_id de Telegram',
                'archivos_afectados': ['transmistral2.py - funciones de Telegram']
            })
        
        # Recomendaciones generales
        if self.resultados['estadisticas'].get('errores', 0) > 10:
            self.resultados['recomendaciones'].append({
                'prioridad': 'ALTA',
                'problema': 'Alto número de errores detectados',
                'solucion': 'Revisar logs detalladamente y corregir errores sistemáticos',
                'archivos_afectados': ['Sistema completo']
            })
    
    def generar_reporte(self):
        """Genera un reporte completo del diagnóstico"""
        print("📋 Generando reporte de diagnóstico...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reporte_path = f'diagnostico_coincidencias_{timestamp}.json'
        
        # Agregar metadatos
        self.resultados['metadatos'] = {
            'fecha_diagnostico': datetime.now().isoformat(),
            'directorio_logs': self.log_dir,
            'total_errores_criticos': len(self.resultados['errores_criticos']),
            'total_problemas_gdrive': len(self.resultados['problemas_gdrive']),
            'total_problemas_telegram': len(self.resultados['problemas_telegram']),
            'total_recomendaciones': len(self.resultados['recomendaciones'])
        }
        
        # Guardar reporte
        with open(reporte_path, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Reporte generado: {reporte_path}")
        return reporte_path
    
    def imprimir_resumen(self):
        """Imprime un resumen del diagnóstico"""
        print("\n" + "="*80)
        print("📊 RESUMEN DEL DIAGNÓSTICO")
        print("="*80)
        
        print(f"\n🚨 ERRORES CRÍTICOS: {len(self.resultados['errores_criticos'])}")
        for error in self.resultados['errores_criticos']:
            print(f"  ❌ {error['error']} (Línea {error['linea']} en {error['archivo']})")
        
        print(f"\n☁️ PROBLEMAS GOOGLE DRIVE: {len(self.resultados['problemas_gdrive'])}")
        for problema in self.resultados['problemas_gdrive'][:5]:  # Mostrar solo los primeros 5
            print(f"  ⚠️ {problema['error'][:100]}...")
        
        print(f"\n📱 PROBLEMAS TELEGRAM: {len(self.resultados['problemas_telegram'])}")
        for problema in self.resultados['problemas_telegram'][:5]:  # Mostrar solo los primeros 5
            print(f"  ⚠️ {problema['error'][:100]}...")
        
        print(f"\n📊 ESTADÍSTICAS:")
        stats = self.resultados['estadisticas']
        print(f"  📄 Total líneas analizadas: {stats.get('total_lineas', 0)}")
        print(f"  🎯 Coincidencias detectadas: {stats.get('coincidencias_detectadas', 0)}")
        print(f"  ✅ Procesos completados: {stats.get('procesos_completados', 0)}")
        print(f"  ❌ Errores: {stats.get('errores', 0)}")
        print(f"  ⚠️ Warnings: {stats.get('warnings', 0)}")
        
        print(f"\n💡 RECOMENDACIONES: {len(self.resultados['recomendaciones'])}")
        for i, rec in enumerate(self.resultados['recomendaciones'], 1):
            print(f"  {i}. [{rec['prioridad']}] {rec['problema']}")
            print(f"     Solución: {rec['solucion']}")
        
        print("\n" + "="*80)
    
    def ejecutar_diagnostico_completo(self):
        """Ejecuta el diagnóstico completo"""
        print("🔍 INICIANDO DIAGNÓSTICO DEL SISTEMA DE COINCIDENCIAS")
        print("="*80)
        
        # Verificar que existe el directorio de logs
        if not os.path.exists(self.log_dir):
            print(f"❌ Directorio de logs no encontrado: {self.log_dir}")
            return None
        
        # Ejecutar análisis
        self.analizar_logs_errores()
        self.analizar_logs_aplicacion()
        self.generar_recomendaciones()
        
        # Generar reporte
        reporte_path = self.generar_reporte()
        
        # Imprimir resumen
        self.imprimir_resumen()
        
        return reporte_path

def main():
    """Función principal"""
    diagnostico = DiagnosticoCoincidencias()
    reporte_path = diagnostico.ejecutar_diagnostico_completo()
    
    if reporte_path:
        print(f"\n✅ Diagnóstico completado. Reporte guardado en: {reporte_path}")
    else:
        print("\n❌ Error en el diagnóstico")

if __name__ == "__main__":
    main()

