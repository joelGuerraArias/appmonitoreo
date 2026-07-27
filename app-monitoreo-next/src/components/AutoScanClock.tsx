"use client";

import { useEffect, useState } from "react";
import { formatHms, segundosHastaHora } from "@/lib/countdown";

export function AutoScanClock({
  enabled,
  hora,
}: {
  enabled: boolean;
  hora: string;
}) {
  const [now, setNow] = useState(() => new Date());
  const [left, setLeft] = useState(() => segundosHastaHora(hora));

  useEffect(() => {
    const t = setInterval(() => {
      setNow(new Date());
      setLeft(segundosHastaHora(hora));
    }, 1000);
    return () => clearInterval(t);
  }, [hora]);

  if (!enabled) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-zinc-400">
        Auto-escaneo desactivado
      </div>
    );
  }

  const clock = now.toLocaleTimeString("es-DO", { hour12: false });

  return (
    <div className="rounded-xl border border-cyan-500/30 bg-gradient-to-br from-cyan-950/40 to-slate-900/60 px-5 py-4">
      <p className="text-xs uppercase tracking-wider text-cyan-300/80">
        Auto-escaneo programado
      </p>
      <div className="mt-2 flex flex-wrap items-end gap-6">
        <div>
          <p className="text-xs text-zinc-400">Hora actual</p>
          <p className="font-mono text-2xl text-white">{clock}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">Inicio</p>
          <p className="font-mono text-2xl text-cyan-200">{hora}</p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">Cuenta atrás</p>
          <p className="font-mono text-3xl font-semibold text-white">
            {formatHms(left)}
          </p>
        </div>
      </div>
    </div>
  );
}
