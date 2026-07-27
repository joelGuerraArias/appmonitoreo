import os
import sys
import time
import json
import requests
import re
import shlex
import subprocess
import threading
from urllib.parse import urlparse, parse_qs, unquote, quote
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración para simular la extensión Stream Detector
HEADLESS = False
WAIT_MS = 20000  # Tiempo extendido para que cargue todo
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

def detect_hls_streams(page_url: str, headless: bool, wait_ms: int):
    """
    Simula el comportamiento de la extensión Stream Detector
    Detecta todos los streams HLS disponibles en la página
    """
    print(f"[INFO] 🔍 Analizando: {page_url}")
    found_streams = []

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=headless, channel="chrome")
            print("[OK] ✅ Chrome lanzado exitosamente")
        except Exception as e:
            print(f"[ERROR] ❌ No pude lanzar Chrome: {e}")
            return []

        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # Interceptar todas las respuestas de red
        def on_response(res):
            try:
                u = res.url
                ct = (res.headers or {}).get("content-type", "").lower()

                # Detectar streams HLS por URL
                if any(pattern in u.lower() for pattern in [
                    ".m3u8", "mpegurl", "live", "stream", "hls", "playlist"
                ]):
                    print(f"[STREAM] 📺 {u}")
                    print(f"[TYPE] {ct}")

                    found_streams.append({
                        'url': u,
                        'content_type': ct,
                        'status': res.status,
                        'source': 'network_request',
                        'timestamp': time.strftime("%m/%d/%Y %I:%M:%S %p")
                    })

                # Detectar por content-type
                if 'mpegurl' in ct or 'hls' in ct:
                    print(f"[HLS DETECTED] 🎯 {u}")
                    found_streams.append({
                        'url': u,
                        'content_type': ct,
                        'status': res.status,
                        'source': 'content_type',
                        'timestamp': time.strftime("%m/%d/%Y %I:%M:%S %p")
                    })

            except Exception as e:
                print(f"[ERROR] en on_response: {e}")

        page.on("response", on_response)

        try:
            print("[INFO] 🌐 Navegando a la página...")
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            print("[OK] ✅ Página cargada exitosamente")
        except PlaywrightTimeoutError:
            print("[WARN] ⚠️ Timeout de navegación; continúo…")
        except Exception as e:
            print(f"[ERROR] ❌ Error al navegar: {e}")
            browser.close()
            return []

        # Buscar elementos de video y hacer click en play
        try:
            print("[INFO] 🎬 Buscando elementos de video...")

            # Buscar iframes de Dailymotion u otros players
            iframes = page.locator("iframe").all()
            for i, iframe in enumerate(iframes):
                try:
                    src = iframe.get_attribute("src")
                    if src:
                        print(f"[IFRAME {i+1}] {src}")
                        if "dailymotion" in src.lower():
                            print("[DAILYMOTION] 🎬 Encontrado iframe de Dailymotion")
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

        # Intentar hacer play en todos los elementos posibles
        try:
            print("[INFO] ▶️ Intentando hacer play en el video...")

            # Selectores para diferentes tipos de players
            play_selectors = [
                'button[aria-label="play"]',
                'button[aria-label="Play"]',
                "button.play",
                ".vjs-play-control",
                ".jw-icon-play",
                ".plyr__control[aria-label='Play']",
                "button[title='Play']",
                "button[aria-label='Reproducir']",
                ".playbtn",
                ".player-play",
                ".dailymotion-player button",
                ".play-button",
                ".start-button",
                ".video-play",
                ".jw-play",
                ".vjs-big-play-button",
                ".play-icon",
                ".play-overlay",
                ".video-player-play"
            ]

            for selector in play_selectors:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        print(f"[PLAY] 🎯 Encontrado selector: {selector} ({len(elements)} elementos)")
                        for el in elements:
                            try:
                                el.click(timeout=1000)
                                print(f"[CLICK] ✅ Click en: {selector}")
                            except:
                                pass
                except:
                    pass

            # Intentar play en elementos video directamente
            try:
                page.evaluate("""() => {
                    const videos = document.querySelectorAll('video');
                    videos.forEach(v => {
                        v.muted = true;
                        v.play().catch(e => console.log('Play error:', e));
                    });
                }""")
                print("[PLAY] ▶️ Intento de play en videos completado")
            except Exception as e:
                print(f"[ERROR] en intento de play: {e}")

        except Exception as e:
            print(f"[ERROR] en intento de play: {e}")

        print(f"[INFO] ⏳ Esperando {wait_ms}ms para que carguen los streams...")
        page.wait_for_timeout(max(1000, int(wait_ms)))

        # Buscar en el contenido de la página por URLs de streams
        try:
            page_content = page.content()
            print(f"[INFO] 📄 Analizando contenido de la página ({len(page_content)} caracteres)")

            # Patrones para encontrar streams HLS en el HTML
            stream_patterns = [
                r'["\']([^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*live[^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*stream[^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*hls[^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*playlist[^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*video[^"\']*\.m3u8[^"\']*)["\']',
                r'["\']([^"\']*x[0-9a-zA-Z]{6}\.m3u8[^"\']*)["\']'
            ]

            for pattern in stream_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    if match and len(match) > 10 and match not in [s['url'] for s in found_streams]:
                        print(f"[CONTENT MATCH] 📋 {match}")
                        found_streams.append({
                            'url': match,
                            'content_type': 'from_content',
                            'status': 'found_in_page',
                            'source': 'page_content',
                            'timestamp': time.strftime("%m/%d/%Y %I:%M:%S %p")
                        })

        except Exception as e:
            print(f"[ERROR] al buscar en contenido: {e}")

        browser.close()

    return found_streams

def test_stream_accessibility(streams):
    """Probar si los streams encontrados son accesibles"""
    accessible = []
    headers = {
        'User-Agent': USER_AGENT,
        'Referer': 'https://cdn.com.do/',
        'Origin': 'https://cdn.com.do'
    }

    for stream in streams:
        try:
            url = stream['url']
            print(f"\n[TESTING] 🔍 {url}")

            response = requests.get(url, headers=headers, timeout=10, stream=True)

            if response.status_code == 200:
                content = response.text[:1000] if response.text else ""

                # Verificar si es un manifest HLS válido
                if '#EXTM3U' in content:
                    print(f"[HLS OK] ✅ {url}")
                    stream['accessible'] = True
                    stream['content'] = content
                    accessible.append(stream)
                elif any(ext in url.lower() for ext in ['.m3u8', 'live', 'stream', 'hls']):
                    print(f"[STREAM OK] 📺 {url} (status: {response.status_code})")
                    stream['accessible'] = True
                    accessible.append(stream)
                else:
                    print(f"[OTHER] ❓ {url} (status: {response.status_code})")
            else:
                print(f"[NOT ACCESSIBLE] ❌ {url} (status: {response.status_code})")

        except Exception as e:
            print(f"[ERROR] al probar {url}: {e}")

    return accessible

def main():
    print("=== 🔍 Stream Detector Extension Simulator ===")
    page_url = "https://cdn.com.do/envivo/"
    print(f"🎯 URL a analizar: {page_url}")

    print("\n[START] 🚀 Iniciando detección de streams HLS...")
    found_streams = detect_hls_streams(page_url, HEADLESS, WAIT_MS)

    if not found_streams:
        print("\n❌ No se encontraron streams")
        print("💡 Posibles causas:")
        print("   - El stream podría estar protegido")
        print("   - Podría requerir autenticación")
        print("   - Intenta con HEADLESS=True")
        print("   - Verifica si la página requiere cookies")
        sys.exit(1)

    print(f"\n✅ Se encontraron {len(found_streams)} streams potenciales:")
    for i, stream in enumerate(found_streams, 1):
        print(f"  {i}. {stream['url']}")
        print(f"     📄 Content-Type: {stream.get('content_type', 'unknown')}")
        print(f"     🔗 Source: {stream.get('source', 'unknown')}")
        print(f"     🕒 Timestamp: {stream.get('timestamp', 'unknown')}")

    print("\n[TEST] 🔍 Probando accesibilidad de los streams...")
    accessible_streams = test_stream_accessibility(found_streams)

    if accessible_streams:
        print(f"\n🎉 {len(accessible_streams)} streams accesibles encontrados:")
        print("\n" + "="*80)
        print("📋 RESULTADOS FINALES:")
        print("="*80)

        for i, stream in enumerate(accessible_streams, 1):
            print(f"\n{i}. 🎯 STREAM HLS ENCONTRADO:")
            print(f"   📺 URL: {stream['url']}")
            print(f"   🔍 Source: {stream.get('source', 'unknown')}")
            print(f"   🕒 Timestamp: {stream.get('timestamp', 'unknown')}")

            if 'content' in stream:
                print("   ✅ Tipo: HLS Manifest válido")
            else:
                print("   📺 Tipo: Stream URL")

            # Si es el primer stream válido, lo destacamos
            if i == 1:
                print("   🥇 PRIMERA OPCIÓN VÁLIDA (recomendada)")
                print(f"\n💾 COPIA ESTA URL: {stream['url']}")

        print("\n" + "="*80)
        print("✅ ¡TAREA COMPLETADA!")
        print(f"🎯 Primer stream válido: {accessible_streams[0]['url']}")
        print("="*80)

        # 🎬 GRABAR EL PRIMER STREAM ENCONTRADO
        print("\n🎥 INICIANDO GRABACIÓN AUTOMÁTICA...")
        print(f"📺 Stream a grabar: {accessible_streams[0]['url']}")

        # Crear directorio grab si no existe
        out_path = ensure_grab_dir()
        print(f"📁 Archivo de salida: {out_path}")

        # Grabar el stream
        success = record_stream_ffmpeg(
            accessible_streams[0]['url'],
            out_path,
            USER_AGENT,
            "https://cdn.com.do/",
            "https://cdn.com.do",
            ""
        )

        if success:
            print("\n🎉 ¡GRABACIÓN COMPLETADA EXITOSAMENTE!")
            print(f"📂 Revisa tu carpeta: ./grab/")
        else:
            print("\n❌ Error en la grabación")
            print("💡 El stream podría haber expirado o requerir autenticación especial")

    else:
        print("\n❌ Ningún stream es directamente accesible")
        print("💡 Esto podría indicar que:")
        print("   - Requiere autenticación")
        print("   - Usa protección DRM")
        print("   - Necesita headers específicos")
        print("   - Es un stream privado")

    print("\n🏁 Análisis completado")

if __name__ == "__main__":
    main()
