import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_ADMIN_BASE_PATH || '/admin/',
  server: {
    host: '0.0.0.0',
    port: 5174,
  },
})
