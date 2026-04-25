<template>
  <div flex items-center>
    <MenuCollapse />
    <BreadCrumb ml-15 hidden sm:block />
  </div>
  <div ml-auto flex items-center>
    <!-- 租户选择器 -->
    <TenantSelector v-if="userStore.tenants.length > 1" />
    <Languages />
    <ThemeMode />
    <GithubSite />
    <FullScreen />
    <UserAvatar />
  </div>
</template>

<script setup>
import BreadCrumb from './components/BreadCrumb.vue'
import MenuCollapse from './components/MenuCollapse.vue'
import FullScreen from './components/FullScreen.vue'
import UserAvatar from './components/UserAvatar.vue'
import GithubSite from './components/GithubSite.vue'
import ThemeMode from './components/ThemeMode.vue'
import Languages from './components/Languages.vue'
import TenantSelector from './components/TenantSelector.vue'
import { useUserStore } from '@/store'

const userStore = useUserStore()
</script>
