#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para completar datos inconclusos en Supabase - Modo automático
"""

from supabase import create_client, Client
from datetime import datetime, date, time
import re

# Configuración de Supabase
SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

# Inicializar cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def extraer_info_medio_hora(nombre_archivo):
    """Extrae información del medio y hora del nombre del archivo"""
    nombre_limpio = nombre_archivo.replace('_', ' ').replace('-', ' ')
    
    # Buscar nombres de medios conocidos
    medios_conocidos = ['KNN', 'CDN', 'CANAL', 'Telesistema', '6am', 'Mañana', 'TELECENTRO', 'ANTENA']
    
    for medio in medios_conocidos:
        if medio.lower() in nombre_limpio.lower():
            # Extraer hora si existe
            match_hora = re.search(r'(\d{1,2})[:\-_](\d{2})[:\-_](\d{2})', nombre_archivo)
            if match_hora:
                hora_str = f"{match_hora.group(1)}:{match_hora.group(2)}:{match_hora.group(3)}"
                return f"{medio} - {hora_str}"
            return medio
    
    return "Medio de Comunicación"

def parsear_nombre_medio(nombre_archivo):
    """Extrae el nombre del medio"""
    # Buscar patrones comunes
    if 'KNN' in nombre_archivo.upper():
        return 'KNN'
    elif 'CDN' in nombre_archivo.upper():
        return 'CDN CANAL'
    elif 'Telesistema' in nombre_archivo:
        return 'Telesistema'
    elif '6am' in nombre_archivo.lower() or 'mañana' in nombre_archivo.lower():
        return '6am la Mañana'
    
    info = extraer_info_medio_hora(nombre_archivo)
    partes = info.split('-')
    return partes[0].strip() if partes else "Medio de Comunicación"

def parsear_hora_programa(nombre_archivo):
    """Extrae y parsea la hora del programa"""
    # Buscar patrón HH:MM:SS o HH-MM-SS o HH_MM_SS
    match_hora = re.search(r'(\d{1,2})[:\-_](\d{2})[:\-_](\d{2})', nombre_archivo)
    if match_hora:
        try:
            hora = int(match_hora.group(1))
            minuto = int(match_hora.group(2))
            segundo = int(match_hora.group(3))
            return time(hora, minuto, segundo).isoformat()
        except:
            pass
    
    return None

def parsear_fecha_programa(nombre_archivo):
    """Extrae y parsea la fecha del programa"""
    # Buscar patrón YYYY-MM-DD o YYYYMMDD
    match_fecha = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', nombre_archivo)
    if match_fecha:
        try:
            año = int(match_fecha.group(1))
            mes = int(match_fecha.group(2))
            dia = int(match_fecha.group(3))
            return date(año, mes, dia).isoformat()
        except:
            pass
    
    return None

print("="*70)
print("🔧 COMPLETANDO DATOS INCONCLUSOS EN SUPABASE")
print("="*70)
print()

try:
    # Obtener registros con datos incompletos
    print("🔍 Consultando registros...")
    result = supabase.table('alertas_medios').select('*').order('id', desc=True).limit(100).execute()
    
    if not result.data:
        print("❌ No se encontraron registros")
        exit()
    
    print(f"📊 Encontrados {len(result.data)} registros para revisar\n")
    
    registros_actualizados = 0
    registros_sin_url = 0
    
    for registro in result.data:
        id_registro = registro['id']
        nombre_archivo = registro.get('nombre_archivo', '')
        termino = registro.get('termino_detectado', '')
        
        datos_actualizados = {}
        cambios = []
        
        # 1. Completar nombre_medio
        if not registro.get('nombre_medio') or registro['nombre_medio'] == 'Medio de Comunicación':
            nombre_medio = parsear_nombre_medio(nombre_archivo)
            if nombre_medio and nombre_medio != 'Medio de Comunicación':
                datos_actualizados['nombre_medio'] = nombre_medio
                cambios.append(f"medio→{nombre_medio}")
        
        # 2. Completar hora_programa
        if not registro.get('hora_programa'):
            hora_programa = parsear_hora_programa(nombre_archivo)
            if hora_programa:
                datos_actualizados['hora_programa'] = hora_programa
                cambios.append(f"hora→{hora_programa}")
        
        # 3. Completar fecha_programa
        if not registro.get('fecha_programa'):
            fecha_programa = parsear_fecha_programa(nombre_archivo)
            if fecha_programa:
                datos_actualizados['fecha_programa'] = fecha_programa
                cambios.append(f"fecha→{fecha_programa}")
        
        # 4. Verificar URL
        if not registro.get('url_video'):
            registros_sin_url += 1
            cambios.append("⚠️ URL NULL")
        
        # 5. Actualizar si hay cambios
        if datos_actualizados:
            try:
                update_result = supabase.table('alertas_medios').update(datos_actualizados).eq('id', id_registro).execute()
                
                if update_result.data:
                    registros_actualizados += 1
                    print(f"✅ ID {id_registro} [{termino}]: {', '.join(cambios)}")
                else:
                    print(f"❌ ID {id_registro}: Error en actualización")
            except Exception as e:
                print(f"❌ ID {id_registro}: {str(e)[:50]}")
        elif cambios:
            print(f"ℹ️ ID {id_registro} [{termino}]: {', '.join(cambios)}")
    
    print("\n" + "="*70)
    print("📊 RESUMEN:")
    print(f"  • Registros revisados: {len(result.data)}")
    print(f"  • Registros actualizados: {registros_actualizados}")
    print(f"  • Registros sin URL: {registros_sin_url}")
    print("="*70)
    
    # Mostrar registros que aún están incompletos
    print("\n🔍 VERIFICANDO REGISTROS INCOMPLETOS...")
    result2 = supabase.table('alertas_medios').select('id, termino_detectado, nombre_archivo, nombre_medio, hora_programa, fecha_programa, url_video').order('id', desc=True).limit(20).execute()
    
    incompletos = 0
    for reg in result2.data:
        problemas = []
        
        if not reg.get('nombre_medio') or reg['nombre_medio'] == 'Medio de Comunicación':
            problemas.append('medio')
        if not reg.get('hora_programa'):
            problemas.append('hora')
        if not reg.get('fecha_programa'):
            problemas.append('fecha')
        if not reg.get('url_video'):
            problemas.append('URL')
        
        if problemas:
            incompletos += 1
            print(f"  ⚠️ ID {reg['id']} [{reg.get('termino_detectado', 'N/A')}]: Faltan {', '.join(problemas)}")
    
    if incompletos == 0:
        print("  ✅ Todos los registros están completos (excepto URLs que requieren re-subida)")
    else:
        print(f"\n  Total incompletos: {incompletos}/20")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Proceso finalizado")





















