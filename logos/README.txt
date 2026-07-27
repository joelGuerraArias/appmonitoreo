Logos de canales para el intro de clips de coincidencia
======================================================

Nombre del archivo = prefijo del canal en el nombre del video de emision.

Ejemplos:
  Video:  TELEANTILLAS_720p_2025-09-15_07-37-25.mp4
  Logo:   TELEANTILLAS.png  (tambien .jpg / .webp)

La carpeta por defecto es grabaciones/logos (variable LOGOS_CANAL_DIR en .env).

Si no hay logo del canal, se usa el logo de la entidad (Edesur / Intrant / MINERD)
segun el termino detectado. Opcional: INTRO_FALLBACK_LOGO en .env.

Nombres tipo clip: ..._2026-05-18_clip_26.mp4 — el sistema extrae el canal
(El_Matutino, TELEANTILLAS, etc.) aunque no traigan hora en el nombre.

Si no hay ningun logo, el clip se envia sin intro (no se bloquea el flujo).

TTS Mistral (.env):
  MISTRAL_API_KEY=...
  MISTRAL_TTS_VOICE_ID=mi voz
  (puede ser el nombre de la voz o su UUID; la API exige UUID y el codigo lo resuelve solo)
