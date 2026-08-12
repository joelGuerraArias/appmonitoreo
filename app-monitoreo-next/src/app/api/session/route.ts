import { NextResponse } from "next/server";
import { patchSession } from "@/lib/session";
import { readPrefs, writePrefs } from "@/lib/prefs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const prefs = readPrefs();
  const session = patchSession({
    loop_continuo: prefs.loop_continuo,
    intervalo_loop: prefs.intervalo_loop,
    intervalo_loop_vacio: prefs.intervalo_loop_vacio,
    auto_escaneo_enabled: prefs.auto_escaneo_enabled,
    auto_escaneo_hora: prefs.auto_escaneo_hora,
    auto_escaneo_disparado_fecha: prefs.auto_escaneo_disparado_fecha,
  });
  return NextResponse.json({
    ok: true,
    session,
    prefs: {
      auto_start_worker: prefs.auto_start_worker,
    },
  });
}

export async function PATCH(req: Request) {
  try {
    const body = (await req.json()) as Record<string, unknown>;
    const allowed = [
      "loop_continuo",
      "intervalo_loop",
      "intervalo_loop_vacio",
      "auto_escaneo_enabled",
      "auto_escaneo_hora",
      "ia_motor_sesion",
    ] as const;

    const patch: Record<string, unknown> = {};
    for (const k of allowed) {
      if (k in body) patch[k] = body[k];
    }

    const prefsPatch: Record<string, unknown> = {};
    if ("loop_continuo" in body) prefsPatch.loop_continuo = body.loop_continuo;
    if ("intervalo_loop" in body) prefsPatch.intervalo_loop = body.intervalo_loop;
    if ("intervalo_loop_vacio" in body) {
      prefsPatch.intervalo_loop_vacio = body.intervalo_loop_vacio;
    }
    if ("auto_escaneo_enabled" in body) {
      prefsPatch.auto_escaneo_enabled = body.auto_escaneo_enabled;
    }
    if ("auto_escaneo_hora" in body) {
      prefsPatch.auto_escaneo_hora = body.auto_escaneo_hora;
    }
    if ("auto_start_worker" in body) {
      prefsPatch.auto_start_worker = Boolean(body.auto_start_worker);
    }
    if (Object.keys(prefsPatch).length) writePrefs(prefsPatch);

    const session = patchSession(patch);
    return NextResponse.json({
      ok: true,
      session,
      prefs: { auto_start_worker: readPrefs().auto_start_worker },
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
