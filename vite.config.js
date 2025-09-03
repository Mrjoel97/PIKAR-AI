import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json']
  },
  // Ensure JSX in .js is supported everywhere (dev and build)
  esbuild: {
    jsx: 'automatic'
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx',
      },
    },
  },
  build: {
    rollupOptions: {
      external: ['stripe']
    }
  },
  define: {
    // Prevent .env from forcing NODE_ENV for Vite
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production')
  },
})