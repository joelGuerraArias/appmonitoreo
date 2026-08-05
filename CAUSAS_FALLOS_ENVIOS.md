# Por qué fallan tanto los envíos (Omitido / sin correo)

## Qué veías en la UI

```
⏭️ Omitido — telegram.enabled es falso
⏭️ Omitido — brevo.enabled es falso
⏭️ Omitido — google_drive.enabled es falso
…
```

## Causas reales (en orden de frecuencia)

1. **Cursor vacía archivos críticos** (`.env`, `appMonitoreo.py`, `clientes_config.json`) con *Undo Create Diff* o guardando pestañas vacías.
2. **Blindaje “tonto” (ya corregido):** trataba como sano un JSON Intrant *sin* API key y con `enabled=false`, y lo copiaba a `backups/clientes_config_latest.json`. La siguiente restauración recuperaba basura → todo Omitido otra vez.
3. **Streamlit sin reiniciar:** el proceso seguía horas/días con la config vieja en memoria aunque el disco ya estuviera bien.
4. **ReadOnly en `clientes_config.json`:** impedía que la app guardara canales reactivados (`Permission denied`).

## Qué quedó arreglado (2026-08-04)

| Fix | Efecto |
|-----|--------|
| Intrant sin Brevo/Telegram usable = **BAD** | Se restaura desde backup bueno |
| `clientes_config_intrant_golden.json` | Backup “dorado” que no se pisa con basura |
| Preferir golden / pre-v5.5 al restaurar | No reinyectar latest envenenado |
| `clientes_config` **sin** ReadOnly | La app puede persistir canales ON |
| Recarga fresca en cada envío | No depende de sesión vieja |
| `logs/integridad_causas.log` | Deja escrito *por qué* se restauró |
| Analisishoy obligatorio + alerta correo/UI | Aviso si el MD del día no se crea |

## Si vuelve a pasar

1. Mira `logs/integridad_causas.log` (última causa).
2. Ejecuta: `venv_new\Scripts\python.exe proteger_integridad.py`
3. Reinicia la app (cierra puerto 8501 y vuelve a abrir **App Monitoreo**).
4. En el editor: si `.env` / `clientes_config.json` salen vacíos → **cerrar sin guardar**.
