import { defineStore } from 'pinia'
import { resetRouter } from '@/router'
import { useTagsStore, usePermissionStore } from '@/store'
import { removeToken, toLogin } from '@/utils'
import api from '@/api'

export const useUserStore = defineStore('user', {
  state() {
    return {
      userInfo: {},
      tenants: [], // 用户所属租户列表
      currentTenant: null, // 当前选中的租户
    }
  },
  getters: {
    userId() {
      return this.userInfo?.id
    },
    name() {
      return this.userInfo?.username
    },
    email() {
      return this.userInfo?.email
    },
    avatar() {
      return this.userInfo?.avatar
    },
    role() {
      return this.userInfo?.roles || []
    },
    isSuperUser() {
      return this.userInfo?.is_superuser
    },
    isActive() {
      return this.userInfo?.is_active
    },
    currentTenantId() {
      return this.currentTenant?.id || this.userInfo?.current_tenant_id
    },
  },
  actions: {
    async getUserInfo() {
      try {
        const res = await api.getUserInfo()
        if (res.code === 401) {
          this.logout()
          return
        }
        const { id, username, email, avatar, roles, is_superuser, is_active, tenants, current_tenant_id } = res.data
        this.userInfo = { id, username, email, avatar, roles, is_superuser, is_active, current_tenant_id }
        this.tenants = tenants || []
        // 设置当前租户
        if (current_tenant_id && tenants) {
          this.currentTenant = tenants.find(t => t.id === current_tenant_id) || null
        }
        return res.data
      } catch (error) {
        return error
      }
    },
    async logout() {
      const { resetTags } = useTagsStore()
      const { resetPermission } = usePermissionStore()
      removeToken()
      resetTags()
      resetPermission()
      resetRouter()
      this.$reset()
      toLogin()
    },
    setUserInfo(userInfo = {}) {
      this.userInfo = { ...this.userInfo, ...userInfo }
    },
    // 设置当前租户
    setCurrentTenant(tenant) {
      this.currentTenant = tenant
      if (tenant) {
        this.userInfo.current_tenant_id = tenant.id
      }
    },
    // 获取我的租户列表
    async fetchMyTenants() {
      try {
        const res = await api.getMyTenants()
        this.tenants = res.data || []
        return this.tenants
      } catch (error) {
        console.error('获取租户列表失败', error)
        return []
      }
    },
    // 选择租户
    async selectTenant(tenantId) {
      try {
        const res = await api.selectUserTenant({ tenant_id: tenantId })
        if (res.code === 200) {
          // 更新当前租户
          const tenant = this.tenants.find(t => t.id === tenantId)
          this.setCurrentTenant(tenant)
          $message?.success('租户切换成功')
          return true
        }
        return false
      } catch (error) {
        console.error('选择租户失败', error)
        return false
      }
    },
  },
})
