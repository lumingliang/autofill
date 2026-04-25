import 'uno.css'
import './styles/index.less'

import { createApp } from 'vue'
import { setupRouter } from './router'
import { setupStore } from './store'
import App from './App.vue'
import { setupDirectives } from './directives'
import { setupAntDesign } from './core/ant-design'

async function bootstrap() {
  const app = createApp(App)

  setupStore(app)
  setupAntDesign(app)
  await setupRouter(app)
  setupDirectives(app)

  app.mount('#app')
}

bootstrap()
