import './styles/index.less'

import { createApp } from 'vue'
import App from './App.vue'
import { setupAntDesign } from './core/ant-design'
import { setupDirectives } from './directives'
import { setupRouter } from './router'
import { setupStore } from './store'

// vxe-table
import VXETable from 'vxe-table'
import 'vxe-table/lib/style.css'

// 抑制 ResizeObserver 循环错误（Ant Design Vue 的已知问题）
const originalError = window.console.error
window.console.error = (...args: any[]) => {
  if (/ResizeObserver loop/.test(args[0]?.message || args[0])) {
    return
  }
  originalError.apply(window.console, args)
}

async function bootstrap() {
  const app = createApp(App)

  setupStore(app)
  setupAntDesign(app)
  await setupRouter(app)
  setupDirectives(app)

  // 使用 vxe-table
  app.use(VXETable)

  app.mount('#app')
}

bootstrap()
