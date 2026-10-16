import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, Vite (puerto 5173) manda las llamadas /api a Flask (puerto 5000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
})
