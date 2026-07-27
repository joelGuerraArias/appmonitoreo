import fs from "fs";
import { Readable } from "stream";
import { NextResponse } from "next/server";
import { resolverClipPath } from "@/lib/clips";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function toWebStream(nodeStream: fs.ReadStream): ReadableStream {
  return Readable.toWeb(nodeStream) as ReadableStream;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const rel = searchParams.get("path") || "";
  const full = resolverClipPath(rel);
  if (!full) {
    return NextResponse.json({ ok: false, error: "Clip no encontrado" }, { status: 404 });
  }

  const stat = fs.statSync(full);
  const range = req.headers.get("range");
  const contentType = "video/mp4";

  if (range) {
    const m = /bytes=(\d+)-(\d*)/.exec(range);
    if (!m) {
      return new NextResponse("Invalid Range", { status: 416 });
    }
    const start = Number(m[1]);
    const end = m[2]
      ? Number(m[2])
      : Math.min(start + 1024 * 1024 - 1, stat.size - 1);
    if (start >= stat.size || end >= stat.size) {
      return new NextResponse("Range Not Satisfiable", {
        status: 416,
        headers: { "Content-Range": `bytes */${stat.size}` },
      });
    }
    const chunkSize = end - start + 1;
    const stream = fs.createReadStream(full, { start, end });
    return new NextResponse(toWebStream(stream), {
      status: 206,
      headers: {
        "Content-Range": `bytes ${start}-${end}/${stat.size}`,
        "Accept-Ranges": "bytes",
        "Content-Length": String(chunkSize),
        "Content-Type": contentType,
      },
    });
  }

  const stream = fs.createReadStream(full);
  return new NextResponse(toWebStream(stream), {
    status: 200,
    headers: {
      "Content-Length": String(stat.size),
      "Content-Type": contentType,
      "Accept-Ranges": "bytes",
    },
  });
}
