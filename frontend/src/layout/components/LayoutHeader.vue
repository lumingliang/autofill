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

      <!-- 租户选择器 - 至少一个租户时才显示 -->
      <div v-if="tenantOptions.length >= 1" class="tenant-selector-wrapper">
        <a-select v-model:value="selectedTenantId" :placeholder="'选择租户'" :options="tenantOptions" :show-search="true"
          :filter-option="false" :allow-clear="false" :loading="tenantLoading" style="width: 180px"
          @search="handleTenantSearch" @change="handleTenantChange">
          <template #suffixIcon>
            <ClusterOutlined />
          </template>
          <template #notFoundContent>
            <a-empty :image="simpleImage" description="无匹配租户" />
          </template>
        </a-select>
      </div>

      <a-dropdown>
        <div class="user-info">
          <a-avatar :src="userStore.avatar" :size="32">
            <template #icon>
              <UserOutlined />
            </template>
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
import api from '@/api'
import { useAppStore, useUserStore } from '@/store'
import { setToken } from '@/utils'
import {
  ClusterOutlined,
  DownOutlined,
  LoginOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { Empty } from 'ant-design-vue'
import { debounce } from 'lodash-es'
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Breadcrumb from './Breadcrumb.vue'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

// 快捷登录相关
const isQuickLoginMode = ref(false)
const quickLoginTarget = ref('')

// 租户选择相关
const tenantLoading = ref(false)
const tenantOptions = ref<Array<{ label: string; value: number }>>([])
const selectedTenantId = ref<number | null>(null)
const isTenantLoaded = ref(false) // 防止重复加载

// 初始化选中的租户ID
watch(
  () => userStore.currentTenant,
  (tenant) => {
    selectedTenantId.value = tenant?.id || null
  },
  { immediate: true }
)

// 加载租户列表 - 统一使用后端接口
async function loadTenants(keyword: string = '') {
  // 如果已经加载过且没有搜索关键词，则不再加载
  if (isTenantLoaded.value && !keyword) {
    return
  }

  tenantLoading.value = true
  try {
    const res: any = await api.getTenantSelect({ keyword })
    if (res.code === 200) {
      tenantOptions.value = (res.data || []).map((t: any) => ({
        label: `${t.name} (${t.domain})`,
        value: t.id,
      }))
      if (!keyword) {
        isTenantLoaded.value = true
      }
    }
  } catch (error) {
    console.error('加载租户列表失败', error)
  } finally {
    tenantLoading.value = false
  }
}

// 防抖搜索
const handleTenantSearch = debounce((value: string) => {
  loadTenants(value)
}, 300)

// 租户切换 - 统一使用 selectTenant
async function handleTenantChange(value: number | null) {
  // 从 tenantOptions 中找到完整的租户对象
  const tenantObj = tenantOptions.value.find((t) => t.value === value)
  if (tenantObj) {
    const success = await userStore.selectTenant(value, { id: tenantObj.value, name: tenantObj.label.split(' (')[0], domain: tenantObj.label.match(/\((.*)\)/)?.[1] || '' })
    if (success) {
      // 租户切换成功后，刷新当前页面以加载新租户的数据
      router.go(0)
    }
  } else {
    const success = await userStore.selectTenant(value)
    if (success && value !== null) {
      // 租户切换成功后，刷新当前页面以加载新租户的数据
      router.go(0)
    }
  }
}

onMounted(() => {
  // 检查是否处于快捷登录模式
  const quickLoginMode = localStorage.getItem('quick_login_mode')
  const target = localStorage.getItem('quick_login_target')
  if (quickLoginMode === 'true' && target) {
    isQuickLoginMode.value = true
    quickLoginTarget.value = target
  }

  // 加载租户列表
  loadTenants()
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
    // 获取原用户信息
    setToken(originalToken)
    const userRes: any = await api.getUserInfo()

    if (userRes.code !== 200) {
      window.$message?.error('获取原用户信息失败')
      return
    }

    // 构建待验证的登录信息
    const pendingAuth = {
      token: originalToken,
      currentTenantId: userRes.data.current_tenant_id,
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

    .tenant-selector-wrapper {
      display: flex;
      align-items: center;

      :deep(.ant-select) {
        .ant-select-selector {
          border-radius: 4px;
        }
      }
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
}
</style>
