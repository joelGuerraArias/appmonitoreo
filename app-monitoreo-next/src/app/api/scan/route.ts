import { NextResponse } from "next/server";
import { listarClientesPublicos } from "@/lib/clientes";
import { patchSession, getSession } from "@/lib/session";
import { bootstrapStandalone } from "@/lib/bootstrap";
import {
  isWorkerProcessAlive,
  readWorkerStatus,
  requestWorkerStop,
  startWorker,
} from "@/lib/worker";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function syncSessionFromWorker() {
  const w = readWorkerStatus();
  const alive = isWorkerProcessAlive() || Boolean(w.running);
  return patchSession({
    running: alive && w.phase !== "done" && w.phase !== "stopped",
    videos_encontrados: w.videos_encontrados ?? getSession().videos_encontrados,
    videos_procesados: w.videos_procesados ?? getSession().videos_procesados,
    clips_generados: w.clips_generados ?? getSession().clips_generados,
    loop_ciclo_numero: w.loop_ciclo_numero ?? getSession().loop_ciclo_numero,
    mistral_total_transcripciones:
      w.mistral_total_transcripciones ??
      getSession().mistral_total_transcripciones,
    mistral_total_audio_seconds:
      w.mistral_total_audio_seconds ?? getSession().mistral_total_audio_seconds,
    mistral_total_tokens:
      w.mistral_total_tokens ?? getSession().mistral_total_tokens,
    last_scan_message: w.message || getSession().last_scan_message,
    alertas_envio: Array.isArray(w.alertas_envio)
      ? (w.alertas_envio as ReturnType<typeof getSession>["alertas_envio"])
      : getSession().alertas_envio,
  });
}

export async function GET() {
  bootstrapStandalone();
  const session = syncSessionFromWorker();
  return NextResponse.json({
    ok: true,
    session,
    worker: readWorkerStatus(),
    alive: isWorkerProcessAlive(),
  });
}

export async function POST(req: Request) {
  try {
    bootstrapStandalone();
    const body = (await req.json()) as {
      action?: string;
      mode?: "once" | "loop";
    };
    const action = body.action || "status";

    if (action === "status") {
      const session = syncSessionFromWorker();
      return NextResponse.json({
        ok: true,
        session,
        worker: readWorkerStatus(),
        alive: isWorkerProcessAlive(),
      });
    }

    if (action === "stop") {
      const worker = requestWorkerStop();
      const session = patchSession({
        running: false,
        last_scan_message: "Stop solicitado — el worker terminará el ciclo actual",
      });
      return NextResponse.json({ ok: true, session, worker });
    }

    if (action === "start" || action === "once" || action === "loop") {
      const activos = listarClientesPublicos().filter(
        (c) => c.activo && c.incluir_en_analisis,
      );
      if (activos.length === 0) {
        return NextResponse.json(
          {
            ok: false,
            error:
              "Ninguna entidad con análisis activo. Activa al menos una en el sidebar.",
            session: getSession(),
            worker: readWorkerStatus(),
          },
          { status: 400 },
        );
      }

      const mode: "once" | "loop" =
        action === "once"
          ? "once"
          : action === "loop"
            ? "loop"
            : body.mode === "once"
              ? "once"
              : "loop";

      const started = startWorker(mode);
      if (!started.ok) {
        return NextResponse.json(
          {
            ok: false,
            error: started.error,
            session: getSession(),
            worker: started.status,
          },
          { status: 409 },
        );
      }

      const session = patchSession({
        running: true,
        last_scan_message: `Worker Python (${mode}) iniciado — entidades: ${activos
          .map((c) => c.nombre)
          .join(", ")}`,
      });

      return NextResponse.json({
        ok: true,
        session,
        worker: started.status,
        alive: true,
      });
    }

    return NextResponse.json(
      { ok: false, error: `Acción desconocida: ${action}` },
      { status: 400 },
    );
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
