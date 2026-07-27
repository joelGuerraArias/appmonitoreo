import { NextResponse } from "next/server";
import { setIncluirEnAnalisis } from "@/lib/clientes";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await ctx.params;
    const body = (await req.json()) as { incluir_en_analisis?: boolean };
    if (typeof body.incluir_en_analisis !== "boolean") {
      return NextResponse.json(
        { ok: false, error: "incluir_en_analisis (boolean) requerido" },
        { status: 400 },
      );
    }
    const cliente = setIncluirEnAnalisis(id, body.incluir_en_analisis);
    return NextResponse.json({ ok: true, cliente });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
