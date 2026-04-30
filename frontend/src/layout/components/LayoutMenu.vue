<template>
  <a-menu v-model:selectedKeys="selectedKeys" v-model:openKeys="openKeys" mode="inline" theme="dark"
    :inline-collapsed="appStore.collapsed" @click="handleMenuClick">
    <template v-for="menu in menuList" :key="menu.key">
      <a-sub-menu v-if="menu.children && menu.children.length" :key="menu.key + '-sub'">
        <template #title>
          <span>
            <component :is="getIcon(menu.icon)" v-if="menu.icon" />
            <span>{{ menu.label }}</span>
          </span>
        </template>
        <a-menu-item v-for="child in menu.children" :key="child.key">
          {{ child.label }}
        </a-menu-item>
      </a-sub-menu>
      <a-menu-item v-else :key="menu.key + '-item'">
        <component :is="getIcon(menu.icon)" v-if="menu.icon" />
        <span>{{ menu.label }}</span>
      </a-menu-item>
    </template>
  </a-menu>
</template>

<script setup lang="ts">
import { useAppStore, usePermissionStore } from '@/store'
import {
  ApartmentOutlined,
  ApiOutlined,
  FileTextOutlined,
  HomeOutlined,
  MenuOutlined,
  SafetyOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const permissionStore = usePermissionStore()

const iconMap: Record<string, any> = {
  'MenuOutlined': MenuOutlined,
  'SettingOutlined': SettingOutlined,
  'TeamOutlined': TeamOutlined,
  'FileTextOutlined': FileTextOutlined,
  'ApartmentOutlined': ApartmentOutlined,
  'ApiOutlined': ApiOutlined,
  'SafetyOutlined': SafetyOutlined,
  'UserOutlined': UserOutlined,
  'HomeOutlined': HomeOutlined,
}

function getIcon(iconName?: string) {
  if (!iconName) return null
  // 尝试直接匹配
  if (iconMap[iconName]) return iconMap[iconName]
  // 对于其他图标，返回 MenuOutlined 作为默认
  return MenuOutlined
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

  // 检查当前路由是否是目录类型（有Layout组件且有多个子路由或明确是catalog类型）
  const isCatalog = route.path?.startsWith('/') && visibleChildren.length > 0

  if (visibleChildren.length === 1 && !isCatalog) {
    // 单个子路由，直接提升（仅对非目录类型）
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
      // 查找当前路由所在的父菜单
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
        openKeys.value = [parentKey]
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
      // 刷新当前页面
      router.replace({ path: '/redirect' + menuItem.path })
    } else {
      router.push(menuItem.path)
    }
  }
}
</script>
