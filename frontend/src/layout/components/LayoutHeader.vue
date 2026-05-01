<template>
  <div class="header-wrapper">
    <div class="left-section">
      <MenuFoldOutlined v-if="!appStore.collapsed" class="trigger" @click="appStore.switchCollapsed" />
      <MenuUnfoldOutlined v-else class="trigger" @click="appStore.switchCollapsed" />
      <Breadcrumb />
    </div>
    <div class="right-section">
      <!-- 快捷登录模式提示 -->
      <div v-if="isQuickLoginMode" class="quick-login-notice">
        <a-tag color="warning">
          <LoginOutlined />
          快捷登录: {{ quickLoginTarget }}
        </a-tag>
        <a-button type="primary" size="small" @click="handleReturnToOriginal">
          <LogoutOutlined />
          返回原用户
        </a-button>
      </div>

      <a-dropdown v-if="userStore.tenants.length > 1">
        <a-button type="text">
          <ClusterOutlined />
          {{ userStore.currentTenant?.name || '选择租户' }}
          <DownOutlined />
        </a-button>
        <template #overlay>
          <a-menu @click="handleTenantSwitch">
            <a-menu-item v-for="tenant in userStore.tenants" :key="tenant.id">
              {{ tenant.name }}
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>

      <a-dropdown>
        <div class="user-info">
          <a-avatar :src="userStore.avatar" :size="32">
            <template #icon><UserOutlined /></template>
          </a-avatar>
          <span class="username">{{ userStore.name }}</span>
          <DownOutlined />
        </div>
        <template #overlay>
          <a-menu @click="handleUserMenuClick">
            <a-menu-item key="profile">
              <UserOutlined />
              个人中心
            </a-menu-item>
            <a-menu-divider />
            <a-menu-item key="logout">
              <LogoutOutlined />
              退出登录
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore, useUserStore } from '@/store'
import { setToken } from '@/utils'
import api from '@/api'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DownOutlined,
  UserOutlined,
  LogoutOutlined,
  ClusterOutlined,
  LoginOutlined,
} from '@ant-design/icons-vue'
import Breadcrumb from './Breadcrumb.vue'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

// 快捷登录相关
const isQuickLoginMode = ref(false)
const quickLoginTarget = ref('')

onMounted(() => {
  // 检查是否处于快捷登录模式
  const quickLoginMode = localStorage.getItem('quick_login_mode')
  const target = localStorage.getItem('quick_login_target')
  if (quickLoginMode === 'true' && target) {
    isQuickLoginMode.value = true
    quickLoginTarget.value = target
  }
})

// 返回原用户
async function handleReturnToOriginal() {
  const originalToken = localStorage.getItem('original_token')
  if (!originalToken) {
    window.$message?.error('无法返回原用户，请重新登录')
    router.push('/login')
    return
  }

  try {
    // 获取原用户信息（用于判断是否需要选择租户）
    setToken(originalToken)
    const res: any = await api.getUserInfo()

    if (res.code !== 200) {
      window.$message?.error('获取原用户信息失败')
      return
    }

    // 构建待验证的登录信息
    const pendingAuth = {
      token: originalToken,
      tenants: res.data.tenants,
      needSelectTenant: res.data.tenants?.length > 1 && !res.data.current_tenant_id,
      currentTenantId: res.data.current_tenant_id,
      isQuickLogin: false, // 返回原用户不是快捷登录
    }
    localStorage.setItem('pending_auth', JSON.stringify(pendingAuth))

    // 清除快捷登录标记
    localStorage.removeItem('quick_login_mode')
    localStorage.removeItem('quick_login_target')
    localStorage.removeItem('original_token')

    // 触发退出登录
    await userStore.logoutWithoutRedirect()

    // 跳转到登录页
    router.push('/login')
  } catch (error) {
    console.error('return to original error', error)
    window.$message?.error('返回原用户失败')
    router.push('/login')
  }
}

function handleTenantSwitch({ key }: { key: string }) {
  const tenantId = Number(key)
  if (tenantId !== userStore.currentTenantId) {
    userStore.selectTenant(tenantId).then(() => {
      window.location.reload()
    })
  }
}

function handleUserMenuClick({ key }: { key: string }) {
  if (key === 'profile') {
    router.push('/profile')
  } else if (key === 'logout') {
    userStore.logout()
  }
}
</script>

<style scoped lang="less">
.header-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px 0 0;
  height: 100%;

  .left-section {
    display: flex;
    align-items: center;
    gap: 8px;

    .trigger {
      font-size: 18px;
      cursor: pointer;
      transition: color 0.3s;
      padding: 0 8px;
      margin-left: 0;

      &:hover {
        color: #F4511E;
      }
    }
  }

  .right-section {
    display: flex;
    align-items: center;
    gap: 16px;

    .quick-login-notice {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-right: 8px;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 0 8px;

      .username {
        font-size: 14px;
      }
    }
  }
}</style>
