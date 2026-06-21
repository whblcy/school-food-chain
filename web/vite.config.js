import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // 保留原始请求中的 Authorization 头
            const auth = req.headers['authorization']
            if (auth) {
              proxyReq.setHeader('Authorization', auth)
            }
          })
        }
      }
    }
  }
})
