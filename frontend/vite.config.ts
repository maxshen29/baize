import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 用 127.0.0.1 而非 localhost，避免 Node 将 localhost 解析为 IPv6(::1)
        // 而 uvicorn 默认只监听 IPv4(127.0.0.1) 导致的代理 500/EADDRNOTAVAIL
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/modules': {
        target: 'http://127.0.0.1:8000', // 业务模块静态资源由后端/Nginx 托管
        changeOrigin: true,
      },
    },
  },
})
