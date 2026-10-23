import http from './http'

export function list() {
  return http.get('/modules')
}
export function register(body: any) {
  return http.post('/modules/register', body)
}
export function getModule(code: string) {
  return http.get(`/modules/${code}`)
}
export function setStatus(code: string, action: 'enable' | 'disable' | 'stop' | 'restart') {
  return http.post(`/modules/${code}/${action}`, {})
}
export function getConfig(code: string) {
  return http.get(`/modules/${code}/config`)
}
export function setConfig(code: string, items: any[]) {
  return http.put(`/modules/${code}/config`, { items })
}
export function getDependencies(code: string) {
  return http.get(`/modules/${code}/dependencies`)
}
export function unregister(code: string) {
  return http.delete(`/modules/${code}`)
}
export function listLogs(params: any) {
  return http.get('/audit/logs', { params })
}
