# Grabaciones — Video Analyzer Pro v5.0

Aplicación de **análisis de video con IA** (Streamlit): busca términos en grabaciones, genera clips, transcribe con Whisper / APIs y envía resultados a **Telegram**, **webhooks**, **correo (Brevo)**, **Google Drive**, **Cloudinary**, **Cloudflare R2** (opcional) y **Supabase**, con soporte **multi-cliente** (cada término puede ir a destinos distintos).

**Versión actual:** **5.0** (`appMonitoreo.py`, tag Git `v5.0`).  
**Versión anterior en GitHub:** **v4.0** (2026-07-27).

---

## Video Analyzer v4.0 — novedades respecto a v1.1 / v3

Publicación **2026-07-27**. Resumen de lo añadido o cambiado respecto al release anterior (`v1.1` en GitHub, documentación interna v3):

### Escaneo y parrilla TV

- **`programacion_tv.json`**: filtro `escaneo_solo_horarios` por canal (Teleantillas, Telemicro, Acento, etc.) — solo lun–vie en los bloques definidos.
- **Fin de semana (sáb/dom):** se procesan **todos** los videos, sin filtro de horario.
- **Medios sin horario de escaneo** (CDN, TRA, Intrant, etc.): se procesan **todos** los videos a cualquier hora entre semana.
- **Alias de canales** en nombres de archivo (`Acento_TV`, `CDN_En_Vivo`, `Telemicro_Canal_5`, …).
- UI clara: *“Video fuera de horario”* y resumen de eliminados al cierre del ciclo.

### Gestión de archivos origen

- Tras analizar **con coincidencias o tangenciales** → mueve el MP4 a **`procesados/`** en la misma carpeta del canal.
- **Sin coincidencias ni tangenciales** → **borrado permanente** (`os.remove`, no Papelera) + audios auxiliares del mismo nombre.
- **Fuera de horario (lun–vie)** → mismo borrado permanente + aviso en UI.
- **Candado de seguridad:** solo borra dentro de `videos procesados/`.

### Grabación en curso

- Si el video **está en uso** (WinError 32, archivo bloqueado, ffmpeg no puede leer): se **anota en UI** y se **reintenta al final del ciclo** — no va a `archivos_fallidos/` mientras sigue grabando.

### Intrant, clips y envíos

- Términos Intrant **prioritarios** (no bloqueados como tangencial por IA).
- **`intran` / `intrán`** → canónico `intrant`.
- Clips **anclados al término** (poco antes, más después; no cortar el cierre de la idea).
- **Telegram:** vídeo obligatorio con reintentos R2/Cloudinary/Bunny.
- **Brevo:** correo inmediato por coincidencia (no solo al cierre del lote).
- **Google Sheets:** columnas `A:H`, fechas `DD/MM/YYYY` como texto, tangenciales al detectar.

### Panel y operación

- **`app-monitoreo-next/`** + **`worker_next_monitoreo.py`**: panel Next.js con worker Python (Streamlit opcional).
- **Auto-escaneo 06:30** configurable (`.env`: `AUTO_ESCANEO_*`) + reloj en sidebar.
- Protección **BOM** en `clientes_config.json` y `.env`.

### Archivos nuevos relevantes en v4

| Archivo | Función |
|---------|---------|
| `programacion_tv.json` | Parrilla y filtros de escaneo por canal |
| `app-monitoreo-next/` | UI Next.js del monitoreo |
| `worker_next_monitoreo.py` | Worker headless del pipeline |
| `README_envios.md` | Documentación de envíos por cliente |
| `RELEASE_NOTES_v4.md` | Notas de este release |

> **Secretos:** `clientes_config.json`, `.env` y configs en `videos procesados/` **no** se suben al repo. Copia local obligatoria.

Ver también la sección **📌 Cambios automáticos** al final de este README.

---

### Documentación v5 — punto de reversión (desde 2026-04-16)

A partir de esta fecha, las entradas nuevas en este README y los cambios relacionados se consideran línea base **v5**. Si más adelante quieres **volver atrás**, usa una de estas opciones:

1. **Git:** crea un tag o rama en este commit, por ejemplo `git tag video-analyzer-readme-v5` (o el hash del commit donde quedó estable la v5).
2. **Sin Git:** guarda copias manuales de los archivos críticos con sufijo `_v5` o en una carpeta `backup_v5/`.

**Archivos que conviene respaldar antes de cambios grandes:** `appMonitoreo.py`, `clientes_config.json`, `terminos_guardados.json`, y este `README.md`.

**Qué queda asociado a la documentación v5:** dónde se guarda cada entidad (`clientes_config.json` y `terminos_guardados.json` con `cliente_id`), advertencias al **eliminar un cliente** (términos huérfanos y caída al cliente default), el campo **`incluir_en_analisis`** para incluir o excluir entidades del análisis (sidebar), cliente **MINERD**, y la **Parte A** de tangenciales en Google Drive (`subir_tangencial_videoscheck_a_google_drive`, carpeta `folder_id_tangenciales` y subcarpetas por entidad opcionales).

---

## Resumen general (v5)

Panorama del **Video Analyzer Pro** y de lo acordado en la línea base **v5** (multi-cliente, tangenciales y MINERD). El código se mantiene en **`grabaciones`** como referencia operativa.

### Qué hace el sistema

- App **Streamlit** (`appMonitoreo.py`): escanea videos en la carpeta configurada, transcribe (Whisper / flujo híbrido), detecta **términos** por cliente, genera **clips** con ayuda de modelos (p. ej. Gemini para segmento y relevancia), y distingue **coincidencias** (se envían como alertas) de **menciones tangenciales** (mención sin desarrollo o baja relevancia: se documentan y pueden guardarse en `videoscheck` sin tratarlas como clip “fuerte”).

### Entidades y configuración

- **`clientes_config.json`**: define clientes (**Sistema principal / EDESUR** `default`, **Intrant**, **MINERD**) con `telegram`, `brevo`, `google_drive`, `cloudinary`, `r2`, `supabase`, `webhook`, colores, etc.
- **`terminos_guardados.json`**: cada término enlaza a un **`cliente_id`** para saber a qué entidad notificar.
- **`incluir_en_analisis`**: permite **excluir** un cliente del barrido de análisis desde la sidebar (**Análisis por entidad**) sin borrar sus términos.
- El código que importa para el analizador de video vive en esta carpeta **`grabaciones`** (p. ej. `EJECUTAR_VIDEO_ANALYZER3.bat` → `appMonitoreo.py` aquí). Otras copias del proyecto no forman parte del flujo salvo que tú las mantengas a mano.

### Coincidencias (alertas “fuertes”)

- Envío según cliente: **Telegram**, **Brevo**, **webhooks**, **Google Drive** (carpeta habitual del cliente), **Cloudinary**, **Cloudflare R2** (si está activo), **Supabase**, **Google Sheets** (si `google_sheets.enabled` y `spreadsheet_id` en el cliente).
- **Anti-duplicados** en `videos procesados/envios_coincidencias_dedupe.json` (TTL ~14 días, huella por cliente/término/tiempo/contexto) para no reenviar la misma noticia por renombre de archivo o reproceso.
- **Sheets — columna “periodista” / origen:** en cada fila de coincidencia se escribe **`TV`** (monitoreo televisión), no `redaccion`.
- **Drive — carpetas fijas de coincidencias (opcional, `.env`):**
  - `GOOGLE_DRIVE_INTRANT_COINCIDENCIAS_FOLDER_ID` — cliente **Intrant** → carpeta compartida de coincidencias Intrant.
  - `GOOGLE_DRIVE_EDESUR_COINCIDENCIAS_FOLDER_ID` — **Edesur / sistema principal** (heurística por `cliente_id` y nombre) → carpeta **edesurVideos**.
  - Tangenciales siguen usando `folder_id_tangenciales` del JSON y, si aplica, `GOOGLE_DRIVE_FOLDER_TANGENCIALES_ID` como raíz por defecto.

### Tangenciales

- Copia local bajo **`videos procesados/videoscheck`** con prefijo **`_tangencial_`** (video + `.txt` de minutos + **`index.csv`** de trazabilidad).
- **Analisishoy** (`Analisishoy_YYYYMMDD.md`) y el **MD de sesión** pueden incluir bloque de tangenciales; **Brevo** envía **correo inmediato** al detectar cada tangencial (si Brevo está activo para el cliente) y otro **resumen al cierre del ciclo** con todas las del lote.
- **Frase tangencial (enriquecimiento opcional):** si la API auxiliar está activa (`DEEPSEEK_*` / `VIDEO_DEEPSEEK_TANGENCIALES` etc. según `.env`), se puede generar **una sola frase** integrando **transcripción** + **motivo técnico** del análisis; el motivo largo del clasificador queda en **`motivo_sistema`**. Se enriquece **antes** del correo inmediato; los ítems ya enriquecidos no se vuelven a procesar al cerrar el ciclo.
- En correos (HTML y texto plano) no se usa la etiqueta “motivo IA”; la frase visible es el **motivo** / **Por qué tangencial**; el bloque de referencia es **motivo de análisis técnico** cuando aplica.
- **Momento de la mención:** en plantillas tangenciales se muestra de forma explícita el **instante dentro del archivo** donde se detectó el término (`timestamp` → formato `XmYs` y segundos desde el inicio), columna dedicada, tooltips y bloque destacado cuando el correo es de un solo ítem.
- **Parte A — Drive:** si el cliente tiene **`google_drive.folder_id_tangenciales`**, tras el guardado local se suben a esa carpeta el video, el txt de minutos y un **`*_transcripcion_contexto.txt`**. Con **`tangenciales_usar_subcarpeta_cliente`** se usa (o crea) una subcarpeta por entidad: **`edesur`** (cliente `default`), **`intrant`**, **`minerd`**, bajo la misma raíz compartida.

### Cliente MINERD (estado v5)

- Términos propios (educación, INABIE, etc.); **Supabase** hacia **`alertas_medios`**; **Brevo** con destinatarios configurados; **Google Drive** con carpeta de clips y carpeta de tangenciales; **Telegram** activo hacia el canal público **`@InabieAlertas`** (bot añadido como admin del canal).

### Archivos que definen el comportamiento

| Archivo | Función |
|---------|---------|
| `appMonitoreo.py` | Aplicación principal |
| `clientes_config.json` | Clientes y parámetros de integraciones |
| `terminos_guardados.json` | Términos y `cliente_id` |
| `videos procesados/videoscheck/` | Material de revisión (coincidencias `_coincidencia_` y tangenciales `_tangencial_`) |
| `videos procesados/envios_coincidencias_dedupe.json` | Dedupe de envíos de coincidencias |

---

## Requisitos

- **Windows** (el proyecto incluye rutas y notas orientadas a CUDA/NVIDIA en el código).
- **Python 3.10+** recomendado.
- **GPU NVIDIA** opcional pero recomendada para **faster-whisper** / **torch** (CUDA 12.6 referenciado en el arranque).
- **ffmpeg** opcional si procesas o cortas video con herramientas que lo requieran.

---

## Instalación rápida

```powershell
cd "C:\Users\Joel Guerra\Desktop\grabaciones"
python -m venv venv_new
.\venv_new\Scripts\Activate.ps1
pip install -r requirements.txt
```

Opcional: copia o crea un archivo **`.env`** en la raíz con claves (Supabase, APIs, etc.). El código usa `python-dotenv` donde aplique.

---

## Cómo ejecutar la app principal

**Opción A — script incluido**

```text
EJECUTAR_VIDEO_ANALYZER3.bat
```

Activa `venv_new`, `venv_video` o `.venv` (en ese orden) y lanza:

```text
streamlit run appMonitoreo.py
```

**Opción B — manual**

```powershell
.\venv_new\Scripts\Activate.ps1
streamlit run appMonitoreo.py
```

Abre el navegador en **http://localhost:8501** (puerto por defecto de Streamlit).

---

## Otros arrancadores (`.bat`)

| Archivo | Uso |
|--------|-----|
| `EJECUTAR_VIDEO_ANALYZER_AUTO.bat` | Variante automática del analizador |
| `EJECUTAR_CUTTER.bat` | Herramienta cutter |
| `EJECUTAR_TRANSMISTRAL.bat` | Flujo relacionado con Transmistral |
| `EJECUTAR_STREAMLIT.bat` / `ejecutar_app.bat` | Otros arranques Streamlit según tu configuración |

---

## Carpetas y salida importante

Por defecto todo queda bajo la carpeta del script, resuelta en **ruta absoluta** (no depende del “directorio de trabajo” actual):

| Ruta / variable | Descripción |
|-----------------|-------------|
| **`videos procesados/`** | Resultados, logs de escaneo, configs de webhook/Telegram/Cloudinary en subcarpetas, clips por coincidencia, caché, etc. |
| `CARPETA_VIDEOS` / `CARPETA_PROCESADOS` | Por defecto apuntan a esa misma carpeta `videos procesados`; se pueden **sobrescribir con variables de entorno**. |
| **`videos procesados/videoscheck`** | Copias o videos marcados para revisión. |
| **`videos procesados/archivos_fallidos`** | Archivos con error al procesar + `fallidos.txt` en `videos procesados`. |
| **`videos procesados/envios_coincidencias_dedupe.json`** | Registro persistente de coincidencias **ya notificadas** (anti-duplicados entre Telegram, correo y demás destinos del mismo envío). |
| **`logs/`** | Logs diarios de la app (relativos al directorio desde el que se ejecuta Streamlit). |

Archivos de configuración en la **raíz del proyecto** (ejemplos): `terminos_guardados.json`, `clientes_config.json`.

---

## Variables de entorno útiles

| Variable | Significado |
|----------|-------------|
| `CARPETA_VIDEOS` | Carpeta donde se buscan los videos a analizar (por defecto `videos procesados`). |
| `CARPETA_PROCESADOS` | Carpeta de salida (clips, procesados, caché, etc.). |
| `GOOGLE_DRIVE_FOLDER_TANGENCIALES_ID` | (Opcional) ID de carpeta Drive raíz por defecto para tangenciales cuando el JSON no define otra. |
| `GOOGLE_DRIVE_INTRANT_COINCIDENCIAS_FOLDER_ID` | (Opcional) Carpeta Drive fija para **coincidencias** del cliente Intrant. |
| `GOOGLE_DRIVE_EDESUR_COINCIDENCIAS_FOLDER_ID` | (Opcional) Carpeta Drive fija para **coincidencias** Edesur / sistema principal (heurística en código). |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | Cliente OpenAI-compatible para enriquecer frases tangenciales (`DEEPSEEK_TANGENCIALES_ENABLED` etc. para activar/apagar). |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | Integración Supabase. |
| Otras | APIs (OpenAI, Mistral, Gemini, etc.) según configures en la UI o en `.env`. |

---

## Estructura del repo (resumen)

- **`appMonitoreo.py`** — Aplicación principal Streamlit.
- **`coincidencias_logger.py`** — Logging de coincidencias y APIs.
- **`config/`** — Ajustes centralizados (`get_settings()`).
- **`requirements.txt`** / **`requirements_installable.txt`** — Dependencias (la variante “installable” fija versiones en algunos paquetes).
- Scripts auxiliares: `videoAnalizerv2.py`, `videoAnalizerv3.py`, `transmistral*.py`, tests `test_*.py`, etc., según necesites.

---

## Atajos en el escritorio

Si creaste un lanzador en el escritorio (por ejemplo **`Iniciar Video Analyzer 3.bat`**), suele llamar a `EJECUTAR_VIDEO_ANALYZER3.bat` dentro de esta carpeta; si mueves el proyecto, actualiza la ruta `cd` en ese `.bat`.

---

## Licencia y uso

Uso interno / proyecto personal salvo que indiques otra licencia. Las marcas citadas pertenecen a sus titulares.

---

## 📌 Cambios automáticos

- [2026-07-31] FEAT: Video Analyzer v5.0
  - UI Versión 5 + banner de cadena IA; sidebar con horarios de escaneo activos.
  - Cadena: Kimi → GLM → Gemini/GPT-4o → DeepSeek (Kimi default).
  - Parrilla: bloques 12:00–15:00 y 21:00–24:00 en canales filtrados.

- [2026-07-31] MOD: cadena de análisis Kimi → GLM → Gemini/GPT-4o → DeepSeek
  - Kimi es el motor predeterminado al abrir la app (ya no Gemini).
  - Si un motor falla, se pasa al siguiente automáticamente; DeepSeek es el último fallback.
  - Tangenciales: Kimi → GLM → DeepSeek. Sidebar: elegir desde dónde empieza la cadena.

- [2026-07-31] FEAT: restaurado selector Ollama (GLM / Kimi) en sidebar
  - Se había perdido con un `git checkout` accidental; no se quitó a propósito.
  - Sidebar: radio GLM 5.2 / Kimi K2.7 + Activar / Volver a Gemini / Probar conexión; lista de términos activos según `incluir_en_analisis`.
  - Pipeline clips y tangenciales vía `*_sesion` (Ollama con fallback Gemini/DeepSeek).
  - `env_template.txt`: variables `OLLAMA_*`.

- [2026-06-08] FEAT: Ollama Cloud opcional en appMonitoreo (GLM 5.2 / Kimi K2.7)
  - Sidebar: radio + botón «Activar Ollama» / «Volver a Gemini»; Gemini sigue por defecto.
  - Clips: `determinar_segmento_inteligente_sesion` / `extraer_idea_general_segmento_sesion`; fallback Gemini si Ollama falla.
  - Tangenciales (sesión Ollama): GLM 5.2 → fallback DeepSeek vía `enriquecer_motivos_tangenciales_sesion`.
  - `.env`: `OLLAMA_BASE_URL`, `OLLAMA_MODEL_GLM`, `OLLAMA_MODEL_KIMI` (requiere `ollama signin` para `:cloud`).

- [2026-06-08] FEAT: limpieza automática duplicados Supabase (`alertas_medios`)
  - `supabase_limpiar_duplicados.py`: agrupa por URL o `(término, archivo, medio)`; conserva el más reciente; CLI `--dry-run`; contador cada 5 inserts en `videos procesados/supabase_insert_counter.json`.
  - `appMonitoreo.py`: hook post-insert en `enviar_supabase_cliente`.
  - `eliminar_duplicados.py`: delega al módulo nuevo (credenciales vía `.env`).

- [2026-06-08] FIX: informe_general_video.md — registro fiable de coincidencias/tangenciales
  - `appMonitoreo.py`: informe se escribe **antes** de subidas CDN; ruta relee `.env` en cada append; índice JSON + sidebar con últimas entradas; sync al cierre del ciclo; aviso Ctrl+Fin (entradas al final del archivo).

- [2026-05-31] FEAT: prevideo TTS — fecha/hora inteligente desde nombre de archivo
  - `clip_intro.py`: `parsear_emision_desde_nombre_archivo` (multi-formato: `_720p_…`, `YYYY-MM-DD_HH-MM-SS`, Telesistema `2026-05-31 12_16`, carpeta emisión); fallback Mistral JSON si falta hora (`INTRO_PARSE_LLM=1`).

- [2026-05-31] FIX: prevideo (logo + voz) antes del clip — concat ffmpeg
  - `clip_intro.py`: normaliza resolución/fps/audio antes de concatenar intro+clip; fps exacto (no redondear 29.97→30); stderr útil en logs si vuelve a fallar.

- [2026-05-31] MOD: correo Brevo — cola por emisión + contenido alineado al MD
  - `appMonitoreo.py`: un solo correo Brevo por término+emisión por ciclo (gana la coincidencia más tardía, p. ej. clip_16 @ 1m36s en lugar de clip_11 @ 7s). Cuerpo con bloque **Coincidencia @ instante**, contexto detectado y transcripción del **clip** (no del archivo completo). Asunto con instante y medio. Flush al cierre del ciclo antes del MD de sesión.

- [2026-05-31] MOD: correo Brevo — prioridad y asunto distintivo por coincidencia
  - `appMonitoreo.py`: Brevo se envía **antes** que webhooks (evita retrasos por retries HTTP 404). Asunto incluye instante (`@ 1m36s`) y medio. Log con asunto + primer `To`. Dedupe skip ya no reporta éxito de envío (`return False`).

- [2026-05-14 10:57] MOD: Google Sheets por cliente + tangenciales + link Drive
  - `appMonitoreo.py`: nuevo mapeo por cliente para Sheets (`construir_fila_google_sheet_cliente`) con dos formatos: **Edesur/default** con índice `#` y **Intrant** sin `#` con columna `titulo`. `append_fila_google_sheet` ahora soporta `incluir_indice=True/False`. Coincidencias priorizan `webViewLink` de Drive en `url/link` (con fallback a Cloudinary/R2). Se agregó envío de tangenciales al cierre de ciclo a la misma hoja configurada por cliente (`enviar_tangenciales_a_google_sheets`), con logs por cliente/formato y resultado.

- [2026-05-13] MOD: títulos legibles de archivo (emisión broadcast)
  - `archivo_broadcast_legible_y_referencia` / `archivo_broadcast_lineas_correo_plano`: nombres tipo `EnTelevision_720p_YYYY-MM-DD_HH-MM-SS_segNNN` → «EnTelevision 13 de Mayo a las 7:28» (con año en el texto si no es el año en curso); se mantiene nombre técnico cuando aplica. Usado en correos coincidencia/Brevo global, tabla y texto tangenciales, HTML del clip, Telegram/Webhook (`mensaje_completo`), TXT Drive y contexto UI.

- [2026-05-13] MOD: UI — correo de cierre tangenciales
  - Tras cada ciclo, sección explícita “Correo Brevo — cierre de ciclo (tangenciales)” con **motivo si no hay envío** (sin tangenciales acumuladas), **éxito por entidad**, **warnings con mensaje devuelto** si no se envió (Brevo off, sin credenciales, sin destinatarios) y texto de ayuda si ningún cliente recibió el correo.

- [2026-05-06] MOD: transcripción en coincidencias sin mínimo de caracteres
  - Si hay transcripción no vacía (tras `strip()`), entra siempre en el **correo** (`resumen_para_email`), en el **TXT de Google Drive**, en la **subida consolidada de transcripción** y en **AnalisisHoy / informe MD** (antes se filtraba por longitud). La UI de contexto del envío lo indica explícitamente.

- [2026-05-06] FEAT+MOD: coincidencias Sheets / Drive; tangenciales (frase y momento) y correo
  - **Google Sheets:** segunda columna de cada fila de coincidencia (origen tipo “periodista”) pasa a **`TV`** en lugar de `redaccion`.
  - **Drive coincidencias:** variables `.env` `GOOGLE_DRIVE_INTRANT_COINCIDENCIAS_FOLDER_ID` y `GOOGLE_DRIVE_EDESUR_COINCIDENCIAS_FOLDER_ID`; `enviar_gdrive_cliente` elige carpeta por heurística Intrant / Edesur antes del `folder_id` del JSON (MINERD u otros siguen la config del cliente).
  - **Tangenciales — frase resumen:** opcionalmente una sola frase integrando **transcripción** + **motivo técnico** (`motivo` / `motivo_sistema`); enriquecimiento **antes** del Brevo inmediato; ítems con `motivo_sistema` ya relleno no se re-procesan al cierre del ciclo. Los **correos** no mencionan proveedor de API.
  - **Etiquetas de correo:** sin “motivo IA”; texto de referencia como **análisis técnico** cuando hay `motivo_sistema`.
  - **Momento de mención del término:** `tangencial_formato_momento_mencion_termino()`, columna renombrada en HTML, tooltip con segundos desde el inicio, callout destacado en correo de un solo ítem, texto plano inmediato y de cierre con línea dedicada.

- [2026-04-30] MOD: enlaces CDN en Telegram (404 / URL pegadas)
  - `escape_telegram_text` ya no borra `_[]()` etc. (rompía URLs tipo `video_analyzer_clips` y unía líneas al copiar). `_codificar_url_path_unicode` + `_filas_enlaces_clip_codificadas` codifican el path (p. ej. `educación` → `%C3%B3…`). Bloque de enlaces con separación `\n\n`; `sendVideo` solo envía `parse_mode` si aplica.

- [2026-04-22] FEAT: emisión legible y tangenciales en correo
  - `appMonitoreo.py`: `parse_nombre_emision_broadcast` / `formatear_emision_legible_desde_nombre` (fechas con espacio o `_`, meses en español, audio `.m4a`/`.mp3`). `formatear_nombre_medio_desde_ruta` y `extraer_info_medio_hora` usan el título legible; `renombrar_clip_coincidencia` usa `slug_medio_desde_nombre_archivo`. Correos de coincidencia y Telegram muestran emisión legible + referencia técnica si aplica. Narrativa tangencial (plain/MD/HTML) en listas por término y bloque de motivos separado; Supabase parsea medio/fecha/hora vía el mismo parser.

- [2026-04-22] MOD: restauración términos (post espacio en disco)
  - Se restauraron `clientes_config.json` y `terminos_guardados.json` (habían quedado vacíos). EDESUR (`default`) sin `edenorte`. MINERD sin `miner` ni `minerd` (se mantienen educación, ministro, Luis Miguel De Camps, pruebas nacionales, inabie). `total_terminos`: 27.

- [2026-04-22] MOD: caption sidebar CDN y R2
  - Bajo el selector «Subir clips a» en `appMonitoreo.py`, el texto aclara que R2 solo se usa si cada cliente tiene `r2.enabled: true` en `clientes_config.json`, además de las variables `R2_*` en `.env`.

- [2026-04-16] DOC: versión de documentación **v5** (punto de reversión)
  - Este README define la línea base **v5**: convención para revertir (tag Git o copias de `appMonitoreo.py`, `clientes_config.json`, `terminos_guardados.json`, `README.md`). Incluye notas sobre entidades, `incluir_en_analisis`, MINERD y tangenciales en Drive (Parte A).

- [2026-04-06 14:00] FEAT: correo Brevo de menciones tangenciales por cliente
  - Al final de cada ciclo, `enviar_correos_tangenciales_fin_ciclo` agrupa tangenciales con `obtener_cliente_por_termino` y envía un correo por entidad (`crear_plantilla_email_tangenciales_html` + SMTP igual que coincidencias).

- [2026-04-06 12:00] FEAT: append_analisishoy_menciones_tangenciales()
  - Al cerrar cada ciclo de `buscar_y_procesar_videos`, las menciones tangenciales (archivo, término, motivo, tiempo) se añaden a `Analisishoy_YYYYMMDD.md` en `videos procesados`, con el mismo formato que la UI y marca de hora por lote.

- [2026-04-01 09:36] MOD: UI enfocada en resultados relevantes
  - Se ajustó `appMonitoreo.py` para mostrar en pantalla el proceso actual sin acumular listas y dejar persistentes solo coincidencias/menciones tangenciales.

- [2026-04-01 09:36] MOD: versionado visual a 3.0
  - Se unificaron etiquetas visibles de versión en `appMonitoreo.py` y se actualizó el título de la app a Versión 3.

- [2026-04-01 09:58] MOD: videoscheck con verificacion real
  - `guardar_video_y_minuto_coincidencia()` ahora guarda en subcarpetas por video dentro de `videoscheck`, valida la copia y reporta estado real (`copiado`, `movido`, `ya_existia`).

- [2026-04-01 10:00] MOD: marcado de tangenciales en carpeta
  - Los rechazos por mención tangencial/relevancia baja ahora se guardan en `videoscheck` bajo carpeta con prefijo `_tangencial_` para identificación rápida.

- [2026-04-01 10:02] FEAT: indice trazable en videoscheck
  - Se agregó `videos procesados/videoscheck/index.csv` con origen/destino, término, timestamp y estado de copia para cada tangencial o coincidencia guardada.

- [2026-04-01 10:19] MOD: excluir videoscheck del escaneo fuente
  - Se reforzó la búsqueda para ignorar cualquier ruta bajo `videoscheck` al detectar nuevos, evitando reprocesado o confusión de origen.

- [2026-04-02] FEAT: deduplicación de envíos de coincidencias
  - `appMonitoreo.py` registra en `videos procesados/envios_coincidencias_dedupe.json` una huella por cliente/término/tiempo en video y texto de contexto; si ya se notificó con éxito, no reenvía Telegram/correo ni otros destinos del mismo bloque.

- [2026-04-02] MOD: Telegram caption y fallback de video
  - Caption de video acotado a 1024 caracteres con log; nota adicional en chat si aplica; si `send_clips` está desactivado se deja constancia en el resultado. Si Cloudinary falla, reintento por envío directo `sendVideo` hasta 50 MB.

- [2026-04-02] MOD: aviso clip < 90s y limpieza de código muerto
  - Mensaje claro cuando solo se envía resumen por duración mínima de clip; eliminado bloque inalcanzable tras `return` en `enviar_coincidencia_inmediata`.

- [2026-04-02 14:38] MOD: no reprocesar archivos fallidos
  - En `appMonitoreo.py` y `videoAnalizerv2.py` se ignora la carpeta `archivos_fallidos` en los escaneos, se filtra por `fallidos.txt` con coincidencia por ruta o nombre base, y las estadísticas de “nuevos” no cuentan esos videos.

---

## Envíos: anti-duplicados, Telegram y clips (2026-04-02)

Documentación de lo implementado en `appMonitoreo.py` para evitar avisos repetidos y dejar claro el comportamiento de Telegram y los clips.

### Anti-duplicados (misma coincidencia, otro nombre de archivo)

- **Archivo:** `videos procesados/envios_coincidencias_dedupe.json` (se crea solo).
- **Idea:** la clave **no depende** del nombre del archivo en disco (que puede cambiar al reprocesar o mover a `archivos_fallidos`). Se calcula un hash con: id/nombre de cliente, término, segundo aproximado del hallazgo en el video, texto normalizado de contexto (o idea general) y un trozo de la transcripción del segmento.
- **TTL:** entradas antiguas se descartan pasados **14 días**; tamaño máximo aproximado **8000** claves.
- **Cuándo se bloquea el envío:** si esa huella **ya consta** en el JSON, `enviar_coincidencia_a_cliente` no envía nada (Telegram, Brevo, webhooks, Drive, Supabase en ese paso) y la UI muestra que la coincidencia **ya fue notificada**.
- **Cuándo se guarda la huella:** solo si **al menos un destino** del envío tuvo éxito (si todo falla, no se registra, para permitir reintento).
- **Flujo inmediato:** `enviar_coincidencia_inmediata` interpreta el resultado `_dedupe_skip` y termina sin error (mensaje informativo).

### Telegram: caption, resumen y video

- **Límite de API:** el caption de `sendVideo` va como máximo a **1024** caracteres (`TELEGRAM_CAPTION_MAX`); el resumen largo sigue yendo en mensajes de texto (hasta 4096 por parte en `enviar_mensaje_telegram`).
- Si el texto supera ese límite para el caption, se deja **log** y, cuando el video se envía bien, un **mensaje corto** en el chat aclarando que el análisis completo está en el mensaje de texto anterior.
- **`send_clips` desactivado** en la config del cliente: no se sube video; el resultado indica que el clip se omitió por configuración y queda trazado en log.

### Cloudinary y fallback

- Si la subida a **Cloudinary** falla pero el archivo pesa **≤ 50 MB**, se intenta **envío directo** con `sendVideo` (multipart), con timeout acorde al tamaño. Por encima de 50 MB sin URL pública no hay fallback automático en ese camino.

### Cloudflare R2 (opcional)

- Cada cliente puede tener un bloque **`r2`** en `clientes_config.json` con `enabled` y `folder` (prefijo de clave de objeto, alineado con la “carpeta” lógica de Cloudinary). Las credenciales de la cuenta R2 van en **`.env`**: `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`; opcionales `R2_REGION` (p. ej. `auto`), `R2_PUBLIC_BASE_URL` (URL pública estable por objeto), `R2_PRESIGN_SECONDS` (si no hay base pública), `R2_ENABLED=false` para desactivar todas las subidas R2.
- Código: módulo **`r2_storage.py`**, subida en paralelo con Cloudinary cuando ambos están activos para el cliente; el correo puede mostrar **dos reproductores** (principal Cloudinary y copia R2). Flujo global de prueba Brevo: `enviar_correo_brevo(..., upload_video_via='cloudinary'|'r2')`.
- CLI de prueba: `python upload_r2.py ruta/al/archivo.mp4 --key carpeta/objeto.mp4` (`--object-url` imprime solo la URL).

### Clip menor a 90 segundos

- Regla de negocio: clips **menores de 90 s** no se envían como video; **sí** se puede enviar el **resumen de texto** (Telegram, correo, etc.). La interfaz y el log indican explícitamente que el aviso es **solo texto**, sin adjunto de clip.

### Código

- Eliminado el bloque **muerto** (inalcanzable) que quedaba después del `return` principal en `enviar_coincidencia_inmediata` (cientos de líneas que nunca se ejecutaban).

---

## 📌 Cambios automáticos

- [2026-04-07] MOD: motivo tangencial explícito
  - `motivo_display_tangencial()` asegura que el campo **motivo** nunca quede vacío (por defecto *Mención tangencial sin desarrollo*) en narrativa, detalle, UI, MD, correo HTML y texto plano.

- [2026-04-07] MOD: Analisishoy y reporte de sesión
  - `generar_analisishoy_md` ahora incluye el bloque **Contexto / idea del segmento (motivo del hallazgo)** (hasta 8k caracteres), tiempo en video opcional y el mismo `timestamp` que el envío; `generar_md_sesion_coincidencias` lista ideas/contexto completos por coincidencia y **menciones tangenciales** (narrativa + detalle con motivo). Paridad aplicada en `videoAnalizerv2.py` para Analisishoy.

- [2026-04-16 12:00] MOD: MINERD — carpeta Drive tangenciales
  - En `clientes_config.json` se usa `google_drive.folder_id_tangenciales` (raíz compartida para tangenciales). `obtener_google_drive_folder_id_tangenciales()` devuelve ese ID cuando Drive está activo.

- [2026-04-16 14:30] FEAT: Parte A — tangenciales a Google Drive
  - Tras guardar en `videoscheck` con prefijo `_tangencial_` (sin cambiar ese paso), `subir_tangencial_videoscheck_a_google_drive()` sube a Drive el video, el `.txt` de minutos y `*_transcripcion_contexto.txt`. Opción `tangenciales_usar_subcarpeta_cliente`: subcarpetas `edesur`, `intrant`, `minerd` (cliente `default` → `edesur`). Coincidencias y clips habituales no se tocan.

- [2026-04-16 15:00] MOD: MINERD — Telegram
  - Cliente MINERD: `telegram.enabled` activado con token y `chat_id` `@InabieAlertas` en `clientes_config.json`.

- [2026-04-16 16:00] DOC: resumen general v5 en README
  - Nueva sección **Resumen general (v5)** al inicio del documento: qué hace el sistema, entidades, coincidencias vs tangenciales, Parte A Drive, MINERD y tabla de archivos clave.

- [2026-04-16 17:00] MOD: buscar_termino_flexible — MINERD vs minería
  - Los términos `miner` y `minerd` quedan fuera de las variaciones morfológicas automáticas (+s, +es, +a, +o), que hacían coincidir **minera** / **minero** (minería) con el término corto `miner`. Sigue aplicándose la coincidencia de palabra completa (`\b…\b`) y alias definidos en `ALIASES_TERMINOS`. Cambio en `appMonitoreo.py`.

- [2026-04-22 10:00] MOD: coincidencias — subir vídeo antes de notificar
  - `enviar_coincidencia_inmediata` aplica dedupe antes de subir al CDN, renombra el clip (`renombrar_clip_coincidencia`) y sube a Cloudinary antes de llamar a `enviar_coincidencia_a_cliente`, para que correo/Telegram/webhook reciban la URL ya publicada. El renombrado queda centralizado y sigue siendo idempotente en `enviar_coincidencia_a_cliente`.

- [2026-04-22 23:30] FEAT: Bunny.net para correo Brevo
  - `videos procesados/bunny_config.json`, `cargar_bunny_config` / `guardar_bunny_config`, `subir_video_bunny` (PUT a Storage, URL del Pull Zone). `enviar_correo_brevo` acepta `video_url_bunny`, `upload_video_via='bunny'|'cloudinary'`; con `bunny` sube primero y el HTML del correo usa esa URL.

- [2026-04-22 23:55] MOD: Bunny — validación y HTTP
  - `cargar_bunny_config` rechaza JSON que no sea objeto; `subir_video_bunny` acepta respuesta HTTP 204; URLs explícitas en `enviar_correo_brevo` se normalizan con `.strip()`.

- [2026-04-23 00:15] MOD: coincidencias — URL de Bunny en correo (paridad con Cloudinary)
  - Tras subir el clip, `enviar_coincidencia_inmediata` sube también a Bunny si `bunny_config.json` está activo y pasa a `enviar_coincidencia_a_cliente` la URL pública `video_url_cloudinary or video_url_bunny or video_url`, de modo que `enviar_brevo_cliente` y la plantilla HTML usan la misma URL directa del fichero en CDN que con `secure_url` de Cloudinary.

- [2026-04-23 00:40] MOD: correo — dos URLs (Cloudinary + Bunny)
  - `crear_plantilla_email_html` admite `video_url_bunny` y muestra botones, reproductores, enlaces y texto plano para cada URL distinta. `enviar_coincidencia_inmediata` pasa la segunda URL solo si existen ambas subidas. `enviar_correo_brevo`: si vienen `video_url_gdrive` y `video_url_bunny` juntas, o tras subir a Cloudinary también sube a Bunny cuando está habilitado, el correo incluye ambas.

- [2026-04-23 15:00] MOD: correo — solo Cloudinary otra vez
  - La plantilla HTML y Brevo vuelven a un único enlace/reproductor. `enviar_coincidencia_a_cliente` usa `video_url_correo` (= solo Cloudinary) para el correo; Telegram/Supabase/MD siguen con `video_url` (Cloudinary o Bunny). Bunny puede seguir subiéndose en paralelo pero no se enlaza en el correo. `enviar_correo_brevo` ignora Bunny en el HTML; si solo hay URL Bunny explícita, el correo va sin vídeo en plantilla.

- [2026-04-23 12:00] MOD: Bunny PUT alineado con cliente Edge Storage
  - `subir_video_bunny` arma el PUT como `https://{host}/{quote(zona)}/{quote(seg)}...`, admite `remote_filename` con ruta completa (`videos/grabaciones/archivo.mp4`) y `upload_timeout_seconds` opcional en `bunny_config.json` (por defecto 3600).

- [2026-04-23 12:30] MOD: Bunny = misma convención que Cloudinary
  - `subir_video_bunny(video_path, termino="", timestamp="", remote_path_override=None)` replica el patrón de `subir_video_cloudinary`: carpeta `folder` del JSON + `{termino}_{timestamp}_{nombreBase}.{ext}` (doble `_` si no hay timestamp). Las llamadas en coincidencias y Brevo pasan el mismo `termino_encontrado` que Cloudinary; `remote_path_override` conserva rutas tipo `videos/grabaciones/...`.

- [2026-04-23 13:00] MOD: bunny_config — carpeta de Storage
  - En `videos procesados/bunny_config.json`, `folder` pasa a `videos/grabaciones` para alinear las subidas con la ruta del Pull Zone (`…/videos/grabaciones/…mp4`).

- [2026-04-23 14:00] MOD: Bunny — credenciales y activación
  - `cargar_bunny_config` completa `api_key` desde `BUNNY_STORAGE_API_KEY` o `BUNNY_API_KEY` si el JSON la deja vacía; default de `folder` alineado con `videos/grabaciones`. Plantilla JSON con `enabled: true`, zona `fgjmultimedios` y host `storage.bunnycdn.com` como en el panel Bunny.

- [2026-04-22 18:00] REFACTOR: módulo `bunny_storage` y Pull Zone en env
  - Nuevo `bunny_storage.py` (normalización de host, path codificado con `quote`, PUT y URL pública vía `public_delivery_url`). `subir_video_bunny` delega en `upload_file` y usa la misma codificación para la URL del Pull Zone. `cargar_bunny_config` aplica `BUNNY_STORAGE_PUBLIC_BASE` sobre `cdn_base_url` cuando está definida (hostname real del Pull Zone, no `{storage_zone}.b-cdn.net`). Ejemplo de plantilla: zona `fgjviii`, base `https://fgjviiipull.b-cdn.net`.

- [2026-04-22 21:00] MOD: Bunny — misma convención que Cloudinary (sin tocar Cloudinary)
  - `_bunny_ruta_remota_misma_convencion_cloudinary()` calcula la ruta en Bunny leyendo `cargar_cloudinary_config()` y repitiendo la misma fórmula de `public_id` que `subir_video_cloudinary`, más extensión. `subir_video_cloudinary` sigue igual que antes (sin helper compartido).

- [2026-04-22 22:15] FEAT: correo tangenciales — enlace al vídeo en Google Drive
  - `subir_tangencial_videoscheck_a_google_drive` devuelve `(ok, mensaje, url_video_drive)` usando `webViewLink` o `https://drive.google.com/file/d/{id}/view`. Tras subida OK se rellena `video_url_drive` en el último ítem de `menciones_tangenciales_data`. `crear_item_tangencial` incluye la clave por defecto. Plantilla HTML y cuerpo plano de `enviar_brevo_menciones_tangenciales_cliente` muestran columna «Vídeo (Drive)» / línea con la URL.

- [2026-05-19] FEAT: intro logo + voz Mistral antes de cada clip de coincidencia
  - Módulo `clip_intro.py`: logo en `logos/NOMBRECANAL.png`, TTS Mistral (`MISTRAL_TTS_VOICE_ID`, p. ej. `mi voz`), concat ffmpeg al inicio del clip tras verificación. Variables: `INTRO_CLIP_ENABLED`, `LOGOS_CANAL_DIR`, `MISTRAL_TTS_MODEL`. Checkbox en sidebar.

- [2026-05-19] REFACTOR: `VIDEOAnalizer3.py` → `appMonitoreo.py`
  - Renombrado el script principal en grabaciones; actualizados `.bat`, docs, reglas Cursor e import en `_enviar_prueba_dual_r2_cloudinary.py`. Ejecutar: `streamlit run appMonitoreo.py`.

- [2026-05-18 23:00] DOC: aislamiento bidireccional grabaciones ↔ radioAnalizer
  - Reglas Cursor en ambos proyectos, `.cursorignore`, `PROYECTO.md`, workspaces `.code-workspace`. Prohibición explícita de editar el proyecto hermano desde el agente.

- [2026-05-18 22:30] DOC: aislamiento de `radioAnalizer`
  - Regla Cursor `.cursor/rules/grabaciones-isolation.mdc`, `AGENTS.md`, `grabaciones.code-workspace` y `.vscode/settings.json`. Abrir solo la carpeta `grabaciones` en Cursor; no mezclar con `Desktop\radioAnalizer`.

- [2026-05-18 22:00] FEAT: `appMonitoreo.py` — informe general implementado
  - `informe_general.md` en `%USERPROFILE%\Desktop\informes` (o `INFORMES_GENERAL_DIR` / `INFORME_GENERAL_MD`). Coincidencias al enviar (`generar_analisishoy_md`), tangenciales al cierre (`append_analisishoy_menciones_tangenciales`) y reporte de sesión con ambos (`generar_md_sesion_coincidencias`).

- [2026-04-23 14:00] FEAT: informe general MD (coincidencias + tangenciales)
  - Un solo `informe_general.md` acumula **coincidencias** y **tangenciales** (sin transcripción). Por defecto: carpeta `informes` en el **Escritorio** del usuario (`%USERPROFILE%\Desktop\informes`). Variable opcional `INFORMES_GENERAL_DIR` en entorno. Coincidencias: al validar envío. Tangenciales: al cierre del ciclo (tras Drive si aplica).

- [2026-04-23 14:30] MOD: informe general — ruta por defecto
  - Ruta fijada a Escritorio/informes (resuelve con `Path.home()`); creación de carpeta al cargar el módulo.

- [2026-04-23 16:00] MOD: Bunny — activación por `.env` y mensajes en UI
  - Sin `bunny_config.json`: si en entorno hay `BUNNY_STORAGE_API_KEY` (o `BUNNY_API_KEY`), `BUNNY_STORAGE_ZONE` y `BUNNY_STORAGE_PUBLIC_BASE`, se activa solo el subida (`enabled` True) salvo `BUNNY_STORAGE_ENABLED=false`. Con JSON: `BUNNY_STORAGE_ENABLED`, `BUNNY_STORAGE_ZONE` y siguen rellenando desde `.env`. La subida en coincidencias exige también `cdn_base_url`; en Streamlit se muestra la URL al subir o un caption con lo que falta (o si no hay clip).

- [2026-04-22 23:30] MOD: Bunny — correo Brevo y activación JSON sin `enabled`
  - `enviar_coincidencia_inmediata` pasa al correo `video_url_cloudinary or video_url_bunny` (antes solo Cloudinary, el mail quedaba sin enlace si solo funcionaba Bunny). `enviar_coincidencia_a_cliente` usa `video_url_correo or video_url` para Brevo. `enviar_correo_brevo` incluye URL Bunny en plantilla, subida Bunny cuando toca, y fallback a Bunny si Cloudinary falla o no está configurado. `cargar_bunny_config`: si el JSON no define la clave `enabled` pero hay AccessKey + zona + Pull Zone (p. ej. key en `.env`), se activa salvo `BUNNY_STORAGE_ENABLED=false`; `enabled: false` explícito en JSON sigue apagando.

- [2026-04-22 23:55] MOD: Bunny Pull Zone — 401 y firmas de URL
  - Si el CDN devuelve `401 Unauthorized` en `*.b-cdn.net`, suele ser **Token authentication** activo: desactivarlo en el panel o poner en `.env` `BUNNY_CDN_TOKEN_KEY` (clave del Pull Zone) y `BUNNY_CDN_TOKEN_AUTH_MODE=basic` o `advanced`. La URL `storage.bunnycdn.com/...` no es navegable (API de storage). `bunny_storage.public_delivery_url` acepta firma opcional; `cargar_bunny_config` / `subir_video_bunny` leen `cdn_token_*` y variables `BUNNY_CDN_TOKEN_*`. `_bunny_test_upload.py` imprime URL sin firma y firmada si hay token en entorno.

- [2026-04-22 23:58] FILE: `_enviar_correo_prueba_bunny.py`
  - Script puntual: envía por Brevo (desde `brevo_config.json`) un correo a `autosemana@gmail.com` con plantilla HTML del analizador, enlace Pull Zone del clip de prueba y nota sobre Storage API / tokens.

- [2026-04-22 20:00] MOD: Bunny → Cloudflare R2
  - Eliminado Bunny (`bunny_storage.py`, scripts de prueba). Añadidos `r2_storage.py` (boto3), bloque `r2` por cliente, subida dual Cloudinary+R2, plantilla de correo con enlace principal y copia R2, `enviar_correo_brevo` con `upload_video_via` `cloudinary`|`r2`, fallback R2 tras Cloudinary y copia R2 tras éxito Cloudinary. Dependencia `boto3`; script `upload_r2.py` para pruebas.

- [2026-05-06] DOC: README — Sheets TV, Drive Intrant/Edesur, tangenciales y momento mención en correos (sin marca de API en el cuerpo del mail).

- [2026-04-28 16:00] FEAT: preferencia CDN en sidebar (coincidencias)
  - Radio en barra lateral: subir clips a ambos almacenes, solo Cloudinary o solo R2. Persistencia en `videos procesados/preferencia_cdn_coincidencias.json`; `enviar_coincidencia_inmediata` y la subida previa al envío respetan la opción; sigue aplicando `enabled` por cliente en `clientes_config.json`.

- [2026-05-06] MOD: R2 igual que Cloudinary en clip y correos
  - Subida del clip a R2 junto a Cloudinary cuando aplica tras generar el clip; esa URL (`video_url_r2_precargada`) evita segunda subida en `enviar_coincidencia_inmediata`. R2 solo se desactiva con `r2.enabled: false`; plantillas cliente nuevas pueden llevar `r2.enabled: true`. Google Sheets (`url_gs`) usa Cloudinary o, si falta, R2. Ver `appMonitoreo.py` en esta carpeta.

- [2026-05-26 12:00] MOD: Gemini — migración a 3.5 Flash
  - Reemplazado `gemini-3-pro-preview` (404, modelo retirado) por `gemini-3.5-flash` vía constante `GEMINI_MODEL` en `determinar_segmento_inteligente_gemini` y `extraer_idea_general_segmento_gemini`.

- [2026-05-26 14:00] FEAT: DeepSeek como fallback IA tras fallo Gemini/GPT-4o
  - Cadena: Gemini → GPT-4o → DeepSeek → método tradicional (segmento) o resumen simple (idea). Funciones `determinar_segmento_inteligente_deepseek` y `extraer_idea_general_segmento_deepseek`; requiere `DEEPSEEK_API_KEY`.

- [2026-05-26 16:00] MOD: aviso ffprobe — distingue .env OK vs MP4 problemático
  - Si `FFMPEG_BIN` resuelve ffprobe, el warning apunta al segmento `_seg*` incompleto/en grabación, no a configurar `.env` otra vez.

- [2026-05-28 10:00] FIX: informe_general.md — coincidencias y tangenciales
  - Coincidencias se registran siempre en `Desktop/informes/informe_general.md` (también si dedupe omite reenvío). Tangenciales se anexan al detectarse (como Brevo/Sheets), no solo al cierre de ciclo.

- [2026-05-29 09:10] FIX: informe_general — registro temprano de coincidencias
  - `registrar_coincidencia_informe_general` se ejecuta en `enviar_coincidencia_inmediata` **antes** de Telegram/dedupe/Analisishoy; ya no depende del paso 7 ni de que `generar_analisishoy_md` tenga éxito.

- [2026-05-29 12:00] MOD: informe video en archivo separado
  - Por defecto y en `.env`: `Desktop/informes/informe_general_video.md` (solo grabaciones). `informe_general.md` queda para Radio Analyzer (~32k líneas; el editor a veces no muestra el final).

- [2026-07-08 21:00] FIX: Intrant — vídeos a Telegram
  - Términos Intrant (`intrant`, `milton morrison`, `morrison`, etc.) son **prioritarios**: la IA ya no bloquea el clip por tangencial/relevancia baja. Búsqueda sin tildes (`intrán` → `intrant`). Tangenciales de otros términos también notifican Telegram (subida R2 + vídeo). Corregido `parse_mode` nulo en `enviar_video_telegram_url`.

- [2026-07-08 21:10] FIX: Telegram — vídeo obligatorio siempre
  - `TELEGRAM_VIDEO_OBLIGATORIO=True`: antes de enviar se sube a R2/Cloudinary/Bunny si falta URL; reintentos en cascada (URL → local+CDN → directo → R2 otra vez). Si el vídeo falla, el envío Telegram completo se marca como error (no basta con texto).

- [2026-07-08 21:15] MOD: intran como variante válida de intrant
  - `normalizar_termino_canonico_monitor()` mapea intran/intrán/in tran/intrans → intrant. Búsqueda con `\bintran(?:t)?\b`. Añadido `intran` en términos Intrant y dedupe por término canónico.

- [2026-07-11 00:25] MOD: clips anclados al término (poco antes / más después)
  - El recorte ya no rellena con el bloque previo del programa. Prompt + `_expandir_segmento_anclado_al_termino`: máx. ~15s antes de la mención; el resto de los 90s va después. Evita casos tipo Morrison/Intrant con minutos de tema ajeno antes de la frase útil.

- [2026-07-11 00:30] MOD: idea del término es lo esencial en el recorte
  - Regla #1 del prompt: capturar la idea completa (quién/qué/efecto). Tope previo suavizado (~25s) solo contra relleno ajeno; se alarga el FIN si hace falta cerrar la idea.

- [2026-07-11 00:35] FIX: nunca cortar el cierre de la idea al ajustar duración
  - Al acortar a 90s se recorta el ANTES; se conserva el FIN propuesto. Prompt: «NUNCA cortes la idea a mitad».

- [2026-07-14 15:00] FIX: Google Sheets EDESUR — columnas y fechas
  - Hoja 1 usa `fecha | periodista | titulo | texto | medio | sentimiento | url | fuente` (sin `#`). `construir_fila_google_sheet_cliente` y rangos `A:H`. Append con `RAW` para que `DD/MM/YYYY` no se convierta en índice/serial. Backfill de hoy (coincidencias + tangenciales) desde Analisishoy.

- [2026-07-14 15:15] FIX: Sheets — nunca índice en columna fecha
  - `append_fila_google_sheet` ya no antepone `#`. Rechaza filas si col A no es `DD/MM/YYYY`. Sheet EDESUR reescrito con fechas reales.

- [2026-07-14 15:20] FIX: Sheets EDESUR + Intrant — fecha siempre texto
  - `_normalizar_fecha_sheet_ddmmyyyy` convierte seriales/índices a `DD/MM/YYYY`. Append ignora `incluir_indice`. Intrant: 436 fechas serial→texto. EDESUR: 15 filas OK. Reiniciar Streamlit obligatorio.

- [2026-07-14 21:30] FIX: UI — `clientes_config.json` borrado por BOM
  - Un UTF-8 BOM hizo fallar `cargar_clientes` → la app regeneró solo EDESUR+Presidencia (sin Intrant/Sheets/términos). Restaurado desde historial (4 clientes). Carga con `utf-8-sig`; `guardar_clientes` rechaza overwrite peligroso.

- [2026-07-14 21:35] FIX: reparación completa post-BOM
  - `.env` sin BOM; `load_dotenv(..., encoding=utf-8-sig)`. `clientes_config` 4 clientes + Sheets `A:H` + Brevo/Cloudinary desde `.env` en Presidencia. Fechas EDESUR/Intrant otra vez como texto `DD/MM/YYYY`. Reiniciar Streamlit.

- [2026-07-14 23:40] FEAT: auto-escaneo a las 06:30
  - Si la app está abierta, a las 06:30 (configurable) arranca sola la búsqueda continua una vez al día. Sidebar: «Auto-escaneo programado». `.env`: `AUTO_ESCANEO_ENABLED`, `AUTO_ESCANEO_HORA`, `AUTO_ESCANEO_VENTANA_MIN`.

- [2026-07-14 23:45] FEAT: reloj de auto-escaneo
  - Panel con hora actual, hora de inicio (06:30 a.m.) y cuenta atrás HH:MM:SS; se actualiza ~cada 15s con la app abierta.

- [2026-07-16 20:45] FIX: Brevo — correos al terminar cada video
  - Antes solo se enviaban al cierre de todo el lote (si el ciclo seguía, no salían). Ahora `flush_cola_brevo_emision` corre al acabar cada video con coincidencias, y también vacía cola pendiente al iniciar un ciclo nuevo.

- [2026-07-16 20:55] FIX: Brevo otra vez inmediato en coincidencias
  - EDESUR/Intrant ya no “encolan” el correo: se envía en el mismo paso que Telegram. Si SMTP falla, ahí sí queda en cola de reintento.

- [2026-07-16 21:00] DOCS: `README_envios.md`
  - Lógica oficial de envíos (inmediato vs cierre de ciclo, destinos por cliente, dedupe, Brevo).

- [2026-07-17 00:15] FEAT: versión Next.js del panel (`app-monitoreo-next/`)
  - UI paralela a Streamlit sin tocar `appMonitoreo.py`: entidades, clips, análisis, auto-escaneo. Pipeline de envíos sigue en Python.

- [2026-07-17 00:20] FEAT: Next.js funcional con worker Python
  - `worker_next_monitoreo.py` ejecuta `buscar_y_procesar_videos` headless; Next arranca/detiene el worker y muestra logs en vivo.

- [2026-07-17 00:25] FEAT: Next standalone sin Streamlit
  - Al abrir Next (BAT o `npm run dev`) auto-arranca el worker; auto-escaneo 06:30 corre en el servidor. Streamlit ya no es requisito.

- [2026-07-17 12:50] FEAT: Teleantillas — escaneo solo mañana
  - Solo procesa lun–vie 05:00–07:00 Revista 110, 07:00–09:00 Una nueva mañana, 09:00–10:00 Uno + Uno (`programacion_tv.json` + filtro en escaneo).

- [2026-07-17 12:55] UI: “Video fuera de horario”
  - Si Teleantillas (u otro canal con filtro) está fuera del slot, la UI lo muestra y lo salta sin procesar.

- [2026-07-17 12:52] FEAT: Telemicro — escaneo solo mañana
  - Solo lun–vie 05:00–06:00 La opción de la mañana, 06:00–08:00 Matinal; fuera de horario se salta con el mismo aviso en UI.

- [2026-07-17 14:09] FEAT: mover origen a `procesados/`
  - Tras analizar un video, el archivo original pasa a una carpeta `procesados` en el mismo directorio (p. ej. `Teleantillas/procesados/`). El escaneo ignora esas carpetas para no reprocesarlos.

- [2026-07-19 09:39] FEAT: fin de semana sin filtro de horario
  - Sábado y domingo (fecha del video): se procesan todos los videos, sin `escaneo_solo_horarios`. Lun–vie sigue con la parrilla.

- [2026-07-19 10:25] FIX: domingo no encontraba videos
  - Hoy fin de semana → sin filtro (aunque la app no se hubiera reiniciado con la regla anterior). Mejor alias de canales (`Acento_TV`, `CDN_En_Vivo`, `Telemicro_Canal_5`, etc.).

- [2026-07-23 19:15] FEAT: borrado permanente sin match / fuera de horario
  - Sin coincidencias ni tangenciales → `os.remove` (no Papelera) + audios del mismo nombre.
  - Fuera de horario (lun–vie) → mismo borrado, con aviso en UI y resumen al cierre del ciclo.
  - Solo tangenciales o con coincidencias → se mueven a `procesados/` (no se borran).

- [2026-07-23 19:30] SEC: candado de borrado solo en `videos procesados`

- [2026-07-27 09:15] FEAT: videos en uso / grabando → reintento fin de ciclo
  - Si ffmpeg o el acceso al archivo falla por **archivo en uso** (WinError 32, permission denied, etc.), se anota en UI y se **reintenta al final del ciclo** sin mandarlo a `archivos_fallidos`.
  - Restauradas funciones de horario, mover/borrar origen y fin de semana sin filtro (revertidas por accidento).

- [2026-07-27 09:20] DOCS: medios sin horario de escaneo
  - Canales **sin** `escaneo_solo_horarios` en `programacion_tv.json` (p. ej. CDN, TRA, Intrant) procesan **todos** los videos, a cualquier hora entre semana. Solo los que tienen parrilla de escaneo quedan filtrados.
  - `borrar_video_origen_permanente` rechaza cualquier ruta fuera de `CARPETA_VIDEOS` y solo permite extensiones de media.

- [2026-07-29 11:50] FIX: Analisishoy dual-write restaurado + protección borrado
  - `Analisishoy_YYYYMMDD.md` se escribe otra vez en **videos procesados** y espejo en **Desktop/informes** (se había perdido tras el revert).
  - Al iniciar cada ciclo se crea el archivo del día aunque no haya coincidencias.
  - El borrado permanente **nunca** toca `.md` ni archivos `Analisishoy*`.

- [2026-07-30 12:35] FEAT: escaneo mediodía 12:00–15:00 en todos los canales filtrados
  - Añadido bloque `12:00–15:00` a `escaneo_solo_horarios` (Teleantillas, Telemicro, Antena Latina, Color Vision, Telesistema, Telecentro, Digital 15, Teleuniverso, Acento, Canal Seis, Telemedios). Antes solo pasaban franjas de mañana (y pocos slots a las 14h), por eso se veían muchos videos y solo se procesaban unos pocos.

- [2026-07-30 21:40] FEAT: escaneo noche 21:00–00:00 en todos los canales filtrados
  - Añadido bloque `21:00–24:00` (9 pm a medianoche) a la parrilla de escaneo. Corregido `_hora_en_slot` para aceptar `fin: 24:00`.


