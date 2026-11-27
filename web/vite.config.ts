import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"],
          charts: ["recharts"],
          ui: ["radix-ui", "lucide-react", "sonner"],
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": process.env.API_PROXY ?? "http://localhost:8000",
      "/chat": { target: process.env.API_PROXY ?? "http://localhost:8000", ws: true },
      "/docs": process.env.API_PROXY ?? "http://localhost:8000",
      "/redoc": process.env.API_PROXY ?? "http://localhost:8000",
      "/openapi.json": process.env.API_PROXY ?? "http://localhost:8000",
    },
  },
});
