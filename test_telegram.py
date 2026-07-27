# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime

# Cargar clientes
with open('clientes_config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*60)
print('ENVIANDO MENSAJE TEST A TELEGRAM')
print('='*60)

for cliente in data['clientes']:
    nombre = cliente['nombre']
    tg = cliente.get('telegram', {})
    
    if tg.get('enabled') and tg.get('bot_token') and tg.get('chat_id'):
        bot_token = tg['bot_token']
        chat_id = tg['chat_id']
        
        mensaje = f'''TEST DE CONEXION

Cliente: {nombre}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Sistema Multi-Cliente funcionando correctamente'''

        print(f'\n[{nombre}]')
        print(f'  Bot: {bot_token[:20]}...')
        print(f'  Chat: {chat_id}')
        
        try:
            url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': mensaje
            }
            r = requests.post(url, json=payload, timeout=10)
            
            if r.status_code == 200:
                print(f'  [OK] Mensaje enviado!')
            else:
                error = r.json().get('description', r.text[:100])
                print(f'  [ERROR] {error}')
        except Exception as e:
            print(f'  [ERROR] {str(e)[:50]}')
    else:
        print(f'\n[{nombre}]')
        print(f'  [--] Telegram no configurado')

print('\n' + '='*60)
print('TEST COMPLETADO')
print('='*60)
