import os
import sys
import time
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote, quote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración específica para CDN
HEADLESS = False
WAIT_MS = 15000  # Aumentado para dar más tiempo
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

def detect_cdn_streams(page_url: str, headless: bool, wait_ms: int):
    print(f"[INFO] Analizando: {page_url}")
    found_streams = []

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=headless, channel="chrome")
            print("[OK] Chrome lanzado exitosamente")
        except Exception as e:
            print(f"[ERROR] No pude lanzar Chrome: {e}")
            return []

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        def on_response(res):
            try:
                u = res.url
                ct = (res.headers or {}).get("content-type", "").lower()

                # Buscar diferentes tipos de streams
                if any(pattern in u.lower() for pattern in [
                    ".m3u8", "mpegurl", ".mp4", "video", "stream", "live", "hls"
                ]):
                    print(f"[STREAM FOUND] {u}")
                    print(f"[CONTENT-TYPE] {ct}")
                    found_streams.append({
                        'url': u,
                        'content_type': ct,
                        'status': res.status
                    })

                # Buscar APIs de streaming
                if any(api in u.lower() for api in [
                    'dailymotion', 'api', 'json', 'stream', 'player'
                ]):
                    print(f"[API FOUND] {u}")
                    print(f"[CONTENT-TYPE] {ct}")

            except Exception as e:
                print(f"[ERROR] en on_response: {e}")

        page.on("response", on_response)

        try:
            print("[INFO] Navegando a la página...")
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            print("[OK] Página cargada exitosamente")
        except PlaywrightTimeoutError:
            print("[WARN] Timeout de navegación; continúo…")
        except Exception as e:
            print(f"[ERROR] Error al navegar: {e}")
            browser.close()
            return []

        # Buscar elementos de video y sus configuraciones
        try:
            print("[INFO] Buscando elementos de video...")

            # Buscar iframes de Dailymotion u otros players
            iframes = page.locator("iframe").all()
            for i, iframe in enumerate(iframes):
                try:
                    src = iframe.get_attribute("src")
                    if src:
                        print(f"[IFRAME {i+1}] {src}")
                        if "dailymotion" in src.lower():
                            print("[DAILYMOTION] Encontrado iframe de Dailymotion")
                except:
                    pass

            # Buscar elementos video
            videos = page.locator("video").all()
            for i, video in enumerate(videos):
                try:
                    src = video.get_attribute("src")
                    if src:
                        print(f"[VIDEO {i+1}] {src}")
                except:
                    pass

        except Exception as e:
            print(f"[ERROR] al buscar elementos: {e}")

        # Intentar hacer play
        try:
            print("[INFO] Intentando hacer play en el video...")
            page.evaluate("""() => {
                const sels = [
                  'button[aria-label="play"]','button[aria-label="Play"]',
                  "button.play",".vjs-play-control",".jw-icon-play",
                  ".plyr__control[aria-label='Play']","button[title='Play']",
                  "button[aria-label='Reproducir']",".playbtn",".player-play",
                  ".dailymotion-player button", ".play-button", ".start-button"
                ];
                for (const s of sels){
                  const el = document.querySelector(s);
                  if (el){ try{ el.click(); console.log('Clicked:', s); return; }catch(e){} }
                }
                const v = document.querySelector('video');
                if (v){ v.muted = true; v.play().catch(()=>{}); }
            }""")
            print("[OK] Intento de play completado")
        except Exception as e:
            print(f"[ERROR] en intento de play: {e}")

        print(f"[INFO] Esperando {wait_ms}ms para que cargue el stream...")
        page.wait_for_timeout(max(1000, int(wait_ms)))

        # Buscar en el contenido de la página por URLs de streams
        try:
            page_content = page.content()
            import re

            # Buscar URLs que contengan patrones de streaming
            stream_patterns = [
                r'["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*dailymotion[^"\']*)["\']',
                r'["\']([^"\']*video[^"\']*\.mp4[^"\']*)["\']',
                r'["\']([^"\']*stream[^"\']*)["\']',
                r'["\']([^"\']*live[^"\']*)["\']'
            ]

            for pattern in stream_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 10:  # Filtrar URLs muy cortas
                        print(f"[CONTENT MATCH] {match}")
                        found_streams.append({
                            'url': match,
                            'content_type': 'from_content',
                            'status': 'found_in_page'
                        })

        except Exception as e:
            print(f"[ERROR] al buscar en contenido: {e}")

        browser.close()

    return found_streams

def test_stream_accessibility(streams):
    """Probar si los streams encontrados son accesibles"""
    accessible = []

    for stream in streams:
        try:
            url = stream['url']
            print(f"\n[TESTING] {url}")

            headers = {
                'User-Agent': USER_AGENT,
                'Referer': 'https://cdn.com.do/',
                'Origin': 'https://cdn.com.do'
            }

            response = requests.get(url, headers=headers, timeout=10, stream=True)

            if response.status_code == 200:
                content = response.text[:500] if response.text else ""

                # Verificar si es un manifest HLS
                if '#EXTM3U' in content:
                    print(f"[HLS OK] {url}")
                    stream['accessible'] = True
                    stream['content'] = content
                    accessible.append(stream)
                elif 'dailymotion' in url.lower():
                    print(f"[DAILYMOTION] {url}")
                    stream['accessible'] = True
                    accessible.append(stream)
                else:
                    print(f"[OTHER] {url} (status: {response.status_code})")
                    stream['accessible'] = True
                    accessible.append(stream)
            else:
                print(f"[NOT ACCESSIBLE] {url} (status: {response.status_code})")

        except Exception as e:
            print(f"[ERROR] al probar {url}: {e}")

    return accessible

# Main
if __name__ == "__main__":
    print("=== CDN Stream Detector ===")
    page_url = "https://cdn.com.do/envivo/"
    print(f"URL a analizar: {page_url}")

    print("\n[START] Iniciando detección de streams...")
    found_streams = detect_cdn_streams(page_url, HEADLESS, WAIT_MS)

    if not found_streams:
        print("\n[x] No se encontraron streams")
        print("[SUGGESTIONS]:")
        print("  - El stream podría estar protegido")
        print("  - Podría requerir autenticación")
        print("  - Intenta con HEADLESS=True")
        print("  - Verifica si la página requiere cookies")
        sys.exit(1)

    print(f"\n[OK] Se encontraron {len(found_streams)} streams potenciales:")
    for i, stream in enumerate(found_streams, 1):
        print(f"  {i}. {stream['url']}")
        print(f"     Content-Type: {stream.get('content_type', 'unknown')}")
        print(f"     Status: {stream.get('status', 'unknown')}")

    print("\n[TEST] Probando accesibilidad de los streams...")
    accessible_streams = test_stream_accessibility(found_streams)

    if accessible_streams:
        print(f"\n[OK] {len(accessible_streams)} streams accesibles:")
        for i, stream in enumerate(accessible_streams, 1):
            print(f"  {i}. {stream['url']}")
            if 'content' in stream:
                print(f"     Tipo: HLS Manifest")
            elif 'dailymotion' in stream['url'].lower():
                print(f"     Tipo: Dailymotion Player")
            else:
                print(f"     Tipo: Video Stream")
    else:
        print("\n[!] Ningún stream es directamente accesible")
        print("Esto podría indicar que:")
        print("  - Requiere autenticación")
        print("  - Usa protección DRM")
        print("  - Necesita headers específicos")
        print("  - Es un stream privado")

    print("\n[FIN] Análisis completado")
