"use client";

import type { AnalisisClips } from "@/lib/types";

export function AnalisisPanel({ analisis }: { analisis: AnalisisClips | null }) {
  if (!analisis) {
    return <p className="text-sm text-zinc-400">Cargando análisis…</p>;
  }

  const max = Math.max(...analisis.por_termino.map((x) => x.cantidad), 1);

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total de clips", String(analisis.total)],
          ["Términos únicos", String(analisis.terminos_unicos)],
          ["Clips de hoy", String(analisis.clips_hoy)],
          ["Tamaño total", `${analisis.tamano_total_mb} MB`],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-xl border border-white/10 bg-white/5 px-4 py-3"
          >
            <p className="text-xs text-zinc-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div>
        <h3 className="text-sm font-medium text-white">
          Distribución por términos
        </h3>
        <ul className="mt-3 space-y-2">
          {analisis.por_termino.slice(0, 20).map((row) => (
            <li key={row.termino} className="flex items-center gap-3 text-sm">
              <span className="w-28 truncate text-zinc-300">{row.termino}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full bg-cyan-500"
                  style={{ width: `${(row.cantidad / max) * 100}%` }}
                />
              </div>
              <span className="w-8 text-right text-zinc-400">{row.cantidad}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
