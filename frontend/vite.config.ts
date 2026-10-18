import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Forward API calls to the FastAPI backend during development (no CORS needed).
    proxy: {
      // HUNCH_API lets run.py point the proxy at another port.
      '/api': process.env.HUNCH_API ?? 'http://localhost:8000',
    },
  },
})
