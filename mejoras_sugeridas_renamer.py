# Mejoras sugeridas para renamer.py
# ===================================

"""
MEJORAS OPCIONALES que se podrían implementar en renamer.py:

1. VALIDACIÓN DE ARCHIVOS JSON
   - Validar estructura de programacion.json antes de usar
   - Mostrar errores específicos si el JSON es inválido
   - Sugerir correcciones automáticas

2. PREVIEW DEL RENOMBRADO
   - Mostrar tabla con "Nombre Actual" vs "Nombre Nuevo"
   - Permitir edición manual antes de aplicar cambios
   - Opción "Vista previa" antes de procesar

3. CONFIGURACIÓN AVANZADA
   - Permitir personalizar formato de salida
   - Configurar zona horaria
   - Opciones de manejo de duplicados

4. BACKUP Y DESHACER
   - Crear backup de nombres originales
   - Función "Deshacer último renombrado"
   - Log persistente en archivo

5. DETECCIÓN INTELIGENTE
   - Reconocer más patrones de fecha/hora
   - Detectar automáticamente el canal del contenido
   - Sugerir programación basada en metadatos

6. EXPORTAR/IMPORTAR
   - Exportar configuraciones de programación
   - Importar desde archivos CSV/Excel
   - Compartir configuraciones entre usuarios

7. ESTADÍSTICAS AVANZADAS
   - Gráficos de procesamiento
   - Historial de operaciones
   - Métricas de rendimiento

8. INTEGRACIÓN
   - Arrastrar y soltar carpetas
   - Integración con explorador de archivos
   - Procesamiento por lotes automático

9. VALIDACIÓN DE MEDIOS
   - Verificar integridad de archivos de video
   - Detectar archivos corruptos
   - Información de metadatos (duración, resolución)

10. INTERFAZ MEJORADA
    - Modo claro/oscuro toggle
    - Temas personalizables
    - Atajos de teclado
    - Tooltips informativos
"""

# Ejemplo de implementación de una mejora:

import json
import os
from pathlib import Path

def validar_programacion_json(ruta_archivo):
    """
    Valida la estructura del archivo programacion.json
    Retorna (es_valido, errores, sugerencias)
    """
    errores = []
    sugerencias = []
    
    if not os.path.exists(ruta_archivo):
        return False, ["Archivo no existe"], ["Crear archivo programacion.json"]
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON inválido: {e}"], ["Verificar sintaxis JSON"]
    except Exception as e:
        return False, [f"Error leyendo archivo: {e}"], ["Verificar permisos de archivo"]
    
    if not isinstance(data, list):
        errores.append("El archivo debe contener una lista de programas")
        sugerencias.append("Usar formato: [{\"hora_inicio\": \"12:00 PM\", \"nombre\": \"Programa\"}]")
    
    for i, programa in enumerate(data):
        if not isinstance(programa, dict):
            errores.append(f"Programa {i+1}: debe ser un objeto")
            continue
            
        if 'hora_inicio' not in programa:
            errores.append(f"Programa {i+1}: falta 'hora_inicio'")
        elif not programa['hora_inicio']:
            errores.append(f"Programa {i+1}: 'hora_inicio' vacío")
            
        if 'nombre' not in programa:
            errores.append(f"Programa {i+1}: falta 'nombre'")
        elif not programa['nombre']:
            errores.append(f"Programa {i+1}: 'nombre' vacío")
    
    if not errores:
        sugerencias.append("Archivo válido ✅")
    
    return len(errores) == 0, errores, sugerencias

def crear_preview_renombrado(carpeta, programacion):
    """
    Crea una vista previa del renombrado sin aplicar cambios
    Retorna lista de (nombre_actual, nombre_nuevo, estado)
    """
    preview = []
    extensiones_video = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    for archivo in os.listdir(carpeta):
        if any(archivo.lower().endswith(ext) for ext in extensiones_video):
            archivo_path = Path(carpeta) / archivo
            
            # Simular proceso de renombrado
            try:
                # Aquí iría la lógica de renombrado (simplificada)
                nuevo_nombre = f"PREVIEW_{archivo}"  # Placeholder
                estado = "✅ Listo"
            except Exception as e:
                nuevo_nombre = archivo
                estado = f"❌ Error: {e}"
            
            preview.append({
                'actual': archivo,
                'nuevo': nuevo_nombre,
                'estado': estado,
                'ruta': str(archivo_path)
            })
    
    return preview

def exportar_configuracion_canal(canal, programacion, ruta_destino):
    """
    Exporta la configuración de un canal específico
    """
    config = {
        'canal': canal,
        'version': '1.0',
        'fecha_creacion': datetime.now().isoformat(),
        'programacion': programacion,
        'metadatos': {
            'total_programas': len(programacion),
            'cobertura_horas': '24h',
            'zona_horaria': 'America/Santo_Domingo'
        }
    }
    
    try:
        with open(ruta_destino, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True, f"Configuración exportada a {ruta_destino}"
    except Exception as e:
        return False, f"Error exportando: {e}"

# Ejemplo de uso de las mejoras:
if __name__ == "__main__":
    print("🔧 Mejoras sugeridas para renamer.py")
    print("Este archivo contiene ejemplos de funcionalidades adicionales")
    print("que se podrían implementar en la aplicación principal.")
