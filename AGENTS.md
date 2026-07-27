# grabaciones — Video Analyzer

> **No mezclar con radioAnalizer.** El agente no debe editar `Desktop\radioAnalizer\` desde este workspace.

Proyecto **independiente** de `Desktop\radioAnalizer` (radio). No comparten código en runtime; solo ideas parecidas.

## Entrada principal

- **Script:** `appMonitoreo.py` (Streamlit)
- **Carpeta de trabajo:** `C:\Users\Joel Guerra\Desktop\grabaciones`
- **Salida local:** `videos procesados\` (junto al script)
- **Informe acumulativo:** `Desktop\informes\informe_general.md` (`INFORMES_GENERAL_DIR` / `INFORME_GENERAL_MD`)

## Aislamiento

- Abrir en Cursor la carpeta **`grabaciones`** (o `grabaciones.code-workspace`), no el home ni `radioAnalizer`.
- El agente debe seguir `.cursor/rules/grabaciones-isolation.mdc`.
- `../radioAnalizer/` está en `.cursorignore` (el agente no debe indexar ni editar allí).
- Ver también `PROYECTO.md` y regla `.cursor/rules/grabaciones-isolation.mdc`.

## No confundir con

| Incorrecto | Correcto (este proyecto) |
|------------|---------------------------|
| `radioAnalizer\radioAnalizer.py` | `grabaciones\appMonitoreo.py` |
| `radioAnalizer\appMonitoreo.py` | `grabaciones\appMonitoreo.py` |
| Radio Analyzer IA v2.0 | Video Analyzer IA v3.0 |
