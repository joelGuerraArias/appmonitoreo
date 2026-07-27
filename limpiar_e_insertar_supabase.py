# -*- coding: utf-8 -*-
"""
Script para:
1. Limpiar registros duplicados en Supabase
2. Insertar coincidencias únicas faltantes
"""
from supabase import create_client, Client
from datetime import datetime, date, time
import re

SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

print("="*80)
print("LIMPIEZA Y ACTUALIZACION DE SUPABASE")
print("="*80)
print()

# ==============================================================================
# PASO 1: LIMPIAR DUPLICADOS
# ==============================================================================
print("PASO 1: Eliminando registros duplicados...")
print("-"*80)

try:
    # Obtener todos los registros
    result = supabase.table('alertas_medios').select('*').order('id', desc=False).execute()
    
    print(f"Total de registros: {len(result.data)}")
    
    # Identificar duplicados por combinación de campos clave
    registros_unicos = {}
    duplicados_ids = []
    
    for reg in result.data:
        # Crear clave única basada en: termino + fecha + hora + medio
        clave = f"{reg.get('termino_detectado', '')}_{reg.get('fecha_programa', '')}_{reg.get('hora_programa', '')}_{reg.get('nombre_medio', '')}"
        
        if clave in registros_unicos:
            # Es un duplicado, marcar para eliminar
            duplicados_ids.append(reg['id'])
            print(f"  DUPLICADO: ID {reg['id']} - {reg.get('termino_detectado', 'N/A')} - {reg.get('nombre_medio', 'N/A')}")
        else:
            # Es único, guardar
            registros_unicos[clave] = reg
    
    # Eliminar duplicados
    if duplicados_ids:
        print(f"\nEliminando {len(duplicados_ids)} registros duplicados...")
        for dup_id in duplicados_ids:
            try:
                supabase.table('alertas_medios').delete().eq('id', dup_id).execute()
                print(f"  ✓ Eliminado ID {dup_id}")
            except Exception as e:
                print(f"  ✗ Error eliminando ID {dup_id}: {e}")
        print(f"\n✅ {len(duplicados_ids)} duplicados eliminados")
    else:
        print("✅ No se encontraron duplicados")
    
except Exception as e:
    print(f"❌ Error en limpieza: {e}")

print()

# ==============================================================================
# PASO 2: INSERTAR COINCIDENCIAS FALTANTES
# ==============================================================================
print("PASO 2: Insertando coincidencias únicas faltantes...")
print("-"*80)

# Definir las 5 coincidencias únicas
coincidencias_nuevas = [
    {
        'fecha_detencion': datetime(2025, 9, 29, 22, 35).isoformat(),
        'termino_detectado': 'apagones',
        'nombre_medio': 'Telesistema',
        'hora_programa': time(22, 35, 0).isoformat(),
        'fecha_programa': date(2025, 9, 29).isoformat(),
        'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759231601/video_analyzer_clips/video_analyzer_clips/apagones__20250930_072628_apagones_0m40s.mp4',
        'nombre_archivo': 'TELESISTEMA_480p_2025-09-29_22-35-28_seg000.mp4',
        'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759231601/video_analyzer_clips/video_analyzer_clips/apagones__20250930_072628_apagones_0m40s.mp4',
        'contexto': 'Análisis político sobre gestión gubernamental. Leonel Fernández critica usando apagones como ejemplo de retroceso.',
        'resumen_ejecutivo': 'Tema principal: Leonel Fernández hace crítica detallada usando apagones como ejemplo de retroceso e ineficiencia. Argumenta que aunque siempre hubo apagones, la situación ha empeorado drásticamente.',
        'transcripcion': 'Análisis político - Telenoticias con Cavada. Crítica de expresidente sobre gestión de servicios públicos.',
        'relevancia': 'Alta'
    },
    {
        'fecha_detencion': datetime(2025, 9, 29, 22, 49).isoformat(),
        'termino_detectado': 'apagones',
        'nombre_medio': 'Teleunivero',
        'hora_programa': time(22, 49, 3).isoformat(),
        'fecha_programa': date(2025, 9, 29).isoformat(),
        'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759231921/video_analyzer_clips/video_analyzer_clips/apagones__20250930_073143_apagones_1m54s.mp4',
        'nombre_archivo': 'TELEUNIVERO_480p_2025-09-29_22-49-03_seg046.mp4',
        'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759231921/video_analyzer_clips/video_analyzer_clips/apagones__20250930_073143_apagones_1m54s.mp4',
        'contexto': 'Panel de debate sobre problemas de servicios públicos. Panelista referencia a Esteban Rosario mencionando apagones.',
        'resumen_ejecutivo': 'Tema principal: Debate sobre servicios públicos. Mención breve de apagones como crítica al deterioro de servicios básicos durante panel en Las Noches con Bélgica.',
        'transcripcion': 'Panel de debate - Las Noches con Bélgica. Discusión sobre deterioro de servicios públicos.',
        'relevancia': 'Alta'
    },
    {
        'fecha_detencion': datetime(2025, 9, 29, 19, 49).isoformat(),
        'termino_detectado': 'apagones',
        'nombre_medio': 'CDN CANAL 37',
        'hora_programa': time(19, 49, 47).isoformat(),
        'fecha_programa': date(2025, 9, 29).isoformat(),
        'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759230798/video_analyzer_clips/video_analyzer_clips/apagones__20250930_071246_apagones_3m39s.mp4',
        'nombre_archivo': 'CDN CANAL 37_720p_2025-09-29_19-49-47_seg012.mp4',
        'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759230798/video_analyzer_clips/video_analyzer_clips/apagones__20250930_071246_apagones_3m39s.mp4',
        'contexto': 'Programa de opinión política. Contraste de gestiones. Danilo Medina afirma que durante su gestión electrificaron sin apagones.',
        'resumen_ejecutivo': 'Tema principal: Contraste de gestiones presidenciales. Danilo Medina destaca que durante su gestión se electrificó el país sin apagones, contrastando con la situación actual.',
        'transcripcion': 'Programa político - CDN Canal 37. Críticas al PLD y contraste de gestión eléctrica actual vs gobierno anterior.',
        'relevancia': 'Alta'
    },
    {
        'fecha_detencion': datetime(2025, 9, 29, 14, 0).isoformat(),
        'termino_detectado': 'apagones',
        'nombre_medio': 'Telemicro',
        'hora_programa': time(14, 0, 0).isoformat(),
        'fecha_programa': date(2025, 9, 29).isoformat(),
        'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759229262/video_analyzer_clips/video_analyzer_clips/apagones__20250930_064730_apagones_1m18s.mp4',
        'nombre_archivo': 'Telemicro_LA_OPCION_DE_LA_TARDE_INDEPENDENCIA_93.3_FM_clip_08.mp4',
        'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759229262/video_analyzer_clips/video_analyzer_clips/apagones__20250930_064730_apagones_1m18s.mp4',
        'contexto': 'Programa radial/televisivo interactivo. Conductor invita a oyentes a reportar problemas de servicios públicos incluyendo apagones.',
        'resumen_ejecutivo': 'Tema principal: Programa interactivo La Opción de la Tarde. Invitación a reportar problemas de servicios: "Si hay avería eléctrica, si hay apagones, todos señores reporten a través de nuestro chat en vivo".',
        'transcripcion': 'Programa interactivo - La Opción de la Tarde - Independencia 93.3 FM. Invitación a reportar problemas de servicios públicos.',
        'relevancia': 'Alta'
    },
    {
        'fecha_detencion': datetime(2025, 9, 29, 19, 17).isoformat(),
        'termino_detectado': 'edesur',
        'nombre_medio': 'CDN CANAL 37',
        'hora_programa': time(19, 17, 12).isoformat(),
        'fecha_programa': date(2025, 9, 29).isoformat(),
        'url_video': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759230548/video_analyzer_clips/video_analyzer_clips/edesur__20250930_070843_edesur_3m55s.mp4',
        'nombre_archivo': 'CDN CANAL 37_720p_2025-09-29_19-17-12_seg093.mp4',
        'enlace_directo': 'https://res.cloudinary.com/dhzxzbkmc/video/upload/v1759230548/video_analyzer_clips/video_analyzer_clips/edesur__20250930_070843_edesur_3m55s.mp4',
        'contexto': 'Segmento noticioso. Mención de EDESUR en contexto positivo: acciones contra conexiones ilegales.',
        'resumen_ejecutivo': 'Tema principal: Información noticiosa sobre EDESUR. Mención de acciones contra conexiones ilegales: "Y EDESUR desmantela más de 6.500 conexiones ilegales y regulariza a miles de clientes".',
        'transcripcion': 'Segmento noticioso - CDN Canal 37. Información sobre acciones de EDESUR contra conexiones ilegales.',
        'relevancia': 'Alta'
    }
]

# Verificar cuáles ya existen
print(f"Verificando {len(coincidencias_nuevas)} coincidencias...")

insertadas = 0
ya_existen = 0

for coincidencia in coincidencias_nuevas:
    # Buscar si ya existe
    try:
        existing = supabase.table('alertas_medios').select('id').eq('url_video', coincidencia['url_video']).execute()
        
        if existing.data and len(existing.data) > 0:
            ya_existen += 1
            print(f"  ⏭️ Ya existe: {coincidencia['termino_detectado']} - {coincidencia['nombre_medio']} ({coincidencia['hora_programa']})")
        else:
            # Insertar
            result = supabase.table('alertas_medios').insert(coincidencia).execute()
            if result.data:
                insertadas += 1
                print(f"  ✅ Insertada: {coincidencia['termino_detectado']} - {coincidencia['nombre_medio']} ({coincidencia['hora_programa']})")
            else:
                print(f"  ❌ Error insertando: {coincidencia['termino_detectado']}")
    except Exception as e:
        print(f"  ❌ Error procesando {coincidencia['termino_detectado']}: {e}")

print()
print("="*80)
print("RESUMEN")
print("="*80)
print(f"Coincidencias ya existentes: {ya_existen}")
print(f"Coincidencias insertadas: {insertadas}")
print(f"Total procesadas: {len(coincidencias_nuevas)}")
print()
print("✅ Proceso completado")





















