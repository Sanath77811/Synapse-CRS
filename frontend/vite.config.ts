/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Bind IPv4 and IPv6. host: "127.0.0.1" only makes http://localhost fail on many laptops (::1).
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ready": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/docs": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/openapi.json": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
  },
});
