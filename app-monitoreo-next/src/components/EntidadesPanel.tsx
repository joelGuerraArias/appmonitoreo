"use client";

import type { ClientePublico } from "@/lib/types";

export function EntidadesPanel({
  clientes,
  onToggle,
}: {
  clientes: ClientePublico[];
  onToggle: (id: string, incluir: boolean) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-400">
        Destinos y términos por entidad (lectura segura — sin secretos en el
        navegador). Misma fuente que Streamlit:{" "}
        <code className="text-zinc-300">clientes_config.json</code>.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        {clientes.map((c) => (
          <article
            key={c.id}
            className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-transparent p-4"
            style={{ borderLeftColor: c.color, borderLeftWidth: 4 }}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-white">{c.nombre}</h3>
                <p className="text-xs text-zinc-500">id: {c.id}</p>
              </div>
              <button
                type="button"
                onClick={() => onToggle(c.id, !c.incluir_en_analisis)}
                className={`rounded-md px-3 py-1 text-xs font-semibold ${
                  c.incluir_en_analisis
                    ? "bg-emerald-600 text-white"
                    : "bg-zinc-700 text-zinc-200"
                }`}
              >
                {c.incluir_en_analisis ? "En análisis" : "Pausada"}
              </button>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(c.destinos).map(([key, d]) => (
                <span
                  key={key}
                  className={`rounded-full px-2.5 py-1 text-[11px] ${
                    d.enabled
                      ? "bg-emerald-500/15 text-emerald-300"
                      : "bg-zinc-800 text-zinc-500"
                  }`}
                  title={d.detail}
                >
                  {d.label || key}
                  {d.enabled && d.detail ? `: ${d.detail}` : ""}
                </span>
              ))}
            </div>

            <div className="mt-4">
              <p className="text-xs uppercase tracking-wide text-zinc-500">
                Términos ({c.terminos.length})
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {c.terminos.map((t) => (
                  <span
                    key={t}
                    className="rounded bg-black/30 px-2 py-0.5 text-xs text-zinc-300"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
