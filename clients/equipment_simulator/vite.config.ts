import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const MES_SERVER = 'http://localhost:8082'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
    proxy: {
      '/api': {
        target: MES_SERVER,
        changeOrigin: true,
      },
    },
  },
})
