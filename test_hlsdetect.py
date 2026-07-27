import os
import sys
import time
import shlex
import threading
import subprocess
from urllib.parse import urlparse, parse_qs, unquote, quote

import requests
from flask import Flask, request, Response, abort
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================ Config =================
HEADLESS = False
WAIT_MS  = 9000
GRAB_DIR = "grab"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

# ================ Utils ==================
def ensure_grab_dir() -> str:
    os.makedirs(GRAB_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    return os.path.join(GRAB_DIR, f"grabacion-{ts}.mp4")

def is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except:
        return False

def guess_ref_origin_from_query(m3u8_url: str):
    ref = ""
    org = ""
    try:
        qs = parse_qs(urlparse(m3u8_url).query)
        if "eb" in qs and qs["eb"]:
            ref = unquote(qs["eb"][0])
        if not ref and "td" in qs and qs["td"]:
            td = qs["td"][0]
            if td and "." in td:
                ref = f"https://{td}/"
        if ref:
            org = ref.rstrip("/")
    except:
        pass
    return ref, org

def make_headers(user_agent: str, referer: str, origin: str, cookies: str):
    h = {"User-Agent": user_agent, "Accept": "*/*"}
    if referer: h["Referer"] = referer
    if origin:  h["Origin"]  = origin
    if cookies: h["Cookie"]  = cookies
    return h

def probe_manifest(url: str, headers: dict, label: str):
    print(f"\n[PROBE:{label}] GET {url}")
    try:
        r = requests.get(url, headers=headers, timeout=12)
        ct = (r.headers.get("content-type") or "").lower()
        head = (r.text or "")[:240].replace("\n", "⏎")
        print(f"[PROBE:{label}] status={r.status_code} ct={ct}")
        print(f"[PROBE:{label}] head: {head}")
        ok = r.ok and (r.text.lstrip().startswith("#EXTM3U") or "mpegurl" in ct)
        return ok, r.status_code, ct
    except Exception as e:
        print(f"[PROBE:{label}] error: {e}")
        return False, -1, ""

# =========== Proxy (inyecta Referer/Origin) ===========
def start_proxy(referer: str, origin: str, user_agent: str):
    app = Flask(__name__)
    BASE_HEADERS = make_headers(user_agent, referer, origin, cookies="")

    @app.route("/proxy")
    def proxy():
        raw = request.args.get("u", "")
        if not raw: return abort(400, "missing u")
        u = unquote(raw)
        p = urlparse(u)
        if p.scheme not in ("http", "https") or not p.netloc:
            return abort(400, "bad url")
        try:
            rr = requests.get(u, headers=BASE_HEADERS, stream=True, timeout=15)
        except Exception as e:
            return abort(502, f"upstream error: {e}")
        ct = rr.headers.get("Content-Type", "application/octet-stream")
        def generate():
            for chunk in rr.iter_content(chunk_size=64*1024):
                if chunk: yield chunk
        resp = Response(generate(), status=rr.status_code, mimetype=ct)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        for h in ("Cache-Control", "Expires", "Pragma"):
            if h in rr.headers: resp.headers[h] = rr.headers[h]
        return resp

    th = threading.Thread(target=lambda: app.run("127.0.0.1", 5001, debug=False, use_reloader=False))
    th.daemon = True
    th.start()
    time.sleep(0.4)
    print("[i] Proxy on http://127.0.0.1:5001/proxy?u=<url_enc>")
    return th

# ============== Playwright (Chrome) ==============
def detect_first_m3u8(page_url: str, headless: bool, wait_ms: int):
    print(f"[INFO] Abriendo con Chrome (channel='chrome'): {page_url}")
    found = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=headless, channel="chrome")
        except Exception as e:
            raise RuntimeError("No pude lanzar Google Chrome con Playwright: " + str(e))
        context = browser.new_context()
        page = context.new_page()

        def on_response(res):
            try:
                u = res.url
                ct = (res.headers or {}).get("content-type", "").lower()
                if ".m3u8" in u or "mpegurl" in ct:
                    found.append(u)
            except:
                pass

        page.on("response", on_response)

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print("[WARN] Timeout de navegación; continúo…")
        except Exception as e:
            browser.close()
            raise RuntimeError(f"Error al navegar: {e}")

        # intentos de play
        try:
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
        except:
            pass

        page.wait_for_timeout(max(1000, int(wait_ms)))
        browser.close()

    # primera única
    seen = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            return u
    return None

# ============== Main ==============
if __name__ == "__main__":
    print("=== Auto Detect + Probe + Proxy fallback + Record ===")
    page_url = "https://cdn.com.do/envivo/"  # URL específica para probar
    print(f"URL de la PÁGINA con el player: {page_url}")

    if not is_http_url(page_url):
        print("[x] URL inválida.")
        sys.exit(1)

    # 1) Detectar
    m3u8 = detect_first_m3u8(page_url, HEADLESS, WAIT_MS)
    if not m3u8:
        print("[x] No se detectó ninguna .m3u8. Prueba HEADLESS=False y aumenta WAIT_MS.")
        sys.exit(1)
    print(f"\n[OK] Detectada .m3u8:\n{m3u8}")

    # 2) Referer/Origin sugeridos por la propia URL
    ref_guess, org_guess = guess_ref_origin_from_query(m3u8)
    referer = ref_guess
    origin  = org_guess
    if referer: print(f"[INFO] Referer sugerido: {referer}")
    if origin:  print(f"[INFO] Origin  sugerido: {origin}")

    # 3) Probe directo
    headers = make_headers(USER_AGENT, referer, origin, cookies="")
    ok, st, ct = probe_manifest(m3u8, headers, label="direct")
    cookies = ""

    # 4) Si no es válido, pedir cookies y reintentar
    if not ok:
        print("\n[?] Manifest inválido/403. ¿Pegar cookies del navegador? (y/N) ")
        ans = "n"  # Simulamos respuesta negativa para prueba automática
        if ans == "y":
            cookies = input("Pega aquí el valor del header Cookie: ").strip()
            headers = make_headers(USER_AGENT, referer, origin, cookies)
            ok, st, ct = probe_manifest(m3u8, headers, label="direct+cookies")

    # 5) Si aún inválido, iniciar proxy y reintentar vía proxy
    proxy_thread = None
    proxied_url = m3u8
    if not ok:
        print("\n[i] Iniciando proxy con Referer/Origin para reintentar…")
        proxy_thread = start_proxy(referer, origin, USER_AGENT)
        enc = quote(m3u8, safe="")
        proxied_url = f"http://127.0.0.1:5001/proxy?u={enc}"
        ok, st, ct = probe_manifest(proxied_url, make_headers(USER_AGENT, "", "", ""), label="proxy")

    if not ok:
        print("\n[x] No se pudo validar el manifest. Causas típicas: URL expirada, headers/cookies insuficientes o DRM.")
        sys.exit(1)

    # 6) Grabar
    out_path = ensure_grab_dir()
    # Si vamos por proxy, ya no hace falta pasar Referer/Origin a FFmpeg (el proxy los pone). Cookies igual no se usan en el proxy.
    if proxied_url.startswith("http://127.0.0.1:5001/"):
        record_ffmpeg(proxied_url, out_path, USER_AGENT, "", "", "")
    else:
        record_ffmpeg(m3u8, out_path, USER_AGENT, referer, origin, cookies)

    print("\n[FIN] Revisa tu carpeta ./grab/")
