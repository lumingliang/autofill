import type { App } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { routes, WHITE_LIST } from './routes'
import { getToken } from '@/utils'
import { useUserStore, usePermissionStore } from '@/store'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 }),
})

export async function setupRouter(app: App) {
  await addDynamicRoutes()
  setupRouterGuard()
  app.use(router)
}

export async function addDynamicRoutes() {
  const token = getToken()

  // 没有token情况
  if (!token) {
    return
  }

  // 有token的情况
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()

  if (!userStore.userId) {
    await userStore.getUserInfo()
  }

  try {
    const accessRoutes = await permissionStore.generateRoutes()
    await permissionStore.getAccessApis()
    accessRoutes.forEach((route) => {
      if (!router.hasRoute(route.name)) {
        router.addRoute(route)
      }
    })
  } catch (error) {
    console.error('error', error)
    const userStore = useUserStore()
    await userStore.logout()
  }
}

function setupRouterGuard() {
  router.beforeEach(async (to, from, next) => {
    const token = getToken()

    // 没有token的情况
    if (!token) {
      if (WHITE_LIST.includes(to.path)) {
        next()
      } else {
        next({ path: '/login', query: { redirect: to.path } })
      }
      return
    }

    // 有token的情况
    if (to.path === '/login') {
      next({ path: '/' })
      return
    }

    next()
  })
}

export default router
