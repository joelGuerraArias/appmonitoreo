"use client";

import { useCallback, useEffect, useState } from "react";
import { AutoScanClock } from "./AutoScanClock";
import { Sidebar } from "./Sidebar";
import { ClipsGrid } from "./ClipsGrid";
import { EntidadesPanel } from "./EntidadesPanel";
import { AnalisisPanel } from "./AnalisisPanel";
import type {
  AnalisisClips,
  ClientePublico,
  ClipInfo,
  SessionStats,
} from "@/lib/types";

type Tab = "clips" | "sesion" | "analisis" | "entidades";

type WorkerStatus = {
  running?: boolean;
  phase?: string;
  mode?: string;
  message?: string;
  logs?: string[];
  pendientes?: number;
  wait_seconds?: number;
  updated_at?: string;
};

const emptySession: SessionStats = {
  videos_encontrados: 0,
  videos_procesados: 0,
  clips_generados: 0,
  loop_continuo: true,
  intervalo_loop: 60,
  intervalo_loop_vacio: 120,
  loop_ciclo_numero: 0,
  running: false,
  auto_escaneo_enabled: true,
  auto_escaneo_hora: "06:30",
  auto_escaneo_disparado_fecha: null,
  ia_motor_sesion: "gemini",
  mistral_total_transcripciones: 0,
  mistral_total_audio_seconds: 0,
  mistral_total_tokens: 0,
  alertas_envio: [],
  last_scan_message: null,
  updated_at: "",
};

export function Dashboard() {
  const [clientes, setClientes] = useState<ClientePublico[]>([]);
  const [session, setSession] = useState<SessionStats>(emptySession);
  const [clips, setClips] = useState<ClipInfo[]>([]);
  const [analisis, setAnalisis] = useState<AnalisisClips | null>(null);
  const [tab, setTab] = useState<Tab>("clips");
  const [paths, setPaths] = useState<{ config?: string; procesados?: string }>(
    {},
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [worker, setWorker] = useState<WorkerStatus>({});
  const [alive, setAlive] = useState(false);
  const [autoStartWorker, setAutoStartWorker] = useState(true);

  const loadClientes = useCallback(async () => {
    const res = await fetch("/api/clientes");
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Error clientes");
    setClientes(data.clientes);
    setPaths(data.paths || {});
  }, []);

  const loadClips = useCallback(async () => {
    const res = await fetch("/api/clips?limit=150");
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Error clips");
    setClips(data.clips);
    setAnalisis(data.analisis);
  }, []);

  const loadScanStatus = useCallback(async () => {
    const res = await fetch("/api/scan");
    const data = await res.json();
    if (!data.ok) return;
    if (data.session) setSession(data.session);
    setWorker(data.worker || {});
    setAlive(Boolean(data.alive));
  }, []);

  const loadSessionPrefs = useCallback(async () => {
    const res = await fetch("/api/session");
    const data = await res.json();
    if (!data.ok) return;
    if (data.session) setSession(data.session);
    if (data.prefs?.auto_start_worker != null) {
      setAutoStartWorker(Boolean(data.prefs.auto_start_worker));
    }
  }, []);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      await Promise.all([
        loadClientes(),
        loadSessionPrefs(),
        loadScanStatus(),
        loadClips(),
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [loadClientes, loadSessionPrefs, loadScanStatus, loadClips]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Polling rápido mientras el worker vive
  useEffect(() => {
    const ms = alive || session.running ? 3000 : 12000;
    const t = setInterval(() => {
      void loadScanStatus();
      if (alive || session.running) void loadClips();
    }, ms);
    return () => clearInterval(t);
  }, [alive, session.running, loadScanStatus, loadClips]);

  const onToggleEntidad = async (id: string, incluir: boolean) => {
    setBusy(true);
    try {
      const res = await fetch(`/api/clientes/${id}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incluir_en_analisis: incluir }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error);
      setClientes((prev) =>
        prev.map((c) => (c.id === id ? data.cliente : c)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const onPatchSession = async (
    patch: Partial<SessionStats> & { auto_start_worker?: boolean },
  ) => {
    if (typeof patch.auto_start_worker === "boolean") {
      setAutoStartWorker(patch.auto_start_worker);
    }
    setSession((s) => ({ ...s, ...patch }));
    const res = await fetch("/api/session", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    const data = await res.json();
    if (data.ok) {
      if (data.session) setSession(data.session);
      if (data.prefs?.auto_start_worker != null) {
        setAutoStartWorker(Boolean(data.prefs.auto_start_worker));
      }
    }
  };

  const scan = async (action: "start" | "once" | "stop") => {
    setBusy(true);
    setError(null);
    try {
      const body =
        action === "start"
          ? { action: "start", mode: session.loop_continuo ? "loop" : "once" }
          : { action };
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Error scan");
      if (data.session) setSession(data.session);
      setWorker(data.worker || {});
      setAlive(Boolean(data.alive));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const tabs: Array<[Tab, string]> = [
    ["clips", "Todos los clips"],
    ["sesion", "Clips recientes"],
    ["analisis", "Análisis"],
    ["entidades", "Entidades y rutas"],
  ];

  const running = alive || session.running;

  return (
    <div className="flex min-h-screen bg-[#070b14] text-zinc-100">
      <div className="hidden lg:block lg:w-80 lg:shrink-0">
        <Sidebar
          session={session}
          clientes={clientes}
          autoStartWorker={autoStartWorker}
          onToggleEntidad={onToggleEntidad}
          onPatchSession={onPatchSession}
        />
      </div>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-white/10 px-4 py-5 sm:px-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-cyan-400/80">
                Video Analyzer · Next.js (standalone)
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                Análisis automático de videos — v3
              </h1>
              <p className="mt-2 max-w-2xl text-sm text-zinc-400">
                No necesitas abrir Streamlit. Al arrancar Next se lanza solo el
                worker Python con el mismo pipeline (
                <code className="text-zinc-300">buscar_y_procesar_videos</code>
                ).
              </p>
            </div>
            <button
              type="button"
              onClick={() => void refresh()}
              className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-zinc-300 hover:bg-white/10"
            >
              Refrescar
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2 text-xs text-zinc-500">
            {paths.procesados && (
              <span className="rounded bg-black/40 px-2 py-1 font-mono">
                📁 {paths.procesados}
              </span>
            )}
            <span className="rounded bg-black/40 px-2 py-1">
              Motor: {session.ia_motor_sesion}
            </span>
            <span
              className={`rounded px-2 py-1 ${
                running
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "bg-zinc-800 text-zinc-400"
              }`}
            >
              {running
                ? `Worker: ${worker.phase || "activo"}`
                : "Idle"}
            </span>
            {typeof worker.pendientes === "number" && (
              <span className="rounded bg-black/40 px-2 py-1">
                Pendientes: {worker.pendientes}
              </span>
            )}
          </div>
        </header>

        <div className="space-y-5 px-4 py-5 sm:px-8">
          <AutoScanClock
            enabled={session.auto_escaneo_enabled}
            hora={session.auto_escaneo_hora}
          />

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={busy || running}
              onClick={() => void scan("start")}
              className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              {session.loop_continuo
                ? "Iniciar búsqueda continua"
                : "Iniciar un ciclo"}
            </button>
            <button
              type="button"
              disabled={busy || running}
              onClick={() => void scan("once")}
              className="rounded-xl bg-cyan-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              Procesar una vez
            </button>
            <button
              type="button"
              disabled={busy || !running}
              onClick={() => void scan("stop")}
              className="rounded-xl bg-zinc-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              Detener
            </button>
          </div>

          {(session.last_scan_message || worker.message) && (
            <p className="rounded-lg border border-amber-500/30 bg-amber-950/30 px-3 py-2 text-sm text-amber-100">
              {worker.message || session.last_scan_message}
              {worker.updated_at ? (
                <span className="ml-2 text-xs text-amber-200/60">
                  · {worker.updated_at}
                </span>
              ) : null}
            </p>
          )}
          {error && (
            <p className="rounded-lg border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          )}

          {(worker.logs?.length ?? 0) > 0 && (
            <div className="rounded-xl border border-white/10 bg-black/40 p-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                Log del worker
              </p>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-zinc-300">
                {(worker.logs || []).slice(-25).join("\n")}
              </pre>
            </div>
          )}

          <div className="lg:hidden">
            <Sidebar
              session={session}
              clientes={clientes}
              autoStartWorker={autoStartWorker}
              onToggleEntidad={onToggleEntidad}
              onPatchSession={onPatchSession}
            />
          </div>

          <div className="flex flex-wrap gap-2 border-b border-white/10 pb-2">
            {tabs.map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  tab === id
                    ? "bg-white text-zinc-900"
                    : "text-zinc-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "clips" && (
            <ClipsGrid
              clips={clips}
              emptyText="No hay clips. Inicia un ciclo para procesar videos pendientes."
            />
          )}
          {tab === "sesion" && (
            <ClipsGrid
              clips={clips.slice(0, 30)}
              emptyText="Aún no hay clips recientes en videos procesados."
            />
          )}
          {tab === "analisis" && <AnalisisPanel analisis={analisis} />}
          {tab === "entidades" && (
            <EntidadesPanel
              clientes={clientes}
              onToggle={onToggleEntidad}
            />
          )}
        </div>
      </main>
    </div>
  );
}
