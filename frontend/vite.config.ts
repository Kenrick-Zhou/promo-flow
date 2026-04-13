import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(() => {
  // 允许通过 shell 环境变量覆盖后端地址，方便指向远程测试环境
  // 例如：BACKEND_URL=http://test-api:8000 npm run dev
  const backendUrl = process.env.BACKEND_URL ?? 'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        '/api': backendUrl,
        '/bot': backendUrl,
      },
    },
  }
})
