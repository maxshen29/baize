// 本地 token 存取
const ACCESS = 'baize_access'
const REFRESH = 'baize_refresh'

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS, access)
  localStorage.setItem(REFRESH, refresh)
}
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS)
}
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH)
}
export function clearTokens() {
  localStorage.removeItem(ACCESS)
  localStorage.removeItem(REFRESH)
}
export function parseJwt(access: string): any {
  try {
    return JSON.parse(atob(access.split('.')[1]))
  } catch {
    return null
  }
}
