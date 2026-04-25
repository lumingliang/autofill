import { useUserStore, usePermissionStore } from '@/store'
import type { App, Directive } from 'vue'

function hasPermission(permission: string): boolean {
  const userStore = useUserStore()
  const permissionStore = usePermissionStore()

  if (userStore.isSuperUser) {
    return true
  }
  return permissionStore.accessApis.includes(permission)
}

export function setupPermissionDirective(app: App) {
  const permissionDirective: Directive = {
    mounted(el, binding) {
      const permission = binding.value
      if (!permission) {
        console.warn('need permission like v-permission="post/api/v1/user/create"')
        return
      }
      if (!hasPermission(permission)) {
        el.parentElement?.removeChild(el)
      }
    },
  }

  app.directive('permission', permissionDirective)
}
