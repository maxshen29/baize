// 权限判断：基于 user store 中的 permissions 集合
import { useUserStore } from '@/store/user'

export function hasPerm(code: string): boolean {
  const store = useUserStore()
  if (!code) return true
  return store.permissions.includes(code)
}

// 角色判断
export function hasRole(code: string): boolean {
  const store = useUserStore()
  return store.roles.includes(code)
}
