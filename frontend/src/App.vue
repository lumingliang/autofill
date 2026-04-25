<template>
  <a-config-provider :locale="zhCN" :theme="theme">
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </a-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useAppStore } from '@/store'

const appStore = useAppStore()

const theme = computed(() => ({
  token: {
    colorPrimary: '#F4511E',
  },
  algorithm: appStore.isDark ? undefined : undefined,
}))
</script>
