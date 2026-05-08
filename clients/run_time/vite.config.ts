import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const mesConfig = require('../mes.config.json')
const MES_SERVER = 'http://localhost:8082'

export default defineConfig({
  define: {
    __MES_VERSION__: JSON.stringify(mesConfig.mesVersion),
    __MES_RELEASE_DATE__: JSON.stringify(mesConfig.releaseDate),
  },
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5176,
    proxy: {
      '/api': {
        target: MES_SERVER,
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
