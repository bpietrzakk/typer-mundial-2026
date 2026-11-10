import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// one id per build: goes into dist/sw.js (new cache name + new bytes, so the
// browser installs the new worker) and into the app (VITE_BUILD_ID)
const BUILD_ID = Date.now().toString(36)

// swaps the __BUILD_ID__ placeholder in the copied public/sw.js
function swBuildId() {
  let outDir = 'dist'
  return {
    name: 'sw-build-id',
    apply: 'build',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
    },
    closeBundle() {
      const file = resolve(outDir, 'sw.js')
      if (!existsSync(file)) return
      const source = readFileSync(file, 'utf8')
      writeFileSync(file, source.replaceAll('__BUILD_ID__', BUILD_ID))
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, '')
  // backend address for the dev proxy, e.g. VITE_PROXY_TARGET=http://localhost:8001
  const target = env.VITE_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react(), swBuildId()],
    define: {
      'import.meta.env.VITE_BUILD_ID': JSON.stringify(BUILD_ID),
    },
    server: {
      port: Number(env.VITE_DEV_PORT) || 5173,
      // same /api prefix as prod (vercel rewrite) and docker (nginx)
      // so page routes like /matches never get swallowed by the proxy
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
