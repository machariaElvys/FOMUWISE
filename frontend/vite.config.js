import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: [".e2b.app"],
    proxy: { "/api": { target: "http://127.0.0.1:5000", changeOrigin: true } },
  },
});
