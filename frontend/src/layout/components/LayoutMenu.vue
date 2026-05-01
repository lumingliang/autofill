<template>
  <a-menu v-model:selectedKeys="selectedKeys" v-model:openKeys="openKeys" mode="inline" theme="light"
    :inline-collapsed="appStore.collapsed" @click="handleMenuClick">
    <template v-for="menu in menuList" :key="menu.key">
      <a-sub-menu v-if="menu.children && menu.children.length" :key="menu.key + '-sub'">
        <template #title>
          <span>
            <component :is="getIcon(menu.icon)" v-if="menu.icon" class="menu-icon" />
            <span>{{ menu.label }}</span>
          </span>
        </template>
        <a-menu-item v-for="child in menu.children" :key="child.key">
          <component :is="getIcon(child.icon)" v-if="child.icon" class="menu-icon" />
          <span>{{ child.label }}</span>
        </a-menu-item>
      </a-sub-menu>
      <a-menu-item v-else :key="menu.key + '-item'">
        <component :is="getIcon(menu.icon)" v-if="menu.icon" class="menu-icon" />
        <span>{{ menu.label }}</span>
      </a-menu-item>
    </template>
  </a-menu>
</template>

<script setup lang="ts">
import { useAppStore, usePermissionStore } from '@/store'
import * as Icons from '@ant-design/icons-vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const permissionStore = usePermissionStore()

// 直接使用数据库中的图标名称获取 Ant Design 图标组件
function getIcon(iconName?: string): any {
  if (!iconName) return null
  return Icons[iconName as keyof typeof Icons] || Icons.MenuOutlined
}

function resolvePath(basePath: string, path?: string): string {
  if (!path) return basePath
  if (path.startsWith('http')) return path
  return (
    '/' +
    [basePath, path]
      .filter((p) => !!p && p !== '/')
      .map((p) => p.replace(/(^\/)|(\/$)/g, ''))
      .join('/')
  )
}

interface MenuItem {
  label: string
  key: string
  path: string
  icon?: string
  order: number
  children?: MenuItem[]
}

function buildMenuItem(route: any, basePath = ''): MenuItem {
  let menuItem: MenuItem = {
    label: route.meta?.title || route.name,
    key: route.name,
    path: resolvePath(basePath, route.path),
    icon: route.meta?.icon,
    order: route.meta?.order || 0,
  }

  const visibleChildren = route.children
    ? route.children.filter((item: any) => item.name && !item.meta?.hidden)
    : []

  if (!visibleChildren.length) return menuItem

  const isCatalog = route.path?.startsWith('/') && visibleChildren.length > 0

  if (visibleChildren.length === 1 && !isCatalog) {
    const singleRoute = visibleChildren[0]
    menuItem = {
      ...menuItem,
      label: singleRoute.meta?.title || singleRoute.name,
      key: singleRoute.name,
      path: resolvePath(menuItem.path, singleRoute.path),
      icon: singleRoute.meta?.icon || menuItem.icon,
      order: singleRoute.meta?.order || menuItem.order,
    }
    const visibleItems = singleRoute.children
      ? singleRoute.children.filter((item: any) => item.name && !item.meta?.hidden)
      : []

    if (visibleItems.length === 1) {
      menuItem = buildMenuItem(visibleItems[0], menuItem.path)
    } else if (visibleItems.length > 1) {
      menuItem.children = visibleItems
        .map((item: any) => buildMenuItem(item, menuItem.path))
        .sort((a: any, b: any) => a.order - b.order)
    }
  } else {
    menuItem.children = visibleChildren
      .map((item: any) => buildMenuItem(item, menuItem.path))
      .sort((a: any, b: any) => a.order - b.order)
  }
  return menuItem
}

const menuList = computed(() => {
  return permissionStore.menus
    .map((item: any) => buildMenuItem(item))
    .sort((a: any, b: any) => a.order - b.order)
})

const selectedKeys = ref<string[]>([])
const openKeys = ref<string[]>([])

watch(
  () => route.name,
  (name) => {
    if (name) {
      selectedKeys.value = [String(name)]
      const findParent = (menus: MenuItem[]): string | undefined => {
        for (const menu of menus) {
          if (menu.children?.some((c) => c.key === name)) {
            return menu.key
          }
          if (menu.children) {
            const found = findParent(menu.children)
            if (found) return found
          }
        }
        return undefined
      }
      const parentKey = findParent(menuList.value)
      if (parentKey && !appStore.collapsed) {
        openKeys.value = [parentKey + '-sub']
      }
    }
  },
  { immediate: true }
)

function handleMenuClick({ key }: { key: string }) {
  const findMenuByKey = (menus: MenuItem[]): MenuItem | undefined => {
    for (const menu of menus) {
      if (menu.key === key) return menu
      if (menu.children) {
        const found = findMenuByKey(menu.children)
        if (found) return found
      }
    }
    return undefined
  }

  const menuItem = findMenuByKey(menuList.value)
  if (menuItem) {
    if (menuItem.path === route.path) {
      router.replace({ path: '/redirect' + menuItem.path })
    } else {
      router.push(menuItem.path)
    }
  }
}
</script>

<style scoped>
.menu-icon {
  display: inline-flex;
  align-items: center;
  margin-right: 8px;
  font-size: 16px;
  vertical-align: middle;
}

:deep(.ant-menu-item) {
  display: flex;
  align-items: center;
}

:deep(.ant-menu-submenu-title) {
  display: flex;
  align-items: center;
}

:deep(.ant-menu-submenu-title > span) {
  display: flex;
  align-items: center;
}
</style>
