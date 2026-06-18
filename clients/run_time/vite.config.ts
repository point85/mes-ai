import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const mesConfig = require('../mes.config.json')
const MES_SERVER = process.env.MES_SERVER_URL ?? 'http://localhost:8082'

export default defineConfig({
  define: {
    __MES_VERSION__: JSON.stringify(mesConfig.mesVersion),
    __MES_RELEASE_DATE__: JSON.stringify(mesConfig.releaseDate),
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      devOptions: {
        enabled: true,
      },
      includeAssets: ['vite.svg'],
      manifest: {
        name: 'MES AI Runtime',
        short_name: 'MES RT',
        description: 'Runtime client for MES AI',
        theme_color: '#111827',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: 'icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icon-512x512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
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
