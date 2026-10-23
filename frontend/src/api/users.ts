import http from './http'

export function listUsers(params: any) {
  return http.get('/users', { params })
}
export function getUser(id: string) {
  return http.get(`/users/${id}`)
}
export function createUser(body: any) {
  return http.post('/users', body)
}
export function updateUser(id: string, body: any) {
  return http.patch(`/users/${id}`, body)
}
export function deleteUser(id: string) {
  return http.delete(`/users/${id}`)
}
export function setUserRoles(id: string, role_ids: string[]) {
  return http.put(`/users/${id}/roles`, { role_ids })
}
export function setStatus(id: string, action: 'enable' | 'disable' | 'lock' | 'unlock') {
  return http.post(`/users/${id}/${action}`, {})
}
