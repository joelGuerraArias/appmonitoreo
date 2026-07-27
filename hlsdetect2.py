import os
import re
import sys
import time
import json
import subprocess
from pathlib import Path

import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

# =================== CONFIG ===================
# Extensión: The Stream Detector (Chrome Web Store)
EXTENSION_ID = "iakkmkmhhckcmoiibcfjnooibphlobak"

# URL objetivo por defecto (puedes pasar otra por CLI)
# DEFAULT_TARGET_URL = "https://cdn.com.do/envivo/"
DEFAULT_TARGET_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Video de prueba con streams

# Espera para que la extensión detecte (ajusta si tarda)
ESPERA_EXT_S = 25

# Salida: carpeta y archivo (se crea si no existe)
SALIDA_DIR = r"C:\Users\Administrador\Desktop\grabaciones"
SALIDA_FILE = "stream.txt"  # se abre en el Bloc de notas
# ==============================================

# Patrones de URL (prioriza HLS; incluye DASH como fallback)
URL_PATS = [
    re.compile(r"https?://[^\s\"']+?\.m3u8[^\s\"']*", re.IGNORECASE),
    re.compile(r"https?://[^\s\"']+?\.mpd[^\s\"']*", re.IGNORECASE),
    re.compile(r"https?://[^\s\"']+", re.IGNORECASE),  # último recurso
]

# Páginas típicas dentro de la extensión (popup/opciones/historial)
EXT_PAGES = [
    "options.html", "options/index.html", "index.html",
    "popup.html", "ui.html", "panel.html", "results.html", "history.html"
]

# Clics básicos por si el UI requiere pulsar "Copy" o similar
CLICK_SELECTORS = [
    "button.copy", "button#copy", "button[aria-label*=copi]",   # copiar/copy
    "button[title*=Copy]", "button[title*=copiar]",
    "button", "input[type=button]", "a.copy"
]

def find_match_url(text: str):
    if not text:
        return None
    for pat in URL_PATS:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None

def posibles_perfiles():
    """Perfiles típicos de Chrome por SO."""
    if os.name == "nt":
        base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    else:
        base = os.path.expanduser("~/.config/google-chrome")

    out = []
    for name in ["Default"] + [f"Profile {i}" for i in range(1, 8)]:
        p = os.path.join(base, name)
        if os.path.isdir(p):
            out.append(p)
    return out

def buscar_dir_extension(extension_id: str):
    """
    Busca la carpeta instalada de la extensión en perfiles locales
    y devuelve la ruta a la versión más reciente (con manifest.json).
    """
    for prof in posibles_perfiles():
        ext_root = os.path.join(prof, "Extensions", extension_id)
        if os.path.isdir(ext_root):
            versions = [d for d in os.listdir(ext_root) if os.path.isdir(os.path.join(ext_root, d))]
            if not versions:
                continue
            versions.sort(reverse=True)  # usar la más reciente
            for v in versions:
                candidate = os.path.join(ext_root, v)
                if os.path.isfile(os.path.join(candidate, "manifest.json")):
                    return candidate
    return None

def abrir_pagina_extension(driver, ext_id: str, page_name: str):
    """Abre nueva pestaña a chrome-extension://<ID>/<page>."""
    url = f"chrome-extension://{ext_id}/{page_name}"
    try:
        driver.switch_to.new_window('tab')
        driver.get(url)
        time.sleep(1.0)
        return True
    except WebDriverException:
        # cerrar pestaña si quedó a medias y volver a la original
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass
        return False

def raspar_pestana_actual(driver):
    """
    1) Buscar URL en el HTML.
    2) Intentar clics "Copy".
    3) Revisar href/value/text de nodos comunes.
    4) Leer chrome.storage.local (solo en páginas de la extensión).
    """
    # 1) HTML
    html = driver.page_source or ""
    u = find_match_url(html)
    if u:
        return u

    # 2) Clics sencillos
    for sel in CLICK_SELECTORS:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                elems[0].click()
                time.sleep(0.6)
                html = driver.page_source or ""
                u = find_match_url(html)
                if u:
                    return u
        except Exception:
            pass

    # 3) Nodos comunes
    for tag in ["a", "code", "pre", "input", "textarea", "span", "div"]:
        try:
            nodes = driver.find_elements(By.TAG_NAME, tag)
        except Exception:
            nodes = []
        for n in nodes:
            try:
                href = n.get_attribute("href")
                if href:
                    u = find_match_url(href)
                    if u:
                        return u
                val = n.get_attribute("value")
                if val:
                    u = find_match_url(val)
                    if u:
                        return u
                txt = n.text
                if txt:
                    u = find_match_url(txt)
                    if u:
                        return u
            except Exception:
                continue

    # 4) chrome.storage.local (desde páginas de la extensión)
    try:
        result = driver.execute_async_script("""
            var done = arguments[0];
            (function(){
              try {
                if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
                  chrome.storage.local.get(null, function(items){
                    done({ok:true, items: items});
                  });
                } else {
                  done({ok:false, reason: 'no-chrome-storage'});
                }
              } catch(e){
                done({ok:false, reason: e.toString()});
              }
            })();
        """)
        if result and result.get("ok"):
            s = json.dumps(result.get("items", {}), ensure_ascii=False)
            u = find_match_url(s)
            if u:
                return u
    except Exception:
        pass

    return None

def abrir_notepad_con(archivo_path: str):
    """Abre el archivo TXT con Notepad (Windows)."""
    try:
        os.startfile(archivo_path)  # abre con el editor por defecto
    except Exception:
        try:
            subprocess.Popen(["notepad.exe", archivo_path])
        except Exception:
            pass

def cleanup_chrome_processes():
    """Limpia procesos de Chrome que puedan estar causando conflictos."""
    try:
        # En Windows
        result = subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Procesos de Chrome limpiados")
            time.sleep(1)
    except Exception as e:
        print(f"⚠️ Error limpiando procesos: {e}")

def main():
    target_url = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_TARGET_URL

    # Limpiar procesos de Chrome conflictivos
    print("🧹 Limpiando procesos de Chrome...")
    cleanup_chrome_processes()

    # Asegurar carpeta de salida
    Path(SALIDA_DIR).mkdir(parents=True, exist_ok=True)
    salida_path = os.path.join(SALIDA_DIR, SALIDA_FILE)

    # Intentar localizar carpeta "unpacked" de la extensión instalada
    ext_dir = buscar_dir_extension(EXTENSION_ID)

    chrome_options = Options()
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    # IMPORTANTE: no headless; los popups de extensión no funcionan en headless

    # Forzar uso de Chrome real en lugar de Chromium
    # Intentar múltiples ubicaciones comunes de Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]

    chrome_binary = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_binary = path
            break

    if chrome_binary:
        chrome_options.binary_location = chrome_binary
        print(f"✅ Usando Chrome desde: {chrome_binary}")
    else:
        print("⚠️ No se encontró Chrome en ubicaciones estándar, usando Chromium por defecto")

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    if ext_dir and os.path.isfile(os.path.join(ext_dir, "manifest.json")):
        chrome_options.add_argument(f"--disable-extensions-except={ext_dir}")
        chrome_options.add_argument(f"--load-extension={ext_dir}")
        print(f"🧩 Usando The Stream Detector desde: {ext_dir}")
    else:
        print("⚠️ No se localizó automáticamente la carpeta instalada de la extensión.")
        print("   Si no abre la extensión, puedes lanzar con tu perfil real descomentando estas líneas y ajustando la ruta:")
        print("   chrome_options.add_argument(r'--user-data-dir=C:\\Users\\Administrador\\AppData\\Local\\Google\\Chrome\\User Data')")
        print("   chrome_options.add_argument('--profile-directory=Default')")
        # Si quieres forzar el perfil real, descomenta y ajusta:
        # chrome_options.add_argument(r'--user-data-dir=C:\Users\Administrador\AppData\Local\Google\Chrome\User Data')
        # chrome_options.add_argument('--profile-directory=Default')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 1) Abre la página objetivo (como lo harías tú)
        print(f"🌐 Abriendo: {target_url}")
        driver.get(target_url)

        # 2) Dale tiempo a que la extensión detecte el stream
        print(f"⏳ Esperando {ESPERA_EXT_S}s para detección...")
        for i in range(ESPERA_EXT_S):
            time.sleep(1)
            if i % 5 == 0:  # Mostrar progreso cada 5 segundos
                print(f"   ⏱️ {i}s...")

        print("🔍 Revisando si la extensión detectó streams...")

        # 3) DEBUG: Inspeccionar la página actual primero
        print("🔍 DEBUG: Inspeccionando página actual...")
        current_url = driver.current_url
        print(f"   📄 URL actual: {current_url}")

        # Buscar streams en la página actual (sin extensión)
        page_source = driver.page_source
        direct_streams = find_match_url(page_source)
        if direct_streams:
            print(f"✅ Stream encontrado directamente en la página: {direct_streams}")
            found = direct_streams

        # 4) Abrir vistas internas de la extensión y extraer
        if not found:
            print("🔍 Abriendo interfaces de la extensión...")
            for vista in EXT_PAGES:
                print(f"   🔎 Probando: {vista}")
                ok = abrir_pagina_extension(driver, EXTENSION_ID, vista)
                if not ok:
                    print(f"      ❌ No se pudo abrir {vista}")
                    continue

                try:
                    # DEBUG: Ver qué hay en esta página de la extensión
                    ext_page_source = driver.page_source
                    print(f"      📄 Contenido de {vista}: {len(ext_page_source)} caracteres")

                    url = raspar_pestana_actual(driver)
                    if url:
                        print(f"      ✅ Stream encontrado en {vista}: {url}")
                        found = url
                        break
                    else:
                        print(f"      ❌ No se encontró stream en {vista}")
                finally:
                    # cierra pestaña de la extensión y vuelve a la original
                    try:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except Exception:
                        pass

        # Crear el archivo TXT siempre (incluso si no se encontraron streams)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        if found:
            print(f"✅ Stream capturado: {found}")
            # Copia al portapapeles
            try:
                pyperclip.copy(found)
                print("📋 Copiado al portapapeles.")
            except Exception:
                pass

            # Escribe con timestamp
            with open(salida_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {found}\n")
            print(f"💾 Guardado en: {salida_path}")

            # Abre Notepad mostrando el archivo
            abrir_notepad_con(salida_path)
        else:
            print("❗ No se pudo leer la URL desde las vistas estándar de la extensión.")
            print("   🔍 Posibles causas:")
            print("   - El sitio no tiene streams detectables")
            print("   - La extensión necesita interacción manual")
            print("   - El video debe reproducirse manualmente primero")
            print("   - YouTube puede bloquear la detección automática")
            print("   ")
            print("   💡 Soluciones:")
            print("   - Prueba con un sitio de streaming diferente")
            print("   - Asegúrate de que la extensión esté instalada en Chrome")
            print("   - Intenta reproducir el video manualmente primero")

            # Crear archivo TXT con el resultado negativo
            with open(salida_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] No se encontraron streams detectables en {target_url}\n")
            print(f"💾 Resultado guardado en: {salida_path}")

            # Abre Notepad mostrando el archivo
            abrir_notepad_con(salida_path)

        print("🔍 Script completado. Revisa el navegador para ver los resultados.")
        print("✅ Cerrando navegador automáticamente...")
        time.sleep(2)  # Dar tiempo para ver los resultados

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
