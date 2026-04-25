const TOKEN_KEY = 'access_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function toLogin() {
  const { pathname } = window.location
  if (pathname !== '/login') {
    window.location.href = `/login?redirect=${encodeURIComponent(pathname)}`
  }
}
