<template>
  <a-config-provider :locale="zhCN" :theme="theme">
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </a-config-provider>
</template>

<script setup lang="ts">
import { useAppStore } from '@/store'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { computed } from 'vue'

const appStore = useAppStore()

const theme = computed(() => ({
  token: {
    colorPrimary: '#F4511E',
  },
  algorithm: appStore.isDark ? undefined : undefined,
}))
</script>
