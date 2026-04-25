import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { removeToken, setToken } from '@/utils'
import api from '@/api'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<Record<string, any>>({})
  const tenants = ref<any[]>([])
  const currentTenant = ref<any>(null)

  const userId = computed(() => userInfo.value?.id)
  const name = computed(() => userInfo.value?.username)
  const email = computed(() => userInfo.value?.email)
  const avatar = computed(() => userInfo.value?.avatar)
  const isSuperUser = computed(() => userInfo.value?.is_superuser)
  const isTenantAdmin = computed(() => {
    const roles = userInfo.value?.roles || []
    return roles.some((role: any) => role.code === 'tenant_admin')
  })
  const currentTenantId = computed(() => currentTenant.value?.id || userInfo.value?.current_tenant_id)

  async function getUserInfo() {
    try {
      const res: any = await api.getUserInfo()
      if (res.code === 401) {
        await logout()
        return
      }
      const { id, username, email: uEmail, avatar: uAvatar, roles, is_superuser, is_active, tenants: ts, current_tenant_id } = res.data
      userInfo.value = { id, username, email: uEmail, avatar: uAvatar, roles, is_superuser, is_active, current_tenant_id }
      tenants.value = ts || []
      if (current_tenant_id && ts) {
        currentTenant.value = ts.find((t: any) => t.id === current_tenant_id) || null
      }
      return res.data
    } catch (error) {
      return error
    }
  }

  async function logout() {
    removeToken()
    userInfo.value = {}
    tenants.value = []
    currentTenant.value = null
    router.push('/login')
  }

  // 退出登录但不跳转（用于快捷登录）
  async function logoutWithoutRedirect() {
    removeToken()
    userInfo.value = {}
    tenants.value = []
    currentTenant.value = null
  }

  function setUserInfo(info: Record<string, any> = {}) {
    userInfo.value = { ...userInfo.value, ...info }
  }

  function setCurrentTenant(tenant: any) {
    currentTenant.value = tenant
    if (tenant) {
      userInfo.value.current_tenant_id = tenant.id
    }
  }

  async function selectTenant(tenantId: number) {
    try {
      const res: any = await api.selectTenant({ tenant_id: tenantId })
      if (res.code === 200) {
        setToken(res.data.access_token)
        const tenant = tenants.value.find((t) => t.id === tenantId)
        setCurrentTenant(tenant)
        window.$message?.success('租户切换成功')
        return true
      }
      return false
    } catch (error) {
      console.error('选择租户失败', error)
      return false
    }
  }

  async function fetchMyTenants() {
    try {
      const res: any = await api.getMyTenants()
      tenants.value = res.data || []
      return tenants.value
    } catch (error) {
      return []
    }
  }

  return {
    userInfo,
    tenants,
    currentTenant,
    userId,
    name,
    email,
    avatar,
    isSuperUser,
    isTenantAdmin,
    currentTenantId,
    getUserInfo,
    logout,
    logoutWithoutRedirect,
    setUserInfo,
    setCurrentTenant,
    selectTenant,
    fetchMyTenants,
  }
})
