# Video Analyzer v4.0 — App Monitoreo

**Fecha:** 2026-07-27  
**Repositorio:** [appmonitoreo](https://github.com/joelGuerraArias/appmonitoreo)  
**Tag:** `v4.0`

## Resumen

Release mayor sobre **v1.1** (Nora): parrilla TV, limpieza automática de origen, reintento de videos en grabación, panel Next.js, y mejoras Intrant/Telegram/Brevo/Sheets.

## Cambios respecto a v1.1

### Escaneo inteligente

- Filtro por canal vía `programacion_tv.json` (`escaneo_solo_horarios`).
- Sábado y domingo: sin filtro — todos los videos.
- Canales sin horario de escaneo (CDN, TRA, …): todos los videos entre semana.
- Alias de nombres de canal en archivos MP4.

### Post-proceso del video origen

- Con coincidencias o tangenciales → `procesados/` junto al canal.
- Sin match ni tangenciales → borrado permanente.
- Fuera de horario (lun–vie) → borrado permanente + UI.
- Solo borra dentro de `videos procesados/`.

### Videos en grabación

- Archivo en uso → cola de reintento al **final del ciclo** (no `archivos_fallidos/`).

### Pipeline y envíos

- Intrant prioritario; clips anclados al término.
- Telegram con vídeo obligatorio; Brevo inmediato por coincidencia.
- Google Sheets: fechas texto, tangenciales al detectar.
- Auto-escaneo 06:30; panel `app-monitoreo-next/`.

## Archivos principales

| Archivo | Rol |
|---------|-----|
| `appMonitoreo.py` | App Streamlit principal |
| `programacion_tv.json` | Parrilla y filtros de escaneo |
| `worker_next_monitoreo.py` | Worker para Next.js |
| `app-monitoreo-next/` | Panel web Next.js |
| `clip_intro.py` | Intro logo + voz |
| `google_sheet_index_utils.py` | Índice Sheets columna A |
| `README.md` | Documentación y changelog |

## Instalación / actualización desde v1.1

1. `git pull` o clonar tag `v4.0`.
2. Copiar `.env` y `clientes_config.json` locales (no están en el repo).
3. `pip install -r requirements.txt` (o `requirements_installable.txt`).
4. Reiniciar Streamlit (`EJECUTAR_STREAMLIT.bat`) o Next (`EJECUTAR_NEXT_MONITOREO.bat`).

## Versión anterior

- **v1.1** — Tangenciales a Google Sheets al detectar.
- **v1.0** — Primera publicación en GitHub.
