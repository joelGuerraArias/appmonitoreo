# -*- coding: utf-8 -*-
from supabase import create_client, Client

SUPABASE_URL = "https://sfvbcprhfmwglqpyyfxz.supabase.co"
SUPABASE_ANON_KEY = "YOUR_JWT_TOKEN"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

log_file = open('ver_datos.log', 'w', encoding='utf-8')

def log(msg):
    log_file.write(msg + '\n')
    log_file.flush()

log("="*80)
log("ESTADO ACTUAL DE REGISTROS EN SUPABASE")
log("="*80)
log("")

try:
    result = supabase.table('alertas_medios').select('id, termino_detectado, nombre_medio, hora_programa, fecha_programa, url_video, nombre_archivo').order('id', desc=True).limit(20).execute()
    
    log(f"Ultimos {len(result.data)} registros:")
    log("")
    
    completos = 0
    incompletos = 0
    
    for reg in result.data:
        id_reg = reg['id']
        termino = reg.get('termino_detectado', 'N/A')
        medio = reg.get('nombre_medio', 'N/A')
        hora = reg.get('hora_programa', 'NULL')
        fecha = reg.get('fecha_programa', 'NULL')
        url = reg.get('url_video', 'NULL')
        archivo = reg.get('nombre_archivo', 'N/A')
        
        problemas = []
        if medio == 'N/A' or medio == 'Medio de Comunicacion':
            problemas.append('medio')
        if hora == 'NULL':
            problemas.append('hora')
        if fecha == 'NULL':
            problemas.append('fecha')
        if url == 'NULL' or not url:
            problemas.append('URL')
        
        if problemas:
            incompletos += 1
            log(f"ID {id_reg} - [{termino}]")
            log(f"  Archivo: {archivo}")
            log(f"  Medio: {medio}")
            log(f"  Hora: {hora}")
            log(f"  Fecha: {fecha}")
            log(f"  URL: {'SI' if url and url != 'NULL' else 'NO'}")
            log(f"  FALTANTES: {', '.join(problemas)}")
            log("")
        else:
            completos += 1
            log(f"OK ID {id_reg} - [{termino}] - {medio} - {hora} - {fecha} - URL:SI")
    
    log("")
    log("="*80)
    log(f"RESUMEN:")
    log(f"  Registros completos: {completos}")
    log(f"  Registros incompletos: {incompletos}")
    log("="*80)
    
except Exception as e:
    log(f"ERROR: {e}")
    import traceback
    log(traceback.format_exc())

log_file.close()
print("Log guardado en: ver_datos.log")





















