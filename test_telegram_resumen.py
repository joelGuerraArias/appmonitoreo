"""
Script de prueba: envia el resumen de Analisishoy_*.md a Telegram.
Aplica el mismo escape mejorado (preservando puntuacion) que el sistema principal.
"""
import re
import requests

# --- Configuracion (tomada de clientes_config.json) ---
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID   = "@edesuralertas"

ARCHIVO_MD = r"c:\Users\Joel Guerra\Desktop\grabaciones\Analisishoy_20260223.md"

# --- Funcion de escape mejorada (identica a la del sistema) ---
def escape_telegram_text(text):
    if not text:
        return ""
    # Preserva: . , : - / #  |  Elimina: * _ ` [ ] ( ) ~ > + = { } ! \\
    text = re.sub(r'[*_`\[\]()~>+=|{}!\\#]', '', text)
    text = text.replace('\n\n\n', '\n\n').strip()
    return text

# --- Leer el archivo ---
with open(ARCHIVO_MD, encoding='utf-8') as f:
    contenido = f.read()

texto_limpio = escape_telegram_text(contenido)

# --- Telegram: max 4096 chars por mensaje; dividir si hace falta ---
MAX_TG = 4096
partes = []
resto = texto_limpio
while resto:
    if len(resto) <= MAX_TG:
        partes.append(resto)
        break
    corte = resto.rfind('\n', 0, MAX_TG)
    if corte <= 0:
        corte = MAX_TG
    partes.append(resto[:corte].strip())
    resto = resto[corte:].lstrip()

print(f"Enviando {len(partes)} parte(s) a {CHAT_ID} ...")

for i, parte in enumerate(partes, 1):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': parte,
        'disable_web_page_preview': True,
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code == 200:
        print(f"  OK  | Parte {i}/{len(partes)} ({len(parte)} chars)")
    else:
        print(f"  ERR | Parte {i}/{len(partes)}: {r.status_code} - {r.text[:200]}")

print("Listo.")
