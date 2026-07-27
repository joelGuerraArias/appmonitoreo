# -*- coding: utf-8 -*-
from supabase import create_client, Client
from datetime import datetime, date, time
import re

SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

log_file = open('completar_supabase.log', 'w', encoding='utf-8')

def log(msg):
    log_file.write(msg + '\n')
    log_file.flush()

def extraer_medio(nombre):
    if 'KNN' in nombre.upper():
        return 'KNN'
    elif 'CDN' in nombre.upper() or 'CANAL' in nombre.upper():
        return 'CDN CANAL'
    elif 'Telesistema' in nombre or 'TELESISTEMA' in nombre.upper():
        return 'Telesistema'
    elif '6am' in nombre.lower():
        return '6am la Manana'
    return None

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

log("="*70)
log("COMPLETANDO DATOS EN SUPABASE")
log("="*70)
log("")

try:
    log("Consultando registros...")
    result = supabase.table('alertas_medios').select('*').order('id', desc=True).limit(100).execute()
    
    log(f"Registros encontrados: {len(result.data)}")
    log("")
    
    actualizados = 0
    sin_url = 0
    
    for reg in result.data:
        id_reg = reg['id']
        nombre = reg.get('nombre_archivo', '')
        termino = reg.get('termino_detectado', '')
        
        updates = {}
        cambios = []
        
        # Completar medio
        actual_medio = reg.get('nombre_medio', '')
        if not actual_medio or actual_medio == 'Medio de Comunicacion':
            medio = extraer_medio(nombre)
            if medio:
                updates['nombre_medio'] = medio
                cambios.append(f"medio->{medio}")
        
        # Completar hora
        if not reg.get('hora_programa'):
            hora = extraer_hora(nombre)
            if hora:
                updates['hora_programa'] = hora
                cambios.append(f"hora->{hora}")
        
        # Completar fecha
        if not reg.get('fecha_programa'):
            fecha = extraer_fecha(nombre)
            if fecha:
                updates['fecha_programa'] = fecha
                cambios.append(f"fecha->{fecha}")
        
        # Contar sin URL
        if not reg.get('url_video'):
            sin_url += 1
            cambios.append("URL:NULL")
        
        # Actualizar
        if updates:
            try:
                supabase.table('alertas_medios').update(updates).eq('id', id_reg).execute()
                actualizados += 1
                log(f"OK ID {id_reg} [{termino}]: {', '.join(cambios)}")
            except Exception as e:
                log(f"ERROR ID {id_reg}: {str(e)[:80]}")
        elif cambios:
            log(f"INFO ID {id_reg} [{termino}]: {', '.join(cambios)}")
    
    log("")
    log("="*70)
    log(f"Registros revisados: {len(result.data)}")
    log(f"Registros actualizados: {actualizados}")
    log(f"Registros sin URL: {sin_url}")
    log("="*70)
    log("")
    log("PROCESO COMPLETADO!")
    
except Exception as e:
    log(f"ERROR GENERAL: {e}")
    import traceback
    log(traceback.format_exc())

log_file.close()
print("Log guardado en: completar_supabase.log")





















