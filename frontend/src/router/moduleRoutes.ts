import type { RouteRecordRaw, RouteComponent } from 'vue-router'
import type { ModuleInfo } from '@/store/modules'
import { appUsePerm } from '@/store/modules'

// 自动发现 frontend/src/views/modules/<app>/index.vue，作为 AI 应用的真实视图（直接集成，非 iframe）
const views = import.meta.glob('../views/modules/*/index.vue')

// 应用视图缺失时的兜底
const fallback = () => Promise.resolve({ template: '<div style="padding:24px">应用视图缺失</div>' })

// 依据已启用模块动态生成路由（挂在 MainLayout 下），并以使用权限守护
export function buildModuleRoutes(modules: ModuleInfo[]): RouteRecordRaw[] {
  return modules
    .filter((m) => m.status === 'enabled')
    .map((m): RouteRecordRaw => {
      const loader = views[`../views/modules/${m.code}/index.vue`]
      return {
        path: (m.entry || `/apps/${m.code}`).replace(/^\//, ''),
        name: `app-${m.code}`,
        component: (loader || fallback) as RouteComponent,
        props: () => ({ code: m.code, name: m.name }),
        meta: {
          title: m.name,
          moduleCode: m.code,
          icon: m.icon,
          perm: appUsePerm(m.code),
        },
      }
    })
}
