import os
import json
import re
from datetime import datetime
from supabase import create_client

def parse_md_analysis(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the separator used in the MD
    sections = re.split(r'\n---+\n', content)
    coincidences = []
    
    for section in sections:
        if "# 📊 ANÁLISIS COMPLETO:" not in section:
            continue
            
        try:
            # Extract basic info using regex
            archivo_match = re.search(r'-\s+\*\*Archivo:\*\*\s+`([^`]+)`', section)
            fecha_match = re.search(r'-\s+\*\*Fecha de análisis:\*\*\s+([^\r\n]+)', section)
            medio_match = re.search(r'-\s+\*\*Medio:\*\*\s+([^\r\n]+)', section)
            termino_match = re.search(r'-\s+\*\*Término detectado:\*\*\s+\*\*([^*]+)\*\*', section)
            video_url_match = re.search(r'-\s+\*\*Video Cloudinary:\*\*\s+\[[^\]]+\]\(([^\)]+)\)', section)
            
            # Extract transcription 
            trans_match = re.search(r'## 📝 Transcripción Completa\n\n(.*?)(?=\n---|$)', section, re.DOTALL)
            
            # Extract context
            context_match = re.search(r'Contexto:\s+(.*?)(?=\nPuntos clave:|$)', section, re.DOTALL)
            
            if archivo_match and termino_match:
                filename = archivo_match.group(1).strip()
                
                # Attempt to extract date/time from filename: Medio_Res_2026-02-24_07-04-57_seg134.mp4
                # Pattern: YYYY-MM-DD_HH-mm-ss
                time_from_filename = None
                dt_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})', filename)
                if dt_match:
                    date_part = dt_match.group(1)
                    hour_part = dt_match.group(2)
                    min_part = dt_match.group(3)
                    sec_part = dt_match.group(4)
                    time_from_filename = f"{date_part} {hour_part}:{min_part}:{sec_part}"
                
                item = {
                    'nombre_archivo': filename,
                    'fecha_analisis': fecha_match.group(1).strip() if fecha_match else '',
                    'fecha_occurrence': time_from_filename,
                    'medio': medio_match.group(1).strip() if medio_match else '',
                    'termino_detectado': termino_match.group(1).strip(),
                    'url_video': video_url_match.group(1).strip() if video_url_match else '',
                    'transcripcion': trans_match.group(1).strip() if trans_match else '',
                    'contexto': context_match.group(1).strip() if context_match else ''
                }
                coincidences.append(item)
        except Exception as e:
            print(f"Error parsing section: {e}")
            
    return coincidences

def upload_to_supabase():
    # Load config
    config_path = r"c:\Users\Joel Guerra\Desktop\grabaciones\clientes_config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    md_file = r"c:\Users\Joel Guerra\Desktop\grabaciones\videos procesados\Analisishoy_20260224.md"
    coincidencias = parse_md_analysis(md_file)
    print(f"Found {len(coincidencias)} coincidences in MD.")
    
    if not coincidencias:
        return

    for client_cfg in config.get('clientes', []):
        if not client_cfg.get('activo', False):
            continue
            
        supabase_cfg = client_cfg.get('supabase', {})
        if not supabase_cfg.get('enabled', False):
            continue
            
        url = supabase_cfg.get('url')
        key = supabase_cfg.get('anon_key')
        tabla = supabase_cfg.get('tabla_nombre', 'alertasmediosintrant')
        
        if tabla.startswith("📝") or tabla == "alertasmediosintrant":
            tabla = "alertasmediosintrant"
            
        print(f"\n--- Processing client: {client_cfg['nombre']} (Table: {tabla}) ---")
        
        try:
            supabase = create_client(url, key)
            
            # Detect columns to match adaptive schema
            columnas_reales = []
            try:
                res_col = supabase.table(tabla).select("*").limit(1).execute()
                if res_col.data:
                    columnas_reales = list(res_col.data[0].keys())
                    print(f"Detected columns: {columnas_reales}")
            except Exception as col_err:
                print(f"Could not detect columns: {col_err}")

            count = 0
            for item in coincidencias:
                # Determine best date
                # Prioritize occurrence time from filename, fallback to analysis time
                best_date = item['fecha_occurrence'] if item['fecha_occurrence'] else item['fecha_analisis']
                if not best_date:
                    best_date = datetime.now().isoformat()
                
                # Prepare data
                data = {
                    'termino_detectado': item['termino_detectado'],
                    'nombre_archivo': item['nombre_archivo'],
                    'tipo_archivo': 'video/mp4',
                    'contexto': item['contexto'][:500],
                    'resumen_ejecutivo': '',
                    'fecha_detencion': best_date,
                    'hora_programa': '13:41:03.538977',
                    'url_video': item['url_video'],
                    'cliente': client_cfg['nombre'],
                    'transcripcion': item['transcripcion'][:2000]
                }
                
                if 'cliente' not in columnas_reales and 'nombre_medio' in columnas_reales:
                    data['nombre_medio'] = client_cfg['nombre']
                
                if columnas_reales:
                    filtered_data = {k: v for k, v in data.items() if k in columnas_reales}
                else:
                    filtered_data = data
                
                try:
                    # Use upsert or delete/insert to refresh with hours
                    # In this system, we identify by 'nombre_archivo'
                    # First check if exists
                    res_exists = supabase.table(tabla).select("id").eq("nombre_archivo", item['nombre_archivo']).execute()
                    
                    if res_exists.data:
                        # Update
                        row_id = res_exists.data[0]['id']
                        supabase.table(tabla).update(filtered_data).eq("id", row_id).execute()
                        mensaje = "Updated"
                    else:
                        # Insert
                        supabase.table(tabla).insert(filtered_data).execute()
                        mensaje = "Inserted"
                    
                    count += 1
                    if count % 10 == 0:
                        print(f"  Processed {count} items... (Last timestamp: {best_date})")
                except Exception as ins_err:
                    print(f"  Error processing {item['nombre_archivo']}: {ins_err}")
            
            print(f"Finished client {client_cfg['nombre']}. Total processed: {count}")
            
        except Exception as e:
            print(f"Error connecting to Supabase for {client_cfg['nombre']}: {e}")

if __name__ == "__main__":
    upload_to_supabase()
