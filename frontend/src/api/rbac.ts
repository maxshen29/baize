import http from './http'

export function listRoles() {
  return http.get('/roles')
}
export function createRole(body: any) {
  return http.post('/roles', body)
}
export function updateRole(id: string, body: any) {
  return http.patch(`/roles/${id}`, body)
}
export function deleteRole(id: string) {
  return http.delete(`/roles/${id}`)
}
export function rolePermissions(id: string) {
  return http.get(`/roles/${id}/permissions`)
}
export function setRolePermissions(id: string, permission_ids: string[]) {
  return http.put(`/roles/${id}/permissions`, { permission_ids })
}
export function listPermissions(module?: string) {
  return http.get('/permissions', { params: module ? { module } : {} })
}
export function permissionTree() {
  return http.get('/permissions/tree')
}
export function createPermission(body: any) {
  return http.post('/permissions', body)
}
