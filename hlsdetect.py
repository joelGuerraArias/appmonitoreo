# -*- coding: utf-8 -*-
# Ejecuta:  python m3u8_desde_extension_sin_cerrar_chrome.py

import asyncio
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from playwright.async_api import async_playwright, BrowserContext

# ========= CONFIG =========
TARGET_URL    = "https://cdn.com.do/envivo/"
# ruta del perfil de Chrome donde está instalada tu extensión
CHROME_USER_DATA = Path(r"C:\Users\Administrador\AppData\Local\Google\Chrome\User Data")
OUT_FILE      = Path(r"C:\Users\Administrador\Desktop\grabaciones\streams")  # o ...\streams.txt
M3U8_PRIORITY = ["1080", "720", "master", "480"]  # orden preferido
# Si sabes la carpeta exacta de la extensión "desempaquetada", ponla aquí y se usará directo:
MANUAL_EXTENSION_DIR: Optional[Path] = None  # ej: Path(r"C:\ruta\a\mi_extension_unpacked")

# Palabras clave para detectar tu extensión automáticamente en el perfil de Chrome
EXT_NAME_KEYWORDS = ["hls", "stream", "m3u8", "detector", "sniffer", "downloader"]


# ========= HELPERS =========
def upsert_line(file_path: Path, key: str, value: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    lines = existing.splitlines()
    prefix = f"{key}: "
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{prefix}{value}"
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    if existing and not existing.endswith("\n"):
        existing += "\n"
    file_path.write_text(existing + f"{prefix}{value}\n", encoding="utf-8")


def pick_best_m3u8(urls: List[str]) -> Optional[str]:
    if not urls:
        return None
    for key in M3U8_PRIORITY:
        for u in urls:
            if key in u:
                return u
    return urls[0]


def find_extensions_dirs(base: Path) -> List[Path]:
    """Busca directorios tipo ...\Default\Extensions\<id>\<version>\manifest.json"""
    hits = []
    for profile in ["Default"] + [p.name for p in base.glob("*") if p.is_dir() and p.name.startswith("Profile")]:
        ext_root = base / profile / "Extensions"
        if not ext_root.exists():
            continue
        for ext_id_dir in ext_root.iterdir():
            if not ext_id_dir.is_dir():
                continue
            # elige la versión más alta
            versions = [d for d in ext_id_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()]
            if not versions:
                continue
            best_ver = sorted(versions, key=lambda p: p.name, reverse=True)[0]
            hits.append(best_ver)
    return hits


def pick_sniffer_extension_dir(ext_dirs: List[Path]) -> Optional[Path]:
    """Elige una extensión cuyo manifest contenga keywords (HLS/M3U8/Stream...)."""
    for d in ext_dirs:
        try:
            man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            name = (man.get("name", "") + " " + man.get("description", "")).lower()
            if any(k in name for k in EXT_NAME_KEYWORDS):
                return d
        except Exception:
            continue
    return None


def copy_unpacked_extension(src: Path) -> Path:
    tmp = Path.cwd() / "_ext_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp)
    return tmp


async def get_loaded_extension_id(ctx: BrowserContext) -> Optional[str]:
    # MV3 service worker
    for _ in range(10):
        for w in ctx.service_workers:
            u = w.url
            if u.startswith("chrome-extension://"):
                return u.split("/")[2]
        for bg in ctx.background_pages:
            u = bg.url
            if u.startswith("chrome-extension://"):
                return u.split("/")[2]
        await asyncio.sleep(0.5)
    return None


async def popup_url_from_manifest(ctx: BrowserContext, ext_id: str) -> Optional[str]:
    try:
        res = await ctx.request.get(f"chrome-extension://{ext_id}/manifest.json")
        man = await res.json()
        action = man.get("action") or man.get("browser_action") or {}
        popup = (action.get("default_popup") or "").lstrip("/")
        return f"chrome-extension://{ext_id}/{popup}" if popup else None
    except Exception:
        return None


async def read_m3u8_from_popup(popup_page) -> List[str]:
    try:
        await popup_page.get_by_text("Current tab", exact=False).click(timeout=800)
    except Exception:
        pass
    await popup_page.wait_for_load_state("domcontentloaded")
    await popup_page.wait_for_timeout(800)

    links = await popup_page.eval_on_selector_all(
        "a", "els => els.map(a => a.href).filter(u => u && u.includes('.m3u8'))"
    )
    if links:
        return links

    raw = await popup_page.evaluate("document.body.innerText")
    return re.findall(r"https?://[^\s\"'<>]+?\.m3u8\b", raw)


# ========= MAIN =========
async def main():
    # 1) Resolver carpeta de extensión
    ext_dir = MANUAL_EXTENSION_DIR
    if not ext_dir:
        installed = find_extensions_dirs(CHROME_USER_DATA)
        ext_dir = pick_sniffer_extension_dir(installed)
    if not ext_dir:
        print("⚠️ No pude localizar automáticamente la extensión. "
              "Si sabes la ruta 'desempaquetada', ponla en MANUAL_EXTENSION_DIR.")
        return

    unpacked = copy_unpacked_extension(ext_dir)

    # 2) Levantar Chromium con esa extensión (no toca tus ventanas de Chrome)
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=Path.cwd() / "_pw_profile",
            headless=False,
            args=[
                f"--disable-extensions-except={unpacked}",
                f"--load-extension={unpacked}",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )

        # 3) Ir a la página del stream
        page = await ctx.new_page()
        await page.goto(TARGET_URL, wait_until="domcontentloaded")
        try:
            await page.evaluate("""
                () => {
                    const v = document.querySelector('video');
                    if (v) { v.muted = true; v.play?.().catch(()=>{}); }
                    document.documentElement.click();
                }
            """)
        except Exception:
            pass

        # 4) Obtener el ID que tomó la extensión en este Chromium y abrir su popup
        ext_id = await get_loaded_extension_id(ctx)
        if not ext_id:
            print("⚠️ No se cargó ninguna extensión en el contexto de Playwright.")
            await ctx.close()
            return

        popup_url = await popup_url_from_manifest(ctx, ext_id)
        if not popup_url:
            print("⚠️ La extensión no define default_popup en manifest.json.")
            await ctx.close()
            return

        popup = await ctx.new_page()
        await popup.goto(popup_url, wait_until="domcontentloaded")

        # 5) Tomar las URLs .m3u8 del popup
        urls = await read_m3u8_from_popup(popup)
        await popup.close()

        if not urls:
            print("⚠️ No se encontraron .m3u8 en el popup de la extensión.")
            await ctx.close()
            return

        best = pick_best_m3u8(urls)
        upsert_line(OUT_FILE, "URL detectada", best)
        upsert_line(OUT_FILE, "Última actualización", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        print("✅ Actualizado:", OUT_FILE)
        print("→", best)

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
