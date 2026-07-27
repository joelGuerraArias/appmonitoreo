#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para sincronizar coincidencias.md con Supabase
- Limpia duplicados por URL de Cloudinary (mantiene el más antiguo)
- Inserta coincidencias faltantes
"""

import os
import re
from datetime import datetime, date, time
from supabase import create_client, Client

# Configuración de Supabase
SUPABASE_URL = "https://lzbhtppgynjtvajrqwho.supabase.co"
SUPABASE_KEY = "YOUR_JWT_TOKEN"

print("🔄 Iniciando sincronización con Supabase...")
print("="*60)

try:
    # Conectar a Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conectado a Supabase")
    
    # Verificar archivo
    if not os.path.exists("coincidencias.md"):
        print("❌ Error: Archivo coincidencias.md no encontrado")
        exit(1)
    
    print("✅ Archivo coincidencias.md encontrado")
    print()
    
    # PASO 1: Limpiar duplicados por URL de Cloudinary
    print("🧹 PASO 1: Limpiando duplicados por URL de Cloudinary...")
    print("-"*60)
    
    result = supabase.table('alertas_medios').select('*').order('fecha_detencion', desc=False).execute()
    total_registros = len(result.data)
    print(f"📊 Total de registros en la tabla: {total_registros}")
    
    registros_por_url = {}
    duplicados_ids = []
    
    for reg in result.data:
        url = reg.get('url_video', '') or reg.get('enlace_directo', '')
        
        if url and 'cloudinary' in url.lower():
            if url in registros_por_url:
                registro_existente = registros_por_url[url]
                fecha_existente = registro_existente.get('fecha_detencion', '')
                fecha_actual = reg.get('fecha_detencion', '')
                
                if fecha_actual > fecha_existente:
                    duplicados_ids.append(reg['id'])
                    print(f"  🔍 Duplicado encontrado: ID {reg['id']} (más reciente: {fecha_actual[:19]})")
                else:
                    duplicados_ids.append(registro_existente['id'])
                    registros_por_url[url] = reg
                    print(f"  🔍 Duplicado encontrado: ID {registro_existente['id']} (más reciente: {fecha_existente[:19]})")
            else:
                registros_por_url[url] = reg
    
    if duplicados_ids:
        print(f"\n⚠️  Se encontraron {len(duplicados_ids)} registros duplicados")
        print("🗑️  Eliminando registros más recientes...")
        eliminados = 0
        
        for dup_id in duplicados_ids:
            try:
                supabase.table('alertas_medios').delete().eq('id', dup_id).execute()
                eliminados += 1
                print(f"  ✅ Eliminado ID: {dup_id}")
            except Exception as e:
                print(f"  ❌ Error eliminando ID {dup_id}: {e}")
        
        print(f"\n✅ Eliminados {eliminados} registros duplicados (manteniendo los más antiguos)")
    else:
        print("✅ No se encontraron duplicados por URL de Cloudinary")
    
    print()
    
    # PASO 2: Leer coincidencias.md
    print("📖 PASO 2: Extrayendo coincidencias del archivo MD...")
    print("-"*60)
    
    with open("coincidencias.md", "r", encoding="utf-8") as f:
        contenido = f.read()
    
    urls = re.findall(r'https://res\.cloudinary\.com/[^\s\)]+', contenido)
    bloques = re.split(r'\d+\.\s+', contenido)[1:]
    
    print(f"📊 URLs de Cloudinary encontradas: {len(urls)}")
    print(f"📊 Bloques de coincidencias: {len(bloques)}")
    
    coincidencias_nuevas = []
    
    for i, bloque in enumerate(bloques):
        try:
            termino_match = re.search(r'Menciones de (\w+)', bloque, re.IGNORECASE)
            medio_match = re.search(r'Medio:\s*([^\n]+)', bloque)
            hora_match = re.search(r'Hora:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{1,2}:\d{2})', bloque)
            contexto_match = re.search(r'Contexto:\s*([^\n]+)', bloque)
            resumen_match = re.search(r'Resumen:\s*([^\n]+)', bloque)
            archivo_match = re.search(r'URL Video:\s*([^\n]+)', bloque)
            
            if i < len(urls):
                url_video = urls[i]
                
                coincidencia = {
                    'fecha_detencion': datetime.now().isoformat(),
                    'termino_detectado': termino_match.group(1) if termino_match else 'desconocido',
                    'nombre_medio': medio_match.group(1).strip() if medio_match else 'Medio de Comunicacion',
                    'contexto': contexto_match.group(1).strip() if contexto_match else 'Sin contexto',
                    'resumen_ejecutivo': resumen_match.group(1).strip() if resumen_match else 'Sin resumen',
                    'url_video': url_video,
                    'nombre_archivo': archivo_match.group(1).strip() if archivo_match else 'desconocido',
                    'enlace_directo': url_video,
                    'transcripcion': bloque[:500],
                    'relevancia': 'Alta'
                }
                
                if hora_match:
                    fecha_str = hora_match.group(1)
                    hora_str = hora_match.group(2)
                    
                    try:
                        fecha_parts = fecha_str.split('/')
                        hora_parts = hora_str.split(':')
                        
                        coincidencia['fecha_programa'] = date(
                            int(fecha_parts[2]), 
                            int(fecha_parts[1]), 
                            int(fecha_parts[0])
                        ).isoformat()
                        
                        coincidencia['hora_programa'] = time(
                            int(hora_parts[0]), 
                            int(hora_parts[1])
                        ).isoformat()
                    except:
                        coincidencia['fecha_programa'] = date.today().isoformat()
                        coincidencia['hora_programa'] = time(12, 0).isoformat()
                
                coincidencias_nuevas.append(coincidencia)
                print(f"  ✅ Extraída coincidencia {i+1}: {coincidencia['termino_detectado']} - {coincidencia['nombre_medio']}")
        except Exception as e:
            print(f"  ❌ Error procesando bloque {i+1}: {e}")
    
    print()
    
    # PASO 3: Insertar coincidencias
    print("📥 PASO 3: Insertando coincidencias nuevas...")
    print("-"*60)
    
    insertadas = 0
    ya_existen = 0
    
    for idx, coincidencia in enumerate(coincidencias_nuevas, 1):
        try:
            existing = supabase.table('alertas_medios').select('id').eq('url_video', coincidencia['url_video']).execute()
            
            if existing.data and len(existing.data) > 0:
                ya_existen += 1
                print(f"  ⏭️  Coincidencia {idx} ya existe (URL: {coincidencia['url_video'][-30:]}...)")
            else:
                result = supabase.table('alertas_medios').insert(coincidencia).execute()
                if result.data:
                    insertadas += 1
                    print(f"  ✅ Insertada coincidencia {idx}: {coincidencia['termino_detectado']} - {coincidencia['nombre_medio']}")
        except Exception as e:
            print(f"  ❌ Error insertando coincidencia {idx}: {e}")
    
    print()
    print("="*60)
    print("✅ SINCRONIZACIÓN COMPLETADA")
    print("="*60)
    print(f"📊 Resultados:")
    print(f"   - Duplicados eliminados: {len(duplicados_ids)}")
    print(f"   - Coincidencias insertadas: {insertadas}")
    print(f"   - Ya existían: {ya_existen}")
    print(f"   - Total procesadas: {len(coincidencias_nuevas)}")
    print()
    print("✅ Ahora puedes usar el botón en la app para futuras sincronizaciones")
    
except Exception as e:
    print(f"\n❌ ERROR CRÍTICO: {e}")
    import traceback
    traceback.print_exc()
    exit(1)





















