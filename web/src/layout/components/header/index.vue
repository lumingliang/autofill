<template>
  <div flex items-center>
    <MenuCollapse />
    <BreadCrumb ml-15 hidden sm:block />
    <!-- 快捷登录模式提示 -->
    <div v-if="isQuickLoginMode" ml-20 flex items-center gap-2>
      <n-tag type="warning" size="small">
        <template #icon>
          <TheIcon icon="material-symbols:login" :size="14" />
        </template>
        快捷登录: {{ quickLoginTarget }}
      </n-tag>
      <n-button type="primary" size="small" @click="handleReturnToOriginal">
        <template #icon>
          <TheIcon icon="material-symbols:logout" :size="14" />
        </template>
        返回原用户
      </n-button>
    </div>
  </div>
  <div ml-auto flex items-center>
    <!-- 租户选择器 -->
    <TenantSelector v-if="userStore.tenants.length > 1" />
    <!-- 语言切换组件已隐藏，保留文件供后续扩展 -->
    <!-- <Languages /> -->
    <ThemeMode />
    <FullScreen />
    <UserAvatar />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BreadCrumb from './components/BreadCrumb.vue'
import MenuCollapse from './components/MenuCollapse.vue'
import FullScreen from './components/FullScreen.vue'
import UserAvatar from './components/UserAvatar.vue'
import ThemeMode from './components/ThemeMode.vue'
// import Languages from './components/Languages.vue'
import TenantSelector from './components/TenantSelector.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useUserStore } from '@/store'
import { lStorage } from '@/utils'
import api from '@/api'

const userStore = useUserStore()
const router = useRouter()

const isQuickLoginMode = ref(false)
const quickLoginTarget = ref('')

onMounted(() => {
  // 检查是否处于快捷登录模式
  const quickLoginMode = lStorage.get('quick_login_mode')
  const target = lStorage.get('quick_login_target')
  if (quickLoginMode === 'true' && target) {
    isQuickLoginMode.value = true
    quickLoginTarget.value = target
  }
})

async function handleReturnToOriginal() {
  const originalToken = lStorage.get('original_token')
  if (!originalToken) {
    $message.error('无法返回原用户，请重新登录')
    router.push('/login')
    return
  }

  try {
    // 获取原用户信息（用于判断是否需要选择租户）
    const { setToken } = await import('@/utils')
    setToken(originalToken)
    const res = await api.getUserInfo()

    if (res.code !== 200) {
      $message.error('获取原用户信息失败')
      return
    }

    // 构建待验证的登录信息
    const pendingAuth = {
      token: originalToken,
      tenants: res.data.tenants,
      needSelectTenant: res.data.tenants?.length > 1 && !res.data.current_tenant_id,
      currentTenantId: res.data.current_tenant_id,
      isQuickLogin: false // 返回原用户不是快捷登录
    }
    lStorage.set('pending_auth', JSON.stringify(pendingAuth))

    // 清除快捷登录标记
    lStorage.remove('quick_login_mode')
    lStorage.remove('quick_login_target')
    lStorage.remove('original_token')

    // 触发退出登录
    await userStore.logoutWithoutRedirect()

    // 跳转到登录页
    router.push('/login')
  } catch (error) {
    console.error('return to original error', error)
    $message.error('返回原用户失败')
    router.push('/login')
  }
}
</script>
