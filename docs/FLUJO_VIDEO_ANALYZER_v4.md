# Video Analyzer (v4) — Funcionamiento y flujo de coincidencias

**Línea de documentación: v4** · Archivo de referencia para `appMonitoreo.py` (Streamlit). Describe qué hace el código, qué requisitos tiene y **paso a paso** qué ocurre cuando se encuentra una **coincidencia fuerte** (alerta con clip).

---

## 1. Qué es el analizador

- Una **aplicación Streamlit** concentrada principalmente en `appMonitoreo.py`.
- Analiza videos de una **carpeta local**, **transcribe**, **busca términos** asociados a **clientes**, usa **IA** (p. ej. Gemini) para decidir **segmento del clip** y **relevancia**, genera **clips** con **FFmpeg** y **envía** alertas por los canales configurados (Telegram, Brevo, webhooks, Drive, Supabase, Google Sheets, etc.).

**Todo el flujo de negocio vive en ese proyecto**; no dependes de otro repositorio para ejecutar el analizador.

---

## 2. Qué sí necesita “desde fuera” (requisitos normales)

No es un segundo programa, pero toda app real necesita:

| Tipo | Qué es |
|------|--------|
| **Entorno** | Python + dependencias (`requirements.txt`). |
| **Sistema** | **FFmpeg** accesible en el PATH para recortar video. |
| **Configuración** | `clientes_config.json`, `terminos_guardados.json`, y a veces JSON auxiliares (p. ej. Bunny). |
| **Secretos / APIs** | Archivo **`.env`** o variables: Brevo, Telegram, Cloudinary, R2, Supabase, claves de Gemini/OpenAI, etc. Sin credenciales, el canal correspondiente no puede conectarse. |

---

## 3. Multi-cliente

- Cada **término** enlaza a un **`cliente_id`**.
- El sistema usa **`obtener_cliente_por_termino`** para saber a qué entidad notificar y qué credenciales/carpetas usar.

---

## 4. Flujo cuando encuentra una coincidencia “fuerte” (con clip de alerta)

Orden aproximado tal como ocurre en el bucle principal de procesamiento (p. ej. `buscar_y_procesar_videos`).

### 4.1 Transcripción y localización

- El video ya fue transcrito (o se usa transcripción en segmentos con timestamps).
- Se detecta el **término** en un instante (**timestamp**) y se obtiene **contexto** alrededor.

### 4.2 Control de duplicados en la misma pasada

- Evita procesar dos veces el mismo par término + instante en el mismo archivo cuando aplica la lógica de lista interna.

### 4.3 IA: segmento del clip (Gemini)

- Se llama a **`determinar_segmento_inteligente_gemini`**: decide **inicio** y **fin** del fragmento a recortar.
- **Si el modelo indica tangencial** (devuelve `None`): **no** sigue el camino de coincidencia con clip; entra en el flujo de **tangenciales** (videoscheck opcional, Drive tangencial, lista de tangenciales, correos tangenciales, etc.) y **no genera** la alerta “fuerte” para ese caso.

### 4.4 Ajuste a la duración del archivo

- Se limita el segmento para no salirse del final del video.
- Opcionalmente se **expande** la duración del clip hasta un mínimo configurado (p. ej. 90 s) si la IA devolvió un tramo más corto.

### 4.5 Generación del clip (FFmpeg)

- Se genera un archivo **`.mp4`** en la subcarpeta del término.

### 4.6 IA: idea del segmento y relevancia (Gemini / fallback)

- Con **`extraer_idea_general_segmento_gemini`** se obtiene resumen, relevancia, si es **relevante** o no.
- Si la relevancia es **baja** o no es relevante, y el término **no es prioritario**, el sistema puede tratar el caso como **tangencial**: eliminar el clip generado y seguir el flujo tangencial.
- Si **sigue adelante**, continúa como **coincidencia válida** para alerta.

### 4.7 Verificación posterior del clip (según reglas)

- Puede transcribir audio del clip para comprobar que el **término** aparece en el vídeo recortado; si falla la verificación y no aplica excepción por término prioritario, puede descartar el clip.

### 4.8 Subida a CDNs (mismo ciclo del clip)

- Según configuración del cliente y variables de entorno, puede subir el clip a **Cloudinary**, **Bunny** y **Cloudflare R2** (y reutilizar URL en el envío para no subir dos veces).

### 4.9 Duración mínima para enviar video

- Si existe un umbral mínimo de duración del clip para **adjuntar/enviar** vídeo, un clip demasiado corto puede hacer que el envío vaya **solo con texto** en algunos canales (sin adjunto de clip), según la lógica actual.

### 4.10 Envío inmediato: `enviar_coincidencia_inmediata`

- Resuelve el **cliente** asociado al término.
- Completa o reutiliza URLs (Cloudinary, Bunny, R2).
- Llama a **`enviar_coincidencia_a_cliente`** con resumen, transcripción, URLs de vídeo, etc.

### 4.11 `enviar_coincidencia_a_cliente` — orquestación por cliente

1. **Antiduplicados (dedupe):** si esa coincidencia ya fue notificada recientemente (misma huella cliente/término/tiempo/contexto), **no reenvía**.
2. **Renombrado del clip** con prefijo tipo `ccTérmino_...` para identificación.
3. Construcción del **resumen** y del **cuerpo** para correo y otros canales.
4. Por cada destino **habilitado** en `clientes_config.json` para ese cliente:
   - **Telegram**
   - **Webhook HTTP**
   - **Brevo** (HTML + texto plano, enlaces a vídeo)
   - **Google Drive** (archivo de texto + video)
   - **Supabase**
   - **Google Sheets** (fila de seguimiento, si está configurado)
5. Actualización de **Analisishoy** (markdown en disco).
6. Si hubo al menos un envío exitoso, **registro en dedupe** para evitar repeticiones.

### 4.12 Cierre en el mismo video

- Se guardan transcripciones/contexto en archivos auxiliares del clip.
- Se añade la coincidencia a las listas de la sesión y se continúa con el **siguiente término** o el **siguiente archivo**.

---

## 5. Resumen en una frase

**Encuentra el término → la IA valida segmento y relevancia → se recorta el clip → se sube a CDNs si aplica → se envía de inmediato a los canales del cliente → se deja rastro (MD, Sheets, Supabase, etc.) y se evitan duplicados.**

---

## 6. Tangenciales (contraste breve)

Si en el paso de **segmento** o de **relevancia** el sistema clasifica el caso como **tangencial**, **no** sigue el flujo anterior de alerta con clip completo: acumula ítems, puede copiar a `videoscheck`, subir a **Drive tangenciales**, enviar **correo inmediato** Brevo y al **fin del ciclo** un **resumen** con todas las tangenciales (y opcionalmente DeepSeek para enriquecer textos). Ese flujo está detallado en el mismo código (`crear_item_tangencial`, `enviar_brevo_tangencial_inmediato`, `enviar_correos_tangenciales_fin_ciclo`, etc.).

---

## 7. Mantenimiento de este documento (v4)

Si cambia el orden de llamadas o el nombre de funciones centrales, conviene actualizar las secciones 4 y 6 para que sigan alineadas con `appMonitoreo.py`. La versión **v4** de esta documentación puede divergir de versiones anteriores del README u otros MD históricos.

*Generado como referencia de flujo; no sustituye leer el código para casos límite.*
