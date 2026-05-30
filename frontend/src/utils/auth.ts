const TOKEN_KEY = 'access_token'
const TENANT_ID_KEY = 'selected_tenant_id'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

// 租户ID管理
export function getSelectedTenantId(): number | null {
  const id = localStorage.getItem(TENANT_ID_KEY)
  return id ? Number(id) : null
}

export function setSelectedTenantId(tenantId: number | null) {
  if (tenantId) {
    localStorage.setItem(TENANT_ID_KEY, String(tenantId))
  } else {
    localStorage.removeItem(TENANT_ID_KEY)
  }
}

export function removeSelectedTenantId() {
  localStorage.removeItem(TENANT_ID_KEY)
}

export function toLogin() {
  const { pathname } = window.location
  if (pathname !== '/login') {
    window.location.href = `/login?redirect=${encodeURIComponent(pathname)}`
  }
}
