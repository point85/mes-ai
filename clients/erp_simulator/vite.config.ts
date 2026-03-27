import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const MES_SERVER = 'http://localhost:8082'

function erpDetectPlugin(): Plugin {
  return {
    name: 'erp-detect',
    configureServer(server) {
      server.httpServer?.once('listening', async () => {
        try {
          const res = await fetch(`${MES_SERVER}/api/v1/erp/simulator/options`)
          if (res.ok) {
            const json = await res.json()
            const erpType = ((json.data?.erp_type) ?? 'unknown').toUpperCase()
            const label = erpType === 'SAP' ? '\x1b[34mSAP S/4HANA\x1b[0m'
                        : erpType === 'ORACLE' ? '\x1b[31mOracle Cloud\x1b[0m'
                        : `\x1b[33m${erpType}\x1b[0m`
            console.log(`\n  \x1b[1m⚙  ERP Simulator → ${label}\x1b[0m\n`)
          } else {
            console.log('\n  \x1b[33m⚠  ERP Simulator: server returned', res.status, '— is a simulator plugin enabled?\x1b[0m\n')
          }
        } catch {
          console.log('\n  \x1b[33m⚠  ERP Simulator: cannot reach MES server at', MES_SERVER, '\x1b[0m\n')
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), erpDetectPlugin()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: MES_SERVER,
        changeOrigin: true,
      },
    },
  },
})
