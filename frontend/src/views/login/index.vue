<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-header">
        <img src="/logo.svg" class="logo" />
        <h2>AI平台</h2>
      </div>

      <a-form ref="formRef" :model="formData" :rules="rules" @finish="handleLogin">
        <a-form-item name="username">
          <a-input v-model:value="formData.username" size="large" placeholder="" :maxlength="20" autofocus>
            <template #prefix>
              <UserOutlined />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item name="password">
          <a-input-password v-model:value="formData.password" size="large" placeholder="" :maxlength="20"
            @pressEnter="handleLogin">
            <template #prefix>
              <LockOutlined />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" size="large" block :loading="loading" html-type="submit">
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <!-- 租户选择弹窗 -->
    <a-modal v-model:open="showTenantModal" :mask-closable="false" title="选择租户" @ok="handleSelectTenant"
      @cancel="handleCancelTenant">
      <p class="mb-4 text-gray-600">您属于多个租户，请选择要登录的租户：</p>
      <a-select v-model:value="selectedTenantId" :options="tenantOptions" placeholder="请选择租户" style="width: 100%" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { setToken, removeToken } from '@/utils'
import api from '@/api'
import { useUserStore } from '@/store'
import { addDynamicRoutes } from '@/router'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const formData = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 租户选择相关
const showTenantModal = ref(false)
const tenantOptions = ref<any[]>([])
const selectedTenantId = ref<number | null>(null)
const pendingToken = ref('')

// 页面加载时检查是否有待处理的token（快捷登录/返回原用户）
onMounted(() => {
  const pendingAuth = localStorage.getItem('pending_auth')
  if (pendingAuth) {
    handlePendingAuth(pendingAuth)
  }
  // 初始化登录信息
  initLoginInfo()
})

// 加载租户列表并显示选择弹窗
async function loadTenantsAndShowModal(token: string) {
  pendingToken.value = token
  try {
    // 设置临时token以调用租户接口
    setToken(token)
    const res: any = await api.getTenantSelect()
    if (res.code === 200 && res.data?.length > 1) {
      tenantOptions.value = res.data.map((t: any) => ({ label: `${t.name} (${t.domain})`, value: t.id }))
      showTenantModal.value = true
      loading.value = false
      return true
    }
    // 如果只有一个租户或没有租户，直接完成登录
    return false
  } catch (error) {
    console.error('加载租户列表失败', error)
    return false
  }
}

// 处理待验证的登录信息
async function handlePendingAuth(authData: string) {
  try {
    loading.value = true
    const { token, currentTenantId, isQuickLogin, targetUser } = typeof authData === 'string' ? JSON.parse(authData) : authData

    // 清除待验证数据
    localStorage.removeItem('pending_auth')

    // 标记快捷登录模式
    if (isQuickLogin) {
      localStorage.setItem('quick_login_mode', 'true')
      localStorage.setItem('quick_login_target', targetUser)
    }

    // 检查是否需要选择租户
    if (!currentTenantId) {
      const needSelect = await loadTenantsAndShowModal(token)
      if (needSelect) {
        return
      }
    }

    // 直接完成登录
    await completeLogin(token)
  } catch (e) {
    console.error('handle pending auth error', e)
    window.$message?.error('登录失败')
    removeToken()
    loading.value = false
  }
}

// 标准登录
async function handleLogin() {
  const { username, password } = formData
  if (!username || !password) {
    window.$message?.warning('请输入用户名和密码')
    return
  }

  try {
    loading.value = true
    window.$message?.loading('正在验证...', 0)

    const res: any = await api.login({ username, password: password.toString() })
    localStorage.setItem('loginInfo', JSON.stringify({ username, password }))

    const { access_token, current_tenant_id } = res.data

    // 检查是否需要选择租户
    if (!current_tenant_id) {
      const needSelect = await loadTenantsAndShowModal(access_token)
      if (needSelect) {
        return
      }
    }

    await completeLogin(access_token)
  } catch (e: any) {
    console.error('login error', e)
    window.$message?.error(e.message || '登录失败')
    loading.value = false
  }
}

// 选择租户后完成登录
async function handleSelectTenant() {
  if (!selectedTenantId.value) {
    window.$message?.warning('请选择租户')
    return false
  }

  try {
    loading.value = true
    setToken(pendingToken.value)
    const res: any = await api.selectTenant({ tenant_id: selectedTenantId.value })
    await completeLogin(res.data.access_token)
    return true
  } catch (e: any) {
    console.error('select tenant error', e)
    window.$message?.error(e.message || '选择租户失败')
    removeToken()
    loading.value = false
    return false
  }
}

function handleCancelTenant() {
  removeToken()
  pendingToken.value = ''
  tenantOptions.value = []
  selectedTenantId.value = null
}

// 完成登录（统一入口）
async function completeLogin(token: string) {
  setToken(token)
  window.$message?.success('登录成功')
  await addDynamicRoutes()

  const redirect = route.query.redirect as string
  if (redirect) {
    const path = redirect
    delete route.query.redirect
    router.push({ path, query: route.query })
  } else {
    router.push('/')
  }
}

function initLoginInfo() {
  const localLoginInfo = localStorage.getItem('loginInfo')
  if (localLoginInfo) {
    const info = JSON.parse(localLoginInfo)
    formData.username = info.username || ''
    formData.password = info.password || ''
  }
}
</script>

<style scoped lang="less">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

  .login-box {
    width: 400px;
    padding: 40px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

    .login-header {
      text-align: center;
      margin-bottom: 32px;

      .logo {
        width: 64px;
        height: 64px;
        margin-bottom: 16px;
      }

      h2 {
        font-size: 24px;
        color: #333;
        margin-bottom: 8px;
      }
    }
  }
}
</style>
