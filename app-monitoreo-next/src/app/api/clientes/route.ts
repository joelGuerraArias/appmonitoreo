import { NextResponse } from "next/server";
import { listarClientesPublicos } from "@/lib/clientes";
import { carpetaProcesados, clientesConfigPath } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const clientes = listarClientesPublicos();
    return NextResponse.json({
      ok: true,
      clientes,
      paths: {
        config: clientesConfigPath(),
        procesados: carpetaProcesados(),
      },
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
