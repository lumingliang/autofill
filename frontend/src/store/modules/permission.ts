import { defineStore } from 'pinia'
import { ref, computed, markRaw } from 'vue'
import api from '@/api'
import Layout from '@/layout/index.vue'

// 预加载所有视图组件
const vueModules = import.meta.glob('@/views/**/index.vue')

function buildRoutes(routes: any[] = []) {
  return routes.map((e) => {
    const route: any = {
      name: e.name,
      path: e.path,
      component: markRaw(Layout),
      meta: {
        title: e.name,
        icon: e.icon,
        order: e.order,
        keepAlive: e.keepalive,
      },
      children: [],
    }

    if (e.children && e.children.length > 0) {
      route.children = e.children.map((child: any) => {
        const componentPath = `/src/views/${child.component}/index.vue`
        const component = vueModules[componentPath]
        if (!component) {
          console.warn(`Component not found: ${componentPath}`)
        }
        return {
          name: child.name,
          path: child.path,
          component: markRaw(component || (() => import('@/views/error/404.vue'))),
          meta: {
            title: child.name,
            icon: child.icon,
            order: child.order,
            keepAlive: child.keepalive,
          },
        }
      })
    } else {
      const componentPath = `/src/views/${e.component}/index.vue`
      const component = vueModules[componentPath]
      if (!component) {
        console.warn(`Component not found: ${componentPath}`)
      }
      route.children.push({
        name: `${e.name}Default`,
        path: '',
        component: markRaw(component || (() => import('@/views/error/404.vue'))),
        meta: {
          title: e.name,
          icon: e.icon,
          order: e.order,
          keepAlive: e.keepalive,
        },
      })
    }

    return route
  })
}

export const usePermissionStore = defineStore('permission', () => {
  const accessRoutes = ref<any[]>([])
  const accessApis = ref<string[]>([])
  const isRoutesGenerated = ref(false)

  const menus = computed(() => {
    return accessRoutes.value.filter((route) => route.name && !route.meta?.hidden)
  })

  async function generateRoutes() {
    const res: any = await api.getUserMenu()
    accessRoutes.value = buildRoutes(res.data)
    isRoutesGenerated.value = true
    return accessRoutes.value
  }

  async function getAccessApis() {
    const res: any = await api.getUserApi()
    accessApis.value = res.data
    return accessApis.value
  }

  function resetPermission() {
    accessRoutes.value = []
    accessApis.value = []
    isRoutesGenerated.value = false
  }

  return {
    accessRoutes,
    accessApis,
    menus,
    isRoutesGenerated,
    generateRoutes,
    getAccessApis,
    resetPermission,
  }
})
