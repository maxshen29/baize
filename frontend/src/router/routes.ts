import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import UserListView from '@/views/system/UserListView.vue'
import RoleListView from '@/views/system/RoleListView.vue'
import PermissionTree from '@/views/system/PermissionTree.vue'
import ModuleManageView from '@/views/system/ModuleManageView.vue'
import AuditLogView from '@/views/system/AuditLogView.vue'
import LlmManageView from '@/views/system/LlmManageView.vue'
import ThemeConfigView from '@/views/system/ThemeConfigView.vue'

export const staticRoutes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    name: 'layout',
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: DashboardView, meta: { title: '工作台' } },
      { path: 'system/users', name: 'sys-users', component: UserListView, meta: { title: '用户管理', perm: 'user:user:read' } },
      { path: 'system/roles', name: 'sys-roles', component: RoleListView, meta: { title: '角色管理', perm: 'perm:role:read' } },
      { path: 'system/permissions', name: 'sys-perms', component: PermissionTree, meta: { title: '权限管理', perm: 'perm:permission:read' } },
      { path: 'system/modules', name: 'sys-modules', component: ModuleManageView, meta: { title: '应用市场管理', perm: 'module:module:read' } },
      { path: 'system/audit', name: 'sys-audit', component: AuditLogView, meta: { title: '操作日志', perm: 'audit:log:read' } },
      { path: 'system/llm', name: 'sys-llm', component: LlmManageView, meta: { title: '大模型接入', perm: 'llm:provider:read' } },
      { path: 'system/theme', name: 'sys-theme', component: ThemeConfigView, meta: { title: '配色方案', perm: 'theme:config' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]
