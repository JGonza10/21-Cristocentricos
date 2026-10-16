import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, Vite (puerto 5173) manda las llamadas /api a Flask (puerto 5000).
// Dos páginas: la app (index.html) y el overlay del reloj (reloj.html).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
  build: {
    rollupOptions: {
      input: { app: resolve(__dirname, 'index.html'), reloj: resolve(__dirname, 'reloj.html') },
    },
  },
})
