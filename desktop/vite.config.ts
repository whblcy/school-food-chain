import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Tauri 桌面端构建配置
// 复用 Web 前端代码，但通过相对路径加载（Tauri 使用 tauri:// 协议）
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  // Tauri 使用固定端口 1420
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  // 桌面端构建产物输出到 src-tauri 的 dist 目录
  build: {
    outDir: 'dist',
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          'naive-ui': ['naive-ui'],
          'echarts': ['echarts'],
          'vendor': ['vue', 'vue-router', 'pinia', 'axios', 'vue-i18n'],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
