import { fileURLToPath, URL } from 'node:url'
import Vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import Vuetify, { transformAssetUrls } from 'vite-plugin-vuetify'

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks (id) {
          if (!id.includes('node_modules')) {
            return undefined
          }
          if (id.includes('monaco-editor/esm/vs/editor/')) {
            return 'monaco-editor'
          }
          if (id.includes('monaco-editor/esm/vs/base/')) {
            return 'monaco-base'
          }
          if (id.includes('monaco-editor/esm/vs/platform/')) {
            return 'monaco-platform'
          }
          if (id.includes('monaco-editor/esm/vs/')) {
            return 'monaco-vs'
          }
          if (id.includes('/vue/') || id.includes('/vue-router/') || id.includes('/pinia/')) {
            return 'framework'
          }
          if (id.includes('/vuetify/')) {
            return 'vuetify'
          }
          return undefined
        },
      },
    },
  },
  plugins: [
    Vue({
      template: { transformAssetUrls },
    }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/master/packages/vite-plugin#readme
    Vuetify({
      autoImport: true,
      styles: {
        configFile: 'src/styles/settings.scss',
      },
    }),
  ],
  define: { 'process.env': {} },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('src', import.meta.url)),
    },
    extensions: [
      '.js',
      '.json',
      '.jsx',
      '.mjs',
      '.ts',
      '.tsx',
      '.vue',
    ],
  },
  server: {
    port: 8089,
    proxy: {
      '/api': 'http://localhost:8080',
      '/ws': { target: 'ws://localhost:8080', ws: true },
    },
  },
})
