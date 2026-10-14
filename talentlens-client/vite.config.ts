import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:9000',
          changeOrigin: true,
        },
      },
    },
    build: {
      // The FastAPI backend serves the UI from this directory.
      outDir: path.resolve(__dirname, '../talentlens-ai/static'),
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') ||
                id.includes('node_modules/react-router-dom') || id.includes('node_modules/@tanstack') ||
                id.includes('node_modules/zustand') || id.includes('node_modules/axios')) {
              return 'vendor'
            }
          },
        },
      },
    },
  }
})
