import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { nodePolyfills } from 'vite-plugin-node-polyfills'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  build: {
    outDir: '../docs',
    emptyOutDir: true
  },
  plugins: [
    vue(),
    tailwindcss(),
    nodePolyfills({
      include: ['zlib', 'util', 'stream', 'path', 'http', 'https', 'url', 'buffer'],
      globals: {
        Buffer: true,
        global: true,
        process: true
      }
    })
  ],
  resolve: {
    alias: {
      zlib: 'browserify-zlib',
      'dicom-parser': path.resolve(__dirname, './src/dummy.js')
    }
  },
  define: {
    'process.env': {}
  }
})
