import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // proxy API requests to backend in dev — avoids CORS hassles
    proxy: {
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/matches': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/predictions': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ranking': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/leagues': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/bonus': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
