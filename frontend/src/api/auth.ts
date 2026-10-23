import http from './http'

export function login(account: string, password: string) {
  return http.post('/auth/login', { account, password })
}
export function register(body: any) {
  return http.post('/auth/register', body)
}
export function refresh(refresh_token: string) {
  return http.post('/auth/refresh', { refresh_token })
}
export function logout(refresh_token: string) {
  return http.post('/auth/logout', { refresh_token })
}
export function me() {
  return http.get('/auth/me')
}
