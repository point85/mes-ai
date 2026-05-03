import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const mesConfig = require('../mes.config.json')

// https://vite.dev/config/
export default defineConfig({
  define: {
    __MES_VERSION__: JSON.stringify(mesConfig.mesVersion),
    __MES_RELEASE_DATE__: JSON.stringify(mesConfig.releaseDate),
  },
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
    },
  },
})
