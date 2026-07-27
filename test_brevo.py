# -*- coding: utf-8 -*-
import requests

api_key = 'YOUR_BREVO_API_KEY'
print('Probando API key de Brevo...')
print(f'Key: {api_key[:30]}...')

headers = {'api-key': api_key, 'Content-Type': 'application/json'}
r = requests.get('https://api.brevo.com/v3/account', headers=headers, timeout=10)

print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Email: {data.get("email", "N/A")}')
    print('Conexion exitosa!')
else:
    print(f'Error: {r.text[:200]}')











