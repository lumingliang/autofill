import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import UnoCSS from 'unocss/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'
import Components from 'unplugin-vue-components/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // 设置基础路径，所有资源都会带上此前缀
  // 在容器部署时需要设置为 '/web/'，本地开发时设置为 '/'
  base: process.env.DOCKER_BUILD === 'true' ? '/web/' : '/',
  plugins: [
    vue(),
    UnoCSS({
      mode: 'vue-scoped',
    }),
    Components({
      resolvers: [
        AntDesignVueResolver({
          importStyle: false,
        }),
      ],
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    include: [
      'ant-design-vue/es/date-picker/dayjs',
      'dayjs',
      'dayjs/plugin/advancedFormat',
      'dayjs/plugin/customParseFormat',
      'dayjs/plugin/dayOfYear',
      'dayjs/plugin/localeData',
      'dayjs/plugin/quarterOfYear',
      'dayjs/plugin/weekOfYear',
      'dayjs/plugin/weekYear',
    ],
    // 排除 handsontable 内部模块，避免 tree-shaking 问题
    exclude: ['handsontable'],
  },
  server: {
    host: '0.0.0.0',
    port: 3200,
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9999',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:9999',
        changeOrigin: true,
      },
    },
  },
})
