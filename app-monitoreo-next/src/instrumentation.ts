/**
 * Se ejecuta al arrancar el servidor Next (node).
 * Aquí levantamos el worker Python sin necesidad de Streamlit.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === "edge") return;
  const { bootstrapStandalone } = await import("./lib/bootstrap");
  bootstrapStandalone();
}
