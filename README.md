# Proyecto grabaciones — Video Analyzer

## 📌 Cambios automáticos

- [2026-08-12 08:25] FEAT: Video Analyzer v5.8
  - Clips por idea (30–90s): cadena Kimi→DeepSeek→Gemini→GPT; UI muestra idea_central/texto_idea antes del corte; sin expansión ciega a 90s; mínimo de envío 30s. Arrancador con blindaje si `appMonitoreo.py` queda vacío. Next: bootstrap solo en instrumentation.

---

- [2026-08-05 09:17] FEAT: Video Analyzer v5.7
  - Misma base v5.6 + corrección ortográfica en transcripciones (avinader→abinader) y `abinader` fuera de la lista de búsqueda.

---

- [2026-08-05 08:20] FEAT: Video Analyzer v5.6
  - Normalización abinader/digesett, espera vacía 6 min, Analisishoy obligatorio, checklist de canales, blindaje Intrant, enlaces Cloudinary+R2 en correo.

---

- [2026-08-05 08:05] MOD: normalizar términos abinader / digesett
  - Canónicos: `abinader` (aliases avinader, aminader) y `digesett` (aliases zed, DGC, digest, digeset). Reemplaza digest/digeset en la lista Intrant.

---

- [2026-08-05 01:12] MOD: espera sin videos nuevos → 6 min
  - El re-escaneo en vacío (`intervalo_loop_vacio`) queda en 360 s; migra solos los defaults previos de 120 s o 600 s.

---

- [2026-08-04 07:35] FEAT: Analisishoy obligatorio al cerrar ciclo
  - Ahora se crea o actualiza `Analisishoy_YYYYMMDD.md` aunque no haya coincidencias ni tangenciales, y se copia a `Desktop\informes`.

---

- [2026-08-04 07:40] FEAT: alerta correo + UI si Analisishoy no se crea
  - Si falla el Analisishoy obligatorio al cerrar ciclo, la UI muestra error rojo y se envía correo Brevo (destinatarios Intrant).

---

- [2026-08-04 07:40] FEAT: alerta correo + UI si Analisishoy no se crea
  - Si falla el Analisishoy obligatorio al cerrar ciclo, la UI muestra error rojo y se envía correo Brevo (destinatarios Intrant).

---

- [2026-08-04 08:05] MOD: restaurar canales Intrant (Brevo/Telegram/Drive/Sheets)
  - clientes_config.json tenía Brevo/Telegram/Drive apagados (por eso la coincidencia Intrant no envió nada). Se restauraron desde backup pre-v5.5.

---

- [2026-08-04 08:10] MOD: forzar canales Intrant activos
  - Si Brevo/Telegram/Drive/Sheets/Cloudinary tienen credenciales, se reactivan solos (ya no quedan en Omitido).

---

- [2026-08-04 08:06] FIX: recargar Intrant fresco en cada envío + reinicio Streamlit
  - El proceso viejo (desde anoche) seguía con canales apagados. Ahora cada envío lee clientes_config.json actual y fuerza Telegram/Brevo/Drive/Sheets/Supabase ON.

---

- [2026-08-04 08:10] FIX: blindaje ya no envenena backups Intrant
  - clientes_config con canales apagados deja de contar como sano; se usa golden backup; log en logs/integridad_causas.log. Ver CAUSAS_FALLOS_ENVIOS.md.

---

- [2026-08-04 08:15] FEAT: checklist de canales al iniciar sesión
  - Al abrir la app se listan Telegram/Brevo/Drive/Sheets/Supabase/etc. Si falta un crítico, no deja iniciar la búsqueda continua.

---

- [2026-08-04 08:20] FEAT: aviso Telegram + autosemana al verificar sesión
  - Si el checklist de canales está OK (o falla), se informa en la UI y se envía mensaje a Telegram Intrant y correo a autosemana@gmail.com (una vez por sesión).

---

- [2026-08-04 08:35] MOD: correo coincidencia — enlaces Cloudinary + R2 siempre visibles
  - Sección obligatoria en HTML/texto plano; si falta alguno, warning en UI y log.

---
