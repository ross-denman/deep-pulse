import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/chronicle': {
        target: 'http://localhost:4110',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:4110',
        ws: true,
      },
    },
  },
})
