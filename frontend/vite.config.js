import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const configPath = resolve(__dirname, '..', 'config.json')

let config = null

try {
  const raw = readFileSync(configPath, 'utf-8')
  config = JSON.parse(raw)
} catch (e) {
  console.error('Failed to load config:', e.message)
}

const backendHost = config?.backend?.host === '0.0.0.0' ? 'localhost' : config?.backend?.host
const backendPort = config?.backend?.port
const frontendPort = config?.frontend?.port
const serverHost = config?.server?.host || 'localhost'
const serverPort = config?.server?.port || 5000

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontendPort,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true
      },
      '/connector': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true
      },
      '/json/version': {
        target: `http://127.0.0.1:9292`,
        changeOrigin: true,
        ws: true
      }
    }
  },
  define: {
    __SERVER_HOST__: JSON.stringify(serverHost),
    __SERVER_PORT__: JSON.stringify(serverPort)
  }
})