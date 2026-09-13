import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// `/api/*` is proxied to the FastAPI backend so the browser never deals with
// CORS or a hardcoded port. Override the target with VITE_API_TARGET.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    resolve: {
      alias: { "@shared": fileURLToPath(new URL("../shared", import.meta.url)) },
    },
    server: {
      port: 5173,
      fs: { allow: [".."] }, // shared/types.ts lives outside frontend/
      proxy: {
        "/api": {
          target: env.VITE_API_TARGET || "http://127.0.0.1:8000",
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
      },
    },
  };
});
