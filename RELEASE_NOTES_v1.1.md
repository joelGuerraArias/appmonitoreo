# Nora v1.1 — App Monitoreo

**Fecha:** 2026-05-19  
**Repositorio:** [appmonitoreo](https://github.com/joelGuerraArias/appmonitoreo)  
**Tag:** `v1.1`

## Resumen

Actualización sobre **v1.0** centrada en tangenciales y Google Sheets.

## Cambios principales

### Tangenciales → Google Sheets al detectar (no solo al cierre)

- Nuevas funciones: `enviar_tangencial_una_a_google_sheets`, `notificar_google_sheets_tangencial_inmediato_si`.
- Al registrar una tangencial se envía a Sheets **en el mismo momento** que el correo Brevo inmediato.
- Al **cerrar el ciclo** solo se reintentan filas pendientes (`sheets_enviado`); no se duplican las ya enviadas.
- Texto en UI del bloque de cierre aclarando este comportamiento.

### Nota operativa (18/05/2026)

- Dos tangenciales Edesur (El Matutino `clip_05` y `clip_16`) llegaron por correo pero no aparecían en la hoja aunque el log indicaba envío correcto; se reinsertaron manualmente en la hoja Edesur.
- Tras reiniciar la app con este release, las tangenciales nuevas deben verse en Sheets al detectarse.

## Archivos incluidos en este release

| Archivo | Rol |
|---------|-----|
| `appMonitoreo.py` | Aplicación principal |
| `clip_intro.py` | Intro logo + voz (coincidencias) |
| `google_sheet_index_utils.py` | Índice columna A en Sheets |
| `logos/README.txt` | Convención de logos por canal |

## Requisitos

- `.env` con credenciales Google (`GOOGLE_REFRESH_TOKEN`, etc.), Brevo y resto según cliente.
- `clientes_config.json` local (no incluido en el repo por secretos).
- Reiniciar Streamlit/app tras actualizar para cargar el código nuevo.

## Versión anterior

- **v1.0** — Primera publicación en GitHub (`Nora v1.0 - appMonitoreo.py`).
