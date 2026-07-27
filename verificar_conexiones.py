# -*- coding: utf-8 -*-
import requests
import json
import smtplib
from supabase import create_client
import cloudinary
import cloudinary.api

# Cargar clientes
with open('clientes_config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*60)
print('VERIFICACION DE CONEXIONES DE CLIENTES')
print('='*60)

for cliente in data['clientes']:
    nombre = cliente['nombre']
    print(f'\n[CLIENTE] {nombre}')
    print('-'*40)
    
    # 1. Telegram
    tg = cliente.get('telegram', {})
    if tg.get('enabled') and tg.get('bot_token'):
        try:
            url = f"https://api.telegram.org/bot{tg['bot_token']}/getMe"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                bot_info = r.json()
                print(f'  [OK] Telegram: Bot @{bot_info["result"]["username"]}')
            else:
                print(f'  [ERROR] Telegram: Status {r.status_code}')
        except Exception as e:
            print(f'  [ERROR] Telegram: {str(e)[:50]}')
    else:
        print(f'  [--] Telegram: No configurado')
    
    # 2. Webhook
    wh = cliente.get('webhook', {})
    if wh.get('enabled') and wh.get('url'):
        try:
            r = requests.post(wh['url'], json={'test': True}, timeout=10)
            print(f'  [OK] Webhook: Status {r.status_code}')
        except Exception as e:
            print(f'  [ERROR] Webhook: {str(e)[:50]}')
    else:
        print(f'  [--] Webhook: No configurado/deshabilitado')
    
    # 3. Brevo (SMTP)
    br = cliente.get('brevo', {})
    if br.get('enabled') and br.get('api_key'):
        try:
            smtp_server = br.get('smtp_server', 'smtp-relay.brevo.com')
            smtp_port = br.get('smtp_port', 587)
            smtp_user = br.get('smtp_user', br.get('sender_email', ''))
            api_key = br['api_key']
            
            # Probar conexión SMTP
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, api_key)
            
            dest_count = len(br.get("correos_destinatarios", []))
            print(f'  [OK] Brevo SMTP: Conectado ({dest_count} destinatarios)')
        except Exception as e:
            print(f'  [ERROR] Brevo: {str(e)[:50]}')
    else:
        print(f'  [--] Brevo: No configurado')
    
    # 4. Cloudinary
    cl = cliente.get('cloudinary', {})
    if cl.get('enabled') and cl.get('cloud_name'):
        try:
            cloudinary.config(
                cloud_name=cl['cloud_name'],
                api_key=cl['api_key'],
                api_secret=cl['api_secret']
            )
            result = cloudinary.api.ping()
            folder = cl.get("folder", "N/A")
            print(f'  [OK] Cloudinary: Conectado (carpeta: {folder})')
        except Exception as e:
            print(f'  [ERROR] Cloudinary: {str(e)[:50]}')
    else:
        print(f'  [--] Cloudinary: No configurado')
    
    # 5. Supabase
    sb = cliente.get('supabase', {})
    if sb.get('enabled') and sb.get('url'):
        try:
            client = create_client(sb['url'], sb['anon_key'])
            tabla = sb.get('tabla_nombre', 'alertas_medios')
            try:
                client.table(tabla).select('id').limit(1).execute()
                print(f'  [OK] Supabase: Tabla "{tabla}" existe')
            except Exception as te:
                if 'does not exist' in str(te).lower():
                    print(f'  [WARN] Supabase: Conexion OK, tabla "{tabla}" NO existe')
                else:
                    print(f'  [WARN] Supabase: {str(te)[:50]}')
        except Exception as e:
            print(f'  [ERROR] Supabase: {str(e)[:50]}')
    else:
        print(f'  [--] Supabase: No configurado')
    
    # 6. Google Drive
    gd = cliente.get('google_drive', {})
    if gd.get('enabled') and gd.get('folder_id'):
        folder_id = gd["folder_id"]
        print(f'  [OK] Google Drive: Carpeta ID configurada ({folder_id[:15]}...)')
    else:
        print(f'  [--] Google Drive: No configurado')

print('\n' + '='*60)
print('VERIFICACION COMPLETADA')
print('='*60)
