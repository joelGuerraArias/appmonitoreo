# Video Analyzer — Next.js standalone (sin Streamlit)

Al ejecutar Next se arranca **solo** el pipeline completo vía `worker_next_monitoreo.py`.  
**No necesitas abrir Streamlit** (`appMonitoreo.py` / puerto 8501).

## Arranque rápido

Doble clic en la raíz del repo:

```text
EJECUTAR_NEXT_MONITOREO.bat
```

O:

```bash
cd app-monitoreo-next
npm run dev
```

→ http://localhost:3000  
→ A los ~2–3 s arranca el worker Python en loop (si hay entidades ON).

## Qué se inicia solo

| Pieza | Quién la levanta |
|-------|------------------|
| UI web | Next.js |
| Escaneo / transcripción / clips / envíos | `worker_next_monitoreo.py` (mismo código que Streamlit) |
| Auto-escaneo 06:30 | Scheduler **dentro de Next** (servidor), no Streamlit |

Prefs en `videos procesados/next_prefs.json`:

- `auto_start_worker` (default `true`)
- `auto_escaneo_enabled` / `auto_escaneo_hora`

## Apagar auto-start

Sidebar → **Arranque autónomo** → desmarcar  
o en `.env.local`:

```env
NEXT_AUTO_START_WORKER=false
```

## Requisitos

- `venv_new` con las deps del analizador
- `.env` y `clientes_config.json` en la raíz del repo
- **No** hace falta `streamlit run`

## Nota

No corras Streamlit **y** el worker Next a la vez sobre los mismos videos.
