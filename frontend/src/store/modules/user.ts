import api from '@/api'
import router from '@/router'
import { getSelectedTenantId, removeSelectedTenantId, removeToken, setSelectedTenantId } from '@/utils'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

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
      const { id, username, email: uEmail, avatar: uAvatar, roles, is_superuser, is_active, tenants: ts, current_tenant_id } = res.data || res
      userInfo.value = { id, username, email: uEmail, avatar: uAvatar, roles, is_superuser, is_active, current_tenant_id }
      tenants.value = ts || []

      // 恢复持久化的租户选择
      const savedTenantId = getSelectedTenantId()
      if (savedTenantId) {
        // 优先使用本地保存的租户ID（用户明确选择的）
        const savedTenant = ts?.find((t: any) => t.id === savedTenantId)
        if (savedTenant) {
          currentTenant.value = savedTenant
        } else {
          // 如果租户列表中没有该租户（如超管切换到普通租户），创建一个临时租户对象
          currentTenant.value = { id: savedTenantId, name: `租户${savedTenantId}`, domain: '' }
        }
      } else if (current_tenant_id && ts) {
        // 没有本地保存的租户ID时，使用后端返回的当前租户
        currentTenant.value = ts.find((t: any) => t.id === current_tenant_id) || null
      }
      return res.data || res
    } catch (error) {
      return error
    }
  }

  async function logout() {
    removeToken()
    removeSelectedTenantId()
    userInfo.value = {}
    tenants.value = []
    currentTenant.value = null
    router.push('/login')
  }

  // 退出登录但不跳转（用于快捷登录）
  async function logoutWithoutRedirect() {
    removeToken()
    removeSelectedTenantId()
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
      setSelectedTenantId(tenant.id)
    } else {
      removeSelectedTenantId()
    }
  }

  async function selectTenant(tenantId: number | null, tenantObj?: any) {
    try {
      if (tenantId === null) {
        // 清空租户选择（查询全部）
        setCurrentTenant(null)
        window.$message?.success('已切换到全部租户')
        // 不刷新页面，只更新状态
        return true
      }

      // 直接使用传入的租户对象或从列表中查找，不再调用后端接口
      const tenant = tenantObj || tenants.value.find((t) => t.id === tenantId)
      if (tenant) {
        setCurrentTenant(tenant)
        window.$message?.success('租户切换成功')
        // 不刷新页面，只更新状态
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
