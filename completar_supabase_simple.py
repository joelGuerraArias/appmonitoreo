# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from supabase import create_client, Client
from datetime import datetime, date, time
import re

SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def extraer_medio(nombre):
    if 'KNN' in nombre.upper():
        return 'KNN'
    elif 'CDN' in nombre.upper() or 'CANAL' in nombre.upper():
        return 'CDN CANAL'
    elif 'Telesistema' in nombre or 'TELESISTEMA' in nombre.upper():
        return 'Telesistema'
    elif '6am' in nombre.lower():
        return '6am la Manana'
    return 'Medio de Comunicacion'

def extraer_hora(nombre):
    match = re.search(r'(\d{1,2})[:\-_](\d{2})[:\-_](\d{2})', nombre)
    if match:
        try:
            h = int(match.group(1))
            m = int(match.group(2))
            s = int(match.group(3))
            return time(h, m, s).isoformat()
        except:
            return None
    return None

def extraer_fecha(nombre):
    match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', nombre)
    if match:
        try:
            y = int(match.group(1))
            m = int(match.group(2))
            d = int(match.group(3))
            return date(y, m, d).isoformat()
        except:
            return None
    return None

print("Iniciando actualizacion...")

try:
    result = supabase.table('alertas_medios').select('*').order('id', desc=True).limit(100).execute()
    
    print(f"Registros encontrados: {len(result.data)}")
    
    actualizados = 0
    sin_url = 0
    
    for reg in result.data:
        id_reg = reg['id']
        nombre = reg.get('nombre_archivo', '')
        
        updates = {}
        
        # Completar medio
        if not reg.get('nombre_medio') or reg['nombre_medio'] == 'Medio de Comunicacion':
            medio = extraer_medio(nombre)
            if medio != 'Medio de Comunicacion':
                updates['nombre_medio'] = medio
        
        # Completar hora
        if not reg.get('hora_programa'):
            hora = extraer_hora(nombre)
            if hora:
                updates['hora_programa'] = hora
        
        # Completar fecha
        if not reg.get('fecha_programa'):
            fecha = extraer_fecha(nombre)
            if fecha:
                updates['fecha_programa'] = fecha
        
        # Contar sin URL
        if not reg.get('url_video'):
            sin_url += 1
        
        # Actualizar
        if updates:
            try:
                supabase.table('alertas_medios').update(updates).eq('id', id_reg).execute()
                actualizados += 1
                print(f"ID {id_reg}: Actualizado - {list(updates.keys())}")
            except Exception as e:
                print(f"ID {id_reg}: Error - {str(e)[:50]}")
    
    print(f"\nRegistros actualizados: {actualizados}")
    print(f"Registros sin URL: {sin_url}")
    print("\nProceso completado!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()





















