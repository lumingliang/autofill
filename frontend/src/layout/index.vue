<template>
  <a-layout class="h-full">
    <a-layout-sider v-model:collapsed="appStore.collapsed" :trigger="null" collapsible theme="light"
      class="layout-sider">
      <div class="logo-container" @click="goHome">
        <img src="/logo.svg" class="logo-img" />
        <span v-show="!appStore.collapsed" class="logo-title">AI 平台</span>
      </div>
      <div class="menu-wrapper">
        <LayoutMenu />
      </div>
    </a-layout-sider>

    <a-layout>
      <a-layout-header class="layout-header">
        <LayoutHeader />
      </a-layout-header>

      <a-layout-content class="layout-content">
        <LayoutTags />
        <div class="main-content">
          <router-view v-slot="{ Component, route }">
            <transition name="fade" mode="out-in">
              <keep-alive :include="keepAliveNames">
                <component :is="Component" v-if="appStore.reloadFlag" :key="route.fullPath" />
              </keep-alive>
            </transition>
          </router-view>
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { useAppStore, usePermissionStore } from '@/store'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LayoutHeader from './components/LayoutHeader.vue'
import LayoutMenu from './components/LayoutMenu.vue'
import LayoutTags from './components/LayoutTags.vue'

const appStore = useAppStore()
const permissionStore = usePermissionStore()
const route = useRoute()
const router = useRouter()

// 跳转到主页
function goHome() {
  router.push('/')
}

const keepAliveNames = computed(() => {
  const names: string[] = []
  permissionStore.accessRoutes.forEach((r) => {
    r.children?.forEach((child: any) => {
      if (child.meta?.keepAlive) {
        names.push(child.name)
      }
    })
  })
  return names
})
</script>

<style scoped lang="less">
.layout-sider {
  border-right: none !important;
  box-shadow: none !important;

  .logo-container {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    cursor: pointer;
    transition: background-color 0.3s;

    &:hover {
      background-color: rgba(0, 0, 0, 0.03);
    }

    .logo-img {
      width: 32px;
      height: 32px;
    }

    .logo-title {
      color: #1890ff;
      font-size: 18px;
      font-weight: bold;
      margin-left: 12px;
      white-space: nowrap;
    }
  }

  .menu-wrapper {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    height: calc(100% - 64px);
  }
}

:deep(.ant-layout-sider) {
  border-right: none !important;
  margin-right: 0 !important;
}

:deep(.ant-layout-sider-light) {
  border-right: none !important;
}

:deep(.ant-layout-has-sider) {
  >.ant-layout {
    margin-left: 0 !important;
  }
}

:deep(.ant-layout-content) {
  margin: 0 !important;
  padding: 0 !important;
}

.layout-header {
  background: #fff;
  padding: 0;
  height: 64px;
  line-height: 64px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.layout-content {
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .main-content {
    flex: 1;
    padding: 0;
    overflow: auto;
    background: #f0f2f5;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
