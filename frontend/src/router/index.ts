import { createRouter, createWebHistory } from 'vue-router'
import { staticRoutes } from './routes'
import { buildModuleRoutes } from './moduleRoutes'
import { useUserStore } from '@/store/user'
import { useModuleStore } from '@/store/modules'
import { getAccessToken } from '@/utils/auth'
import { hasPerm } from '@/utils/permission'

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
})

let injected = false

router.beforeEach(async (to) => {
  const token = getAccessToken()

  // 未登录 → 登录页
  if (!token && to.path !== '/login') return { path: '/login' }
  // 已登录访问登录页 → 工作台
  if (token && to.path === '/login') return { path: '/dashboard' }

  if (token) {
    const user = useUserStore()
    if (!user.isAuthenticated) {
      try {
        await user.fetchMe()
      } catch {
        return { path: '/login' }
      }
    }
    // 注入模块动态路由（仅一次）
    if (!injected) {
      const ms = useModuleStore()
      try {
        await ms.fetchModules()
      } catch {
        /* ignore */
      }
      buildModuleRoutes(ms.list).forEach((r) => router.addRoute('layout', r))
      injected = true
      return to.fullPath // 重试以匹配新注入的路由
    }
    // 路由级权限校验
    if (to.meta.perm && !hasPerm(to.meta.perm as string)) {
      return { path: '/dashboard' }
    }
  }
  return true
})

export default router
