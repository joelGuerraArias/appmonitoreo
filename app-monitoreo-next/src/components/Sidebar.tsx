"use client";

import type { ClientePublico, SessionStats } from "@/lib/types";

type Props = {
  session: SessionStats;
  clientes: ClientePublico[];
  autoStartWorker: boolean;
  onToggleEntidad: (id: string, incluir: boolean) => void;
  onPatchSession: (patch: Partial<SessionStats> & { auto_start_worker?: boolean }) => void;
};

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-black/25 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-0.5 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

export function Sidebar({
  session,
  clientes,
  autoStartWorker,
  onToggleEntidad,
  onPatchSession,
}: Props) {
  const audioMin = Math.floor(session.mistral_total_audio_seconds / 60);
  const audioSeg = Math.floor(session.mistral_total_audio_seconds % 60);
  const audioDisplay =
    audioMin > 0 ? `${audioMin}m ${audioSeg}s` : `${audioSeg}s`;
  const costo = ((session.mistral_total_audio_seconds / 60) * 0.012).toFixed(4);

  return (
    <aside className="flex h-full w-full max-w-sm flex-col gap-5 overflow-y-auto border-r border-white/10 bg-[#0b1220] p-4 text-sm text-zinc-200">
      <div>
        <h2 className="text-base font-semibold text-white">Estadísticas</h2>
        <div className="mt-3 grid grid-cols-1 gap-2">
          <Metric label="Videos encontrados" value={session.videos_encontrados} />
          <Metric label="Videos procesados" value={session.videos_procesados} />
          <Metric label="Clips generados" value={session.clips_generados} />
        </div>
      </div>

      {session.alertas_envio.length > 0 && (
        <div>
          <h3 className="font-medium text-amber-300">
            Alertas de envío ({session.alertas_envio.length})
          </h3>
          <ul className="mt-2 space-y-1 text-xs text-zinc-400">
            {session.alertas_envio.slice(0, 5).map((a, i) => (
              <li key={i}>
                {a.cuando} · {a.canal} · {a.termino}
              </li>
            ))}
          </ul>
        </div>
      )}

      <section>
        <h3 className="font-semibold text-white">Análisis por entidad</h3>
        <p className="mt-1 text-xs text-zinc-500">
          Apaga una entidad para no buscar ni enviar. Se guarda en{" "}
          <code className="text-zinc-400">clientes_config.json</code>.
        </p>
        <ul className="mt-3 space-y-2">
          {clientes.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-2"
            >
              <span className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: c.color }}
                />
                {c.nombre}
              </span>
              <button
                type="button"
                onClick={() =>
                  onToggleEntidad(c.id, !c.incluir_en_analisis)
                }
                className={`rounded-md px-2 py-1 text-xs font-medium ${
                  c.incluir_en_analisis
                    ? "bg-emerald-600/80 text-white"
                    : "bg-zinc-700 text-zinc-300"
                }`}
              >
                {c.incluir_en_analisis ? "ON" : "OFF"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="font-semibold text-white">Motor IA (sesión)</h3>
        <div className="mt-2 flex flex-col gap-2">
          {(
            [
              ["gemini", "Gemini 3.5 Flash"],
              ["ollama_glm", "Ollama GLM"],
              ["ollama_kimi", "Ollama Kimi"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => onPatchSession({ ia_motor_sesion: id })}
              className={`rounded-lg px-3 py-2 text-left text-xs ${
                session.ia_motor_sesion === id
                  ? "bg-violet-600 text-white"
                  : "bg-white/5 text-zinc-300 hover:bg-white/10"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-semibold text-white">Uso Mistral / Voxtral</h3>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <Metric
            label="Transcripciones"
            value={session.mistral_total_transcripciones}
          />
          <Metric label="Audio" value={audioDisplay} />
          <Metric
            label="Tokens"
            value={session.mistral_total_tokens.toLocaleString()}
          />
          <Metric label="Costo est." value={`$${costo}`} />
        </div>
      </section>

      <section>
        <h3 className="font-semibold text-white">Arranque autónomo</h3>
        <p className="mt-1 text-xs text-zinc-500">
          No hace falta abrir Streamlit. El worker Python corre solo con Next.
        </p>
        <label className="mt-2 flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={autoStartWorker}
            onChange={(e) =>
              onPatchSession({ auto_start_worker: e.target.checked })
            }
          />
          Auto-iniciar worker al abrir Next
        </label>
      </section>

      <section>
        <h3 className="font-semibold text-white">Loop continuo</h3>
        <label className="mt-2 flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={session.loop_continuo}
            onChange={(e) =>
              onPatchSession({ loop_continuo: e.target.checked })
            }
          />
          Activar loop automático
        </label>
        {session.loop_continuo && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="text-xs text-zinc-400">
              Espera ciclos (s)
              <input
                type="number"
                min={10}
                max={600}
                step={10}
                value={session.intervalo_loop}
                onChange={(e) =>
                  onPatchSession({ intervalo_loop: Number(e.target.value) })
                }
                className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1 text-white"
              />
            </label>
            <label className="text-xs text-zinc-400">
              Sin nuevos (s)
              <input
                type="number"
                min={30}
                max={1800}
                step={30}
                value={session.intervalo_loop_vacio}
                onChange={(e) =>
                  onPatchSession({
                    intervalo_loop_vacio: Number(e.target.value),
                  })
                }
                className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1 text-white"
              />
            </label>
          </div>
        )}
        <p className="mt-2 text-xs text-zinc-500">
          Ciclos: {session.loop_ciclo_numero}
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-white">Auto-escaneo</h3>
        <label className="mt-2 flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={session.auto_escaneo_enabled}
            onChange={(e) =>
              onPatchSession({ auto_escaneo_enabled: e.target.checked })
            }
          />
          Iniciar a hora fija
        </label>
        {session.auto_escaneo_enabled && (
          <label className="mt-2 block text-xs text-zinc-400">
            Hora (HH:MM)
            <input
              type="text"
              value={session.auto_escaneo_hora}
              onChange={(e) =>
                onPatchSession({ auto_escaneo_hora: e.target.value })
              }
              className="mt-1 w-full rounded-md border border-white/10 bg-black/30 px-2 py-1 font-mono text-white"
            />
          </label>
        )}
      </section>
    </aside>
  );
}
