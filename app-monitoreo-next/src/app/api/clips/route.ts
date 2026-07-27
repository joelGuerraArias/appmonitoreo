import { NextResponse } from "next/server";
import { analizarClips, buscarTodosLosClips } from "@/lib/clips";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const q = searchParams.get("q") || "";
    const dias = Number(searchParams.get("dias") || "365");
    const limit = Number(searchParams.get("limit") || "200");
    const clips = buscarTodosLosClips({
      busqueda: q,
      diasLimite: Number.isFinite(dias) ? dias : 365,
      limit: Number.isFinite(limit) ? limit : 200,
    });
    return NextResponse.json({
      ok: true,
      clips,
      analisis: analizarClips(clips),
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
