import os
import sys
import time
from urllib.parse import urlparse, parse_qs, unquote, quote
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración simplificada para debug
HEADLESS = False
WAIT_MS = 9000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

def is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except:
        return False

def detect_first_m3u8(page_url: str, headless: bool, wait_ms: int):
    print(f"[INFO] Abriendo con Chrome: {page_url}")
    found = []

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=headless, channel="chrome")
            print("[OK] Chrome lanzado exitosamente")
        except Exception as e:
            print(f"[ERROR] No pude lanzar Chrome: {e}")
            return None

        context = browser.new_context()
        page = context.new_page()

        def on_response(res):
            try:
                u = res.url
                ct = (res.headers or {}).get("content-type", "").lower()
                print(f"[RESPONSE] URL: {u}")
                print(f"[RESPONSE] Content-Type: {ct}")

                if ".m3u8" in u or "mpegurl" in ct:
                    print(f"[M3U8 FOUND] {u}")
                    found.append(u)
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
            return None

        # Intentar hacer play
        try:
            print("[INFO] Intentando hacer play en el video...")
            page.evaluate("""() => {
                const sels = [
                  'button[aria-label="play"]','button[aria-label="Play"]',
                  "button.play",".vjs-play-control",".jw-icon-play",
                  ".plyr__control[aria-label='Play']","button[title='Play']",
                  "button[aria-label='Reproducir']",".playbtn",".player-play",
                ];
                for (const s of sels){
                  const el = document.querySelector(s);
                  if (el){ try{ el.click(); return; }catch(e){} }
                }
                const v = document.querySelector('video');
                if (v){ v.muted = true; v.play().catch(()=>{}); }
            }""")
            print("[OK] Intento de play completado")
        except Exception as e:
            print(f"[ERROR] en intento de play: {e}")

        print(f"[INFO] Esperando {wait_ms}ms para que cargue el stream...")
        page.wait_for_timeout(max(1000, int(wait_ms)))
        browser.close()

    # Mostrar todas las URLs encontradas
    print(f"\n[SUMMARY] Se encontraron {len(found)} URLs potenciales:")
    for i, url in enumerate(found, 1):
        print(f"  {i}. {url}")

    # Primera única
    seen = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            return u
    return None

# Main
if __name__ == "__main__":
    print("=== DEBUG HLS Detect ===")
    page_url = "https://cdn.com.do/envivo/"
    print(f"URL a probar: {page_url}")

    if not is_http_url(page_url):
        print("[x] URL inválida.")
        sys.exit(1)

    print("\n[START] Iniciando detección de stream HLS...")
    m3u8 = detect_first_m3u8(page_url, HEADLESS, WAIT_MS)

    if not m3u8:
        print("\n[x] No se detectó ninguna URL .m3u8")
        print("[SUGGESTIONS]:")
        print("  - La página podría no tener un stream HLS activo")
        print("  - El stream podría estar protegido o requerir autenticación")
        print("  - Intenta con HEADLESS=True si hay problemas de rendering")
        print("  - Aumenta WAIT_MS si el stream tarda en cargar")
        sys.exit(1)

    print(f"\n[OK] Stream HLS detectado: {m3u8}")

    # Probar si la URL es accesible
    try:
        print(f"\n[TEST] Probando acceso directo a: {m3u8}")
        r = requests.get(m3u8, headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.ok and r.text.lstrip().startswith("#EXTM3U"):
            print("[OK] Stream HLS accesible y válido")
        else:
            print(f"[WARN] Stream HLS no accesible directamente (status: {r.status_code})")
    except Exception as e:
        print(f"[ERROR] No se pudo acceder al stream: {e}")

    print("\n[FIN] Debug completado")
