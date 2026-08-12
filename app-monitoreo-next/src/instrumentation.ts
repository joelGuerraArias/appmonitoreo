/**
 * Se ejecuta al arrancar el servidor Next (node).
 * Aquí levantamos el worker Python sin necesidad de Streamlit.
 */
let registered = false;

export async function register() {
  if (process.env.NEXT_RUNTIME === "edge") return;
  if (registered) return;
  registered = true;
  const { bootstrapStandalone } = await import("./lib/bootstrap");
  bootstrapStandalone();
}
