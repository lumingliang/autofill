<template>
  <AppPage :show-footer="true" bg-cover :style="{ backgroundImage: `url(${bgImg})` }">
    <div
      style="transform: translateY(25px)"
      class="m-auto max-w-1500 min-w-345 f-c-c rounded-10 bg-white bg-opacity-60 p-15 card-shadow"
      dark:bg-dark
    >
      <div hidden w-380 px-20 py-35 md:block>
        <icon-custom-front-page pt-10 text-300 color-primary></icon-custom-front-page>
      </div>

      <div w-320 flex-col px-20 py-35>
        <h5 f-c-c text-24 font-normal color="#6a6a6a">
          <icon-custom-logo mr-10 text-50 color-primary />{{ $t('app_name') }}
        </h5>
        <div mt-30>
          <n-input
            v-model:value="loginInfo.username"
            autofocus
            class="h-50 items-center pl-10 text-16"
            placeholder="admin"
            :maxlength="20"
          />
        </div>
        <div mt-30>
          <n-input
            v-model:value="loginInfo.password"
            class="h-50 items-center pl-10 text-16"
            type="password"
            show-password-on="mousedown"
            placeholder="123456"
            :maxlength="20"
            @keypress.enter="handleLogin"
          />
        </div>

        <div mt-20>
          <n-button
            h-50
            w-full
            rounded-5
            text-16
            type="primary"
            :loading="loading"
            @click="handleLogin"
          >
            {{ $t('views.login.text_login') }}
          </n-button>
        </div>
      </div>
    </div>

    <!-- 租户选择弹窗 -->
    <n-modal
      v-model:show="showTenantModal"
      :mask-closable="false"
      preset="dialog"
      title="选择租户"
      positive-text="确认"
      negative-text="取消"
      @positive-click="handleSelectTenant"
      @negative-click="handleCancelTenant"
    >
      <div class="py-4">
        <p class="mb-4 text-gray-600">您属于多个租户，请选择要登录的租户：</p>
        <n-select
          v-model:value="selectedTenantId"
          :options="tenantOptions"
          placeholder="请选择租户"
          value-field="id"
          label-field="name"
        />
      </div>
    </n-modal>
  </AppPage>
</template>

<script setup>
import { lStorage, setToken, removeToken } from '@/utils'
import bgImg from '@/assets/images/login_bg.webp'
import api from '@/api'
import { addDynamicRoutes } from '@/router'
import { useI18n } from 'vue-i18n'
import { onMounted } from 'vue'

const router = useRouter()
const { query } = useRoute()
const { t } = useI18n({ useScope: 'global' })

const loginInfo = ref({ username: '', password: '' })
const loading = ref(false)

// 租户选择相关
const showTenantModal = ref(false)
const tenantOptions = ref([])
const selectedTenantId = ref(null)
const pendingToken = ref('')

// 页面加载时检查是否有待处理的token（快捷登录/返回原用户）
onMounted(() => {
  const pendingAuth = lStorage.get('pending_auth')
  if (pendingAuth) {
    handlePendingAuth(pendingAuth)
  }
})

// 处理待验证的登录信息
async function handlePendingAuth(authData) {
  try {
    loading.value = true
    const { token, tenants, needSelectTenant, currentTenantId, isQuickLogin, targetUser } = JSON.parse(authData)
    
    // 清除待验证数据
    lStorage.remove('pending_auth')
    
    // 标记快捷登录模式
    if (isQuickLogin) {
      lStorage.set('quick_login_mode', 'true')
      lStorage.set('quick_login_target', targetUser)
    }
    
    // 检查是否需要选择租户
    if (needSelectTenant && tenants?.length > 1 && !currentTenantId) {
      pendingToken.value = token
      tenantOptions.value = tenants
      showTenantModal.value = true
      loading.value = false
      return
    }
    
    // 直接完成登录
    await completeLogin(token)
  } catch (e) {
    console.error('handle pending auth error', e)
    $message.error('登录失败')
    removeToken()
    loading.value = false
  }
}

// 标准登录
async function handleLogin() {
  const { username, password } = loginInfo.value
  if (!username || !password) {
    $message.warning(t('views.login.message_input_username_password'))
    return
  }
  
  try {
    loading.value = true
    $message.loading(t('views.login.message_verifying'))
    
    const res = await api.login({ username, password: password.toString() })
    lStorage.set('loginInfo', { username, password })
    
    const { access_token, tenants, need_select_tenant, current_tenant_id } = res.data
    
    // 检查是否需要选择租户
    if (need_select_tenant && tenants?.length > 1 && !current_tenant_id) {
      pendingToken.value = access_token
      tenantOptions.value = tenants
      showTenantModal.value = true
      loading.value = false
      return
    }
    
    await completeLogin(access_token)
  } catch (e) {
    console.error('login error', e)
    $message.error(e.message || '登录失败')
    loading.value = false
  }
}

// 选择租户后完成登录
async function handleSelectTenant() {
  if (!selectedTenantId.value) {
    $message.warning('请选择租户')
    return false
  }
  
  try {
    loading.value = true
    setToken(pendingToken.value)
    const res = await api.selectTenant({ tenant_id: selectedTenantId.value })
    await completeLogin(res.data.access_token)
    return true
  } catch (e) {
    console.error('select tenant error', e)
    $message.error(e.message || '选择租户失败')
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
async function completeLogin(token) {
  setToken(token)
  $message.success(t('views.login.message_login_success'))
  await addDynamicRoutes()
  
  if (query.redirect) {
    const path = query.redirect
    Reflect.deleteProperty(query, 'redirect')
    router.push({ path, query })
  } else {
    router.push('/')
  }
}

function initLoginInfo() {
  const localLoginInfo = lStorage.get('loginInfo')
  if (localLoginInfo) {
    loginInfo.value.username = localLoginInfo.username || ''
    loginInfo.value.password = localLoginInfo.password || ''
  }
}

initLoginInfo()
</script>
