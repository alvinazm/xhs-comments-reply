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

const backendHost = config?.backend?.host
const backendPort = config?.backend?.port
const frontendPort = config?.frontend?.port

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontendPort,
    proxy: {
      '/api': {
        target: `http://${backendHost}:${backendPort}`,
        changeOrigin: true
      }
    }
  }
})