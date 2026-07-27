import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Evita que Turbopack tome el lockfile del home del usuario.
  turbopack: {
    root: path.join(__dirname),
  },
  // Arranca worker Python al levantar el server (src/instrumentation.ts)
  experimental: {
    serverActions: {
      bodySizeLimit: "4mb",
    },
  },
};

export default nextConfig;
