# -*- coding: utf-8 -*-
"""
Worker headless para la UI Next.js (app-monitoreo-next).

Reutiliza el pipeline de appMonitoreo.py (buscar_y_procesar_videos) sin abrir Streamlit.
No modifica la lógica de envíos; solo la invoca en CLI.

Uso:
  venv_new\\Scripts\\python.exe worker_next_monitoreo.py once
  venv_new\\Scripts\\python.exe worker_next_monitoreo.py loop
  venv_new\\Scripts\\python.exe worker_next_monitoreo.py status
"""
from __future__ import annotations

import argparse
import atexit
import importlib
import json
import os
import sys
import time
import traceback
import types
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Desactivar auto-escaneo Streamlit al importar el módulo
os.environ["AUTO_ESCANEO_ENABLED"] = "false"
os.environ["VA_HEADLESS"] = "1"

STATUS_DIR = ROOT / "videos procesados"
STATUS_PATH = STATUS_DIR / "next_worker_status.json"
STOP_PATH = STATUS_DIR / "next_worker_stop.flag"
PID_PATH = STATUS_DIR / "next_worker.pid"
LOG_PATH = ROOT / "logs" / "next_worker.log"


class _SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(key) from e

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as e:
            raise AttributeError(key) from e


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __getattr__(self, name):
        return _noop

    def metric(self, *a, **k):
        return None

    def button(self, *a, **k):
        return False

    def checkbox(self, *a, **k):
        return k.get("value", False)

    def text_input(self, *a, **k):
        return k.get("value", "")

    def number_input(self, *a, **k):
        return k.get("value", 0)

    def selectbox(self, *a, **k):
        opts = k.get("options") or (a[1] if len(a) > 1 else [])
        idx = k.get("index", 0)
        return opts[idx] if opts else None

    def markdown(self, *a, **k):
        return None

    def write(self, *a, **k):
        return None

    def info(self, *a, **k):
        return None

    def success(self, *a, **k):
        return None

    def warning(self, *a, **k):
        return None

    def error(self, *a, **k):
        return None

    def caption(self, *a, **k):
        return None

    def code(self, *a, **k):
        return None

    def empty(self):
        return self

    def container(self):
        return _Ctx()

    def expander(self, *a, **k):
        return _Ctx()

    def columns(self, n, *a, **k):
        count = n if isinstance(n, int) else len(n)
        return [_Ctx() for _ in range(count)]


def _noop(*a, **k):
    return None


def _false(*a, **k):
    return False


def _empty(*a, **k):
    return _Ctx()


def _install_streamlit_shim():
    """Mock mínimo para poder importar appMonitoreo fuera de Streamlit."""
    st = types.ModuleType("streamlit")
    state = _SessionState()
    st.session_state = state
    st.set_page_config = _noop

    def _cache_decorator(f=None, **_k):
        def _wrap(fn):
            return fn

        _wrap.clear = _noop  # type: ignore[attr-defined]
        if f is not None and callable(f):
            return f
        return _wrap

    st.cache_resource = _cache_decorator
    st.cache_data = _cache_decorator
    st.cache_resource.clear = _noop  # type: ignore[attr-defined]
    st.cache_data.clear = _noop  # type: ignore[attr-defined]
    st.rerun = _noop
    st.stop = _noop
    st.markdown = _noop
    st.write = _noop
    st.text = _noop
    st.title = _noop
    st.header = _noop
    st.subheader = _noop
    st.caption = _noop
    st.code = _noop
    st.json = _noop
    st.info = lambda *a, **k: _log(f"INFO: {a[0] if a else ''}")
    st.success = lambda *a, **k: _log(f"OK: {a[0] if a else ''}")
    st.warning = lambda *a, **k: _log(f"WARN: {a[0] if a else ''}")
    st.error = lambda *a, **k: _log(f"ERR: {a[0] if a else ''}")
    st.exception = lambda e: _log(f"EXC: {e}")
    st.button = _false
    st.checkbox = lambda *a, **k: k.get("value", False)
    st.toggle = lambda *a, **k: k.get("value", False)
    st.text_input = lambda *a, **k: k.get("value", "") or ""
    st.text_area = lambda *a, **k: k.get("value", "") or ""
    st.number_input = lambda *a, **k: k.get("value", 0)
    st.selectbox = lambda *a, **k: (k.get("options") or [None])[k.get("index", 0)]
    st.multiselect = lambda *a, **k: k.get("default") or []
    st.radio = lambda *a, **k: (k.get("options") or [None])[0]
    st.slider = lambda *a, **k: k.get("value", 0)
    st.file_uploader = lambda *a, **k: None
    st.download_button = _false
    st.metric = _noop
    st.progress = lambda *a, **k: _Ctx()
    st.spinner = lambda *a, **k: _Ctx()
    st.empty = _empty
    st.container = lambda *a, **k: _Ctx()
    st.expander = lambda *a, **k: _Ctx()
    st.columns = lambda n, *a, **k: [_Ctx() for _ in range(n if isinstance(n, int) else len(n))]
    st.tabs = lambda labels, *a, **k: [_Ctx() for _ in labels]
    st.sidebar = _Ctx()
    st.dataframe = _noop
    st.table = _noop
    st.image = _noop
    st.video = _noop
    st.audio = _noop
    st.plotly_chart = _noop
    st.pyplot = _noop
    st.balloons = _noop
    st.snow = _noop
    st.toast = _noop
    st.form = lambda *a, **k: _Ctx()
    st.form_submit_button = _false
    st.divider = _noop
    st.html = _noop

    components = types.ModuleType("streamlit.components")
    v1 = types.ModuleType("streamlit.components.v1")
    v1.html = _noop
    v1.iframe = _noop
    components.v1 = v1
    st.components = components

    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = v1
    return st


_log_buffer: list[str] = []


def _log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line, flush=True)
    _log_buffer.append(line)
    if len(_log_buffer) > 200:
        del _log_buffer[:-200]
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _write_status(payload: dict) -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        **payload,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "logs": _log_buffer[-40:],
    }
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS_PATH)


def _read_status() -> dict:
    if not STATUS_PATH.exists():
        return {"running": False, "phase": "idle", "message": "Sin worker"}
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"running": False, "phase": "error", "message": str(e)}


def _clear_stop_flag() -> None:
    try:
        if STOP_PATH.exists():
            STOP_PATH.unlink()
    except OSError:
        pass


def _should_stop() -> bool:
    return STOP_PATH.exists()


def _write_pid() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")


def _clear_pid() -> None:
    try:
        if PID_PATH.exists():
            PID_PATH.unlink()
    except OSError:
        pass


def _load_app():
    _install_streamlit_shim()
    _log("Importando appMonitoreo (headless)…")
    # Evitar que el bloque continuo del import procese videos
    import streamlit as st  # type: ignore  # shim

    # Import puede tardar (modelos / deps)
    app = importlib.import_module("appMonitoreo")
    st.session_state.running = False
    st.session_state.auto_escaneo_enabled = False
    st.session_state.procesamiento_en_curso = False
    _log("appMonitoreo listo")
    return app, st


def _snapshot_session(st) -> dict:
    return {
        "videos_encontrados": int(st.session_state.get("videos_encontrados") or 0),
        "videos_procesados": int(st.session_state.get("videos_procesados") or 0),
        "clips_generados": int(st.session_state.get("clips_generados") or 0),
        "loop_ciclo_numero": int(st.session_state.get("loop_ciclo_numero") or 0),
        "mistral_total_transcripciones": int(
            st.session_state.get("mistral_total_transcripciones") or 0
        ),
        "mistral_total_audio_seconds": float(
            st.session_state.get("mistral_total_audio_seconds") or 0
        ),
        "mistral_total_tokens": int(st.session_state.get("mistral_total_tokens") or 0),
        "alertas_envio": list(st.session_state.get("alertas_envio_ui") or [])[-10:],
        "terminos": len(st.session_state.get("terminos_continuos") or []),
    }


def run_cycle(app, st, *, once: bool) -> None:
    duracion = int(st.session_state.get("duracion_clip") or 90)
    buffer = int(st.session_state.get("buffer_anterior") or 30)
    # El worker gestiona el loop; apagar el loop interno de Streamlit (evita sleep/rerun).
    st.session_state.loop_continuo = False
    _write_status(
        {
            "running": True,
            "phase": "processing",
            "mode": "once" if once else "loop",
            "message": "Ejecutando buscar_y_procesar_videos…",
            "pid": os.getpid(),
            **_snapshot_session(st),
        }
    )
    _log(f"Ciclo: duracion_clip={duracion}s buffer={buffer}s")
    try:
        app.buscar_y_procesar_videos(duracion, buffer)
        st.session_state.loop_ciclo_numero = int(
            st.session_state.get("loop_ciclo_numero") or 0
        ) + 1
        _log(
            f"Ciclo OK — videos_proc={st.session_state.get('videos_procesados')} "
            f"clips={st.session_state.get('clips_generados')}"
        )
        _write_status(
            {
                "running": not once,
                "phase": "idle_wait" if not once else "done",
                "mode": "once" if once else "loop",
                "message": "Ciclo completado",
                "pid": os.getpid(),
                **_snapshot_session(st),
            }
        )
    except Exception as e:
        _log(f"Error en ciclo: {e}")
        _log(traceback.format_exc())
        _write_status(
            {
                "running": not once and not _should_stop(),
                "phase": "error",
                "mode": "once" if once else "loop",
                "message": f"Error: {e}",
                "pid": os.getpid(),
                **_snapshot_session(st),
            }
        )


def cmd_once() -> int:
    _clear_stop_flag()
    _write_pid()
    atexit.register(_clear_pid)
    app, st = _load_app()
    run_cycle(app, st, once=True)
    _write_status(
        {
            "running": False,
            "phase": "done",
            "mode": "once",
            "message": "Proceso único finalizado",
            "pid": None,
            **_snapshot_session(st),
        }
    )
    _clear_pid()
    return 0


def cmd_loop() -> int:
    _clear_stop_flag()
    _write_pid()
    atexit.register(_clear_pid)
    app, st = _load_app()
    st.session_state.loop_continuo = True
    _write_status(
        {
            "running": True,
            "phase": "starting",
            "mode": "loop",
            "message": "Loop continuo iniciado",
            "pid": os.getpid(),
            **_snapshot_session(st),
        }
    )

    while not _should_stop():
        run_cycle(app, st, once=False)
        if _should_stop():
            break
        # Intervalo: con videos usa intervalo_loop; sin novedad, intervalo_loop_vacio
        nuevos = 0
        try:
            pend = app.contar_videos_pendientes()
            nuevos = int(pend.get("nuevos") or 0)
        except Exception:
            pass
        wait = int(
            st.session_state.get("intervalo_loop")
            if nuevos > 0
            else st.session_state.get("intervalo_loop_vacio")
            or st.session_state.get("intervalo")
            or 60
        )
        _log(f"Esperando {wait}s (pendientes≈{nuevos})…")
        _write_status(
            {
                "running": True,
                "phase": "waiting",
                "mode": "loop",
                "message": f"Esperando {wait}s antes del próximo ciclo",
                "wait_seconds": wait,
                "pendientes": nuevos,
                "pid": os.getpid(),
                **_snapshot_session(st),
            }
        )
        for _ in range(wait):
            if _should_stop():
                break
            time.sleep(1)

    _log("Stop solicitado — deteniendo worker")
    _clear_stop_flag()
    _write_status(
        {
            "running": False,
            "phase": "stopped",
            "mode": "loop",
            "message": "Worker detenido",
            "pid": None,
            **_snapshot_session(st),
        }
    )
    _clear_pid()
    return 0


def cmd_status() -> int:
    print(json.dumps(_read_status(), ensure_ascii=False, indent=2))
    return 0


def cmd_stop() -> int:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    STOP_PATH.write_text("stop", encoding="utf-8")
    _log("Flag de stop escrito")
    # Actualizar status si no hay proceso vivo
    st_data = _read_status()
    st_data["message"] = "Stop solicitado"
    st_data["phase"] = "stopping"
    _write_status(st_data)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Worker headless Video Analyzer (Next.js)")
    parser.add_argument(
        "command",
        choices=["once", "loop", "status", "stop"],
        help="once=un ciclo | loop=continuo | status | stop",
    )
    args = parser.parse_args()
    if args.command == "once":
        return cmd_once()
    if args.command == "loop":
        return cmd_loop()
    if args.command == "status":
        return cmd_status()
    if args.command == "stop":
        return cmd_stop()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
