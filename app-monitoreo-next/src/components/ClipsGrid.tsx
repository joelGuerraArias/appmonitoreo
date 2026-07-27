"use client";

import { useState } from "react";
import type { ClipInfo } from "@/lib/types";

export function ClipsGrid({
  clips,
  emptyText,
}: {
  clips: ClipInfo[];
  emptyText: string;
}) {
  const [active, setActive] = useState<ClipInfo | null>(null);

  if (!clips.length) {
    return (
      <p className="rounded-xl border border-dashed border-white/15 bg-white/5 px-4 py-8 text-center text-sm text-zinc-400">
        {emptyText}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {active && (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-black">
          <video
            key={active.streamUrl}
            src={active.streamUrl}
            controls
            className="max-h-[420px] w-full"
          />
          <div className="border-t border-white/10 px-4 py-2 text-sm text-zinc-300">
            <strong className="text-white">{active.termino}</strong> ·{" "}
            {active.fecha} · {active.duracion} · {active.size_mb} MB
          </div>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {clips.map((c) => (
          <button
            key={c.relativePath}
            type="button"
            onClick={() => setActive(c)}
            className={`rounded-xl border px-3 py-3 text-left transition ${
              active?.relativePath === c.relativePath
                ? "border-cyan-400/60 bg-cyan-950/40"
                : "border-white/10 bg-white/5 hover:border-white/25"
            }`}
          >
            <p className="truncate text-sm font-medium text-white">{c.termino}</p>
            <p className="mt-1 truncate text-xs text-zinc-500">{c.filename}</p>
            <p className="mt-2 text-xs text-zinc-400">
              {c.fecha} · {c.size_mb} MB
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
