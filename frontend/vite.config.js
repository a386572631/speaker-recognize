import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '', '')
  return {
    plugins: [vue()],
    base: mode === 'production' ? '/stt/' : '/',
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: mode === 'development' ? {
        '/api': {
          target: env.VITE_API_BASE_URL,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      } : {},
    },
  }
})