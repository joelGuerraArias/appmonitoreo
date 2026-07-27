# Lógica de envíos — Video Analyzer (`appMonitoreo.py`)

Documento de referencia: **cómo y cuándo** se notifica cada destino.
Config por cliente: `clientes_config.json`. Credenciales globales: `.env`.

---

## Regla de oro

| Tipo | Momento del envío |
|------|-------------------|
| **Coincidencia fuerte** | **Inmediato** al detectar el término (mismo ciclo del clip) |
| **Tangencial** | **Inmediato** al clasificarla (Brevo / Telegram / Sheets / informe) |
| **Resumen tangenciales** | Extra al **cierre del ciclo** (correo resumen del lote) |

Si un destino tiene `enabled: false` o la entidad tiene `incluir_en_analisis: false`, **no envía**.

---

## Flujo general

```
Video nuevo
  → Transcribir
  → Buscar términos del cliente
  → IA: segmento / clip (~90s) + CDN (R2 / Cloudinary / Bunny)
  → ¿Fuerte o tangencial?
        │
        ├─ FUERTE → enviar_coincidencia_inmediata
        │              → enviar_coincidencia_a_cliente
        │
        └─ TANGENCIAL → notificar_*_tangencial_inmediato_si
```

Función orquestadora de coincidencias: `enviar_coincidencia_a_cliente()`.

---

## Orden de envío (coincidencia fuerte)

Solo si `_destino_envio_activo(cliente, destino)`:

| # | Destino | Qué se envía | Cuándo |
|---|---------|--------------|--------|
| 1 | **Telegram** | Texto + **video obligatorio** (URL R2/Cloudinary/Bunny o local) | Inmediato |
| 2 | **Brevo** | Correo HTML + links de video (no adjunta MP4 grandes) | **Inmediato** |
| 3 | **Webhook** | JSON a Make / n8n (según switches `enviar_makecom` / `enviar_n8n`) | Inmediato |
| 4 | **Google Drive** | TXT (resumen + transcripción) + MP4 del clip | Inmediato |
| 5 | **Supabase** | Fila en `alertas_medios` | Inmediato |
| 6 | **Google Sheets** | Fila `fecha \| periodista \| titulo \| texto \| medio \| sentimiento \| url \| fuente` | Inmediato |

También se actualiza:
- `Analisishoy_YYYYMMDD.md`
- `informe_general_video.md` (y reciente)

### Brevo — detalle importante

- **Coincidencias EDESUR / Intrant / Presidencia / etc.:** envío **inmediato** con `enviar_brevo_cliente()`.
- Si SMTP **falla**, el payload se **encola** y se reintenta al terminar el video / cierre de ciclo (`flush_cola_brevo_emision`).
- La cola **no** es el camino normal: es solo reintento ante error.

> Nota histórica: hubo un cambio local (mayo 2026) que encolaba EDESUR/Intrant hasta el fin del lote. Eso rompía el envío inmediato. **Ya no aplica.** El comportamiento correcto es el de esta tabla.

---

## Tangenciales

Al detectar (sin esperar fin de lote):

1. **Brevo** — correo inmediato de esa tangencial (`enviar_brevo_tangencial_inmediato`)
2. **Telegram** — si el cliente lo tiene activo (Intrant y otros)
3. **Google Sheets** — fila con periodista `TV Tangencial`
4. **Informe general** — bloque tangencial

Al **cierre del ciclo**:
- Correo **resumen** de todas las tangenciales del lote (Brevo)
- Reintento Sheets de las que fallaron al vuelo

---

## Dedupe

Archivo: `envios_coincidencias_dedupe.json` (huella por cliente + término + instante + contexto).

- Si **todos** los canales activos ya enviaron esa huella → no se reenvía.
- Si faltó algún canal → **reenvío parcial** solo de los pendientes.

---

## Por cliente (configuración típica)

| Cliente | Telegram | Brevo | Drive | Sheets | Supabase | Webhook |
|---------|----------|-------|-------|--------|----------|---------|
| **EDESUR** (`default`) | `@edesuralertas` | Sí (lista EDESUR) | edesurVideos | Hoja Edesur | Sí | Make + n8n |
| **Intrant** | `@AlertasIntrant` | Sí | intrantvideos | Hoja Intrant | Sí | Off |
| **MINERD** | `@InabieAlertas` | Sí | minerdvideos | Hoja inabie | Sí | Off |
| **Presidencia** | Canal Intrant (heredado) | Correos propios | Off | Off | Sí | Off |

Presidencia **no** usa Drive / Sheets / Webhook aunque estén en el JSON.

---

## CDN del video (antes de Telegram / correo)

Orden habitual al generar el clip:

1. Subida **R2** (y/o Cloudinary / Bunny según cliente)
2. Telegram usa URL (vídeo obligatorio)
3. Brevo y Sheets ponen el mismo link en el mensaje / columna `url`

Sin URL ni archivo local, Telegram marca error de vídeo.

---

## Condiciones que bloquean envíos

1. `incluir_en_analisis: false` en la entidad (sidebar)
2. `activo: false` en el cliente
3. Destino con `enabled: false`
4. Dedupe completo (ya notificado)
5. Sin términos / sin coincidencia real

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `appMonitoreo.py` | Orquestación (`enviar_coincidencia_*`, tangenciales, flush) |
| `clientes_config.json` | Destinos, tokens, correos, sheet IDs por cliente |
| `.env` | API keys globales (Brevo SMTP, Google OAuth, R2, etc.) |
| `envios_coincidencias_dedupe.json` | Anti-duplicados de envío |
| `backups/config_LATEST/` | Backup de config |

---

## Checklist rápido si “no llegó el correo”

1. ¿La entidad está ON en el sidebar?
2. ¿`brevo.enabled` y lista de destinatarios en `clientes_config.json`?
3. Log: buscar `enviar_brevo_cliente` / `Correo enviado` (inmediato) vs solo `Brevo en cola` (fallo SMTP → reintento).
4. Reiniciar Streamlit tras cambiar código o JSON.
5. Revisar spam; SMTP OK se verifica con la prueba de conexiones del sidebar.
