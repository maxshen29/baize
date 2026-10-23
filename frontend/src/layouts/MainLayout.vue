<template>
  <el-container class="layout tech-bg">
    <!-- 背景悬浮微光球（视差装饰） -->
    <div class="layout-orbs" aria-hidden="true">
      <span class="orb orb--mint orb--slow" style="width: 260px; height: 260px; top: -60px; right: -40px"></span>
      <span class="orb orb--cyan orb--slower" style="width: 220px; height: 220px; bottom: 40px; left: 240px"></span>
      <span class="orb orb--emerald orb--slow" style="width: 180px; height: 180px; top: 38%; right: 28%"></span>
    </div>

    <!-- 侧边栏：浅色薄荷清新 -->
    <el-aside width="236px" class="aside">
      <div class="logo">
        <BrandLogo :size="34" title="白泽" subtitle="AI 应用平台" :title-size="17" />
        <span class="spark"></span>
      </div>
      <el-menu :default-active="activeMenu" router class="menu" :unique-opened="false">
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon><span>工作台</span>
        </el-menu-item>
        <el-sub-menu index="system">
          <template #title><el-icon><Setting /></el-icon><span>系统管理</span></template>
          <el-menu-item v-perm="'user:user:read'" index="/system/users">用户管理</el-menu-item>
          <el-menu-item v-perm="'perm:role:read'" index="/system/roles">角色管理</el-menu-item>
          <el-menu-item v-perm="'perm:permission:read'" index="/system/permissions">权限管理</el-menu-item>
          <el-menu-item v-perm="'module:module:read'" index="/system/modules">应用市场管理</el-menu-item>
          <el-menu-item v-perm="'audit:log:read'" index="/system/audit">操作日志</el-menu-item>
          <el-menu-item v-perm="'llm:provider:read'" index="/system/llm">大模型接入</el-menu-item>
          <el-menu-item v-perm="'theme:config'" index="/system/theme">配色方案</el-menu-item>
        </el-sub-menu>
        <el-sub-menu v-if="moduleStore.visibleList.length" index="apps">
          <template #title><el-icon><Shop /></el-icon><span>AI 应用市场</span></template>
          <el-menu-item
            v-for="m in moduleStore.visibleList"
            :key="m.code"
            :index="(m.entry || '')"
          >
            <el-icon v-if="m.icon && iconMap[m.icon]"><component :is="iconMap[m.icon]" /></el-icon>
            <el-icon v-else><Cpu /></el-icon>
            <span>{{ m.name }}</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
      <div class="aside-foot">
        <span class="spark"></span>
        <span class="aside-foot__txt">白泽 · AI 应用平台</span>
      </div>
    </el-aside>

    <el-container>
      <!-- 头部：玻璃拟态 -->
      <el-header class="header glass">
        <div class="header-left">
          <span class="crumb-dot"></span>
          <span class="title gradient-text">{{ title }}</span>
        </div>
        <div class="right">
          <el-dropdown trigger="click" @command="onTheme" popper-class="theme-pop">
            <el-button text class="theme-btn" title="切换配色方案">
              <span class="theme-dot" :style="{ background: currentSwatch }"></span>
              <span class="theme-name">{{ appStore.currentThemeName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <div class="theme-menu">
                <div
                  v-for="t in THEMES"
                  :key="t.key"
                  class="theme-item"
                  :class="{ active: t.key === appStore.currentTheme }"
                  @click="onTheme(t.key)"
                >
                  <span class="theme-dot" :style="{ background: t.swatch }"></span>
                  <span>{{ t.name }}</span>
                  <el-icon v-if="t.key === appStore.currentTheme" class="tick"><CircleCheck /></el-icon>
                </div>
              </div>
            </template>
          </el-dropdown>
          <el-tooltip content="当前账户" placement="bottom">
            <div class="user">
              <el-avatar :size="32" class="user-avatar">{{ avatarText }}</el-avatar>
              <span class="user-name">{{ userStore.displayName }}</span>
            </div>
          </el-tooltip>
          <el-button class="logout-btn" text type="primary" @click="onLogout">
            <el-icon><SwitchButton /></el-icon>退出
          </el-button>
        </div>
      </el-header>

      <el-main class="main">
        <div class="view-wrap">
          <!-- ⚠ 切勿在此包裹 <transition mode="out-in">：
               AI 应用视图是 import.meta.glob 生成的【异步组件】，
               与 out-in 过渡组合时会出现「离开过渡已完成、但异步组件尚未挂载完成」
               的竞态 → 路由容器最终 0 个子元素 → 整页空白（静态路由不受影响，
               这正是"只有 /apps/* 白屏"的原因）。视图内部已有 .rise-in 入场动画，
               转场观感不受影响。 -->
          <router-view v-slot="{ Component }">
            <component :is="Component" :key="route.path" />
          </router-view>

          <!-- 兜底提示：视图确实没渲染出内容时，给出可操作信息，而不是留白 -->
          <div v-if="viewFailed" class="view-fallback">
            <div class="view-fallback__t">页面未能渲染：{{ failedRoute }}</div>
            <div v-if="loadError" class="view-fallback__err">{{ loadError }}</div>
            <div class="view-fallback__s">
              该应用视图（异步组件）未能加载或挂载。请查看浏览器控制台 Network/Console，
              或到「系统管理 → 应用市场管理」确认应用状态是否启用。
            </div>
            <el-button size="small" type="primary" @click="router.push('/dashboard')">返回工作台</el-button>
          </div>
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  DataLine, Setting, Shop, Cpu, SwitchButton,
  DataAnalysis, Coin, MagicStick, ChatDotRound, ArrowDown, CircleCheck, Connection,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { useModuleStore } from '@/store/modules'
import { useAppStore, THEMES } from '@/store/app'
import BrandLogo from '@/components/BrandLogo.vue'
import { lastAppError, clearAppError } from '@/utils/appErrors'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const moduleStore = useModuleStore()
const appStore = useAppStore()

// 应用图标映射（manifest.icon → Element Plus 图标组件）
const iconMap: Record<string, any> = {
  DataAnalysis,
  Coin,
  MagicStick,
  ChatDotRound,
  Connection,
}

const activeMenu = computed(() => route.path)
const title = computed(() => (route.meta.title as string) || '白泽 AI 应用平台')
const avatarText = computed(() => (userStore.displayName || '白').slice(0, 1).toUpperCase())
const currentSwatch = computed(
  () => THEMES.find((t) => t.key === appStore.currentTheme)?.swatch || THEMES[0].swatch,
)

function onTheme(key: string) {
  appStore.setTheme(key)
}

async function onLogout() {
  await userStore.logout()
  router.push('/login')
}

// 进入已登录区域后，再拉取管理员设定的平台默认配色（未自选用户跟随）
onMounted(() => {
  appStore.loadDefaultTheme()
})

// 临时诊断（用于定位「切换页面后空白」）：路由切换后探测视图容器是否真的渲染出内容。
// 输出可区分四种成因：
//   ① matched 为空            → 路由未匹配（模块未注册/未注入）
//   ② 子元素数量 0            → 组件未挂载（setup/render 抛错或 chunk 加载失败）
//   ③ 子元素尺寸为 0          → 视图根节点没有高度
//   ④ 有尺寸却仍看不到        → 被其他元素遮盖
const viewFailed = ref(false)
const failedRoute = ref('')
const loadError = computed(() => lastAppError.value)

router.beforeEach(() => {
  viewFailed.value = false
  failedRoute.value = ''
  clearAppError()
})

router.afterEach((to) => {
  window.setTimeout(() => {
    const wrap = document.querySelector('.view-wrap') as HTMLElement | null
    if (!wrap) return
    const kids = Array.from(wrap.children).filter(
      (el) => !el.classList.contains('view-fallback'),
    ) as HTMLElement[]
    const visible = kids.some((el) => el.offsetHeight > 4 && el.offsetWidth > 4)
    if (visible) return
    viewFailed.value = true
    failedRoute.value = to.fullPath
    const matched = to.matched.map((r) => String(r.name || r.path))
    const detail = {
      route: to.fullPath,
      name: String(to.name || '-'),
      matched,
      wrapSize: `${wrap.clientWidth}x${wrap.clientHeight}`,
      childCount: kids.length,
      children: kids.map((el) => `${el.tagName.toLowerCase()}.${el.className} ${el.offsetWidth}x${el.offsetHeight}`),
      htmlHead: wrap.innerHTML.slice(0, 200),
    }
    console.warn('[Baize] 视图疑似空白：', detail)
    ElMessage.warning(
      `页面疑似未渲染 ${to.fullPath}｜matched=${matched.join('>') || '无'}｜子元素=${kids.length}`,
    )
  }, 600)
})
</script>

<style scoped>
.layout { height: 100vh; overflow: hidden; }

/* ---- 背景微光球 ---- */
.layout-orbs { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }

/* ---- 侧边栏（浅色清新：白 → 薄荷）---- */
.aside {
  position: relative;
  z-index: 1;
  background: linear-gradient(180deg, var(--c-side-1) 0%, var(--c-side-2) 100%);
  box-shadow: var(--shadow-side);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.aside::before {
  content: "";
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(16, 185, 129, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(16, 185, 129, 0.05) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: linear-gradient(180deg, #000, transparent 85%);
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 85%);
  pointer-events: none;
}

.logo {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 16px;
  font-size: 18px;
  font-weight: 700;
}
.logo .spark { margin-left: auto; }

/* Element Plus 浅色菜单主题覆盖 */
.menu {
  flex: 1;
  border-right: none;
  background: transparent !important;
  --el-menu-text-color: var(--c-text-2);
  --el-menu-active-color: var(--brand-emerald);
  --el-menu-hover-bg-color: rgba(16, 185, 129, 0.1);
  --el-menu-item-height: 48px;
  --el-menu-sub-item-height: 44px;
}
.menu :deep(.el-menu-item),
.menu :deep(.el-sub-menu__title) {
  border-radius: 10px;
  margin: 4px 10px;
  color: var(--c-text-2);
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}
.menu :deep(.el-menu-item.is-active) {
  position: relative;
  color: var(--brand-emerald) !important;
  background: var(--brand-grad-soft);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand-emerald), 0 6px 18px rgba(16, 185, 129, 0.14);
}
.menu :deep(.el-menu-item.is-active)::after {
  content: "";
  position: absolute;
  right: 12px; top: 50%;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--brand-mint);
  box-shadow: 0 0 10px 2px var(--brand-mint);
  transform: translateY(-50%);
  animation: glow-pulse 2.2s ease-in-out infinite;
}
.menu :deep(.el-sub-menu__title) { color: var(--c-text-2); }
.menu :deep(.el-menu--popup) { background: var(--c-surface) !important; border: 1px solid var(--c-border); }
.menu :deep(.el-menu-item:hover),
.menu :deep(.el-sub-menu__title:hover) { color: var(--brand-emerald) !important; }

.aside-foot {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 12px;
  color: var(--c-text-3);
  border-top: 1px solid var(--c-border);
}

/* ---- 头部 ---- */
.header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 22px;
  border-bottom: 1px solid var(--c-border);
  border-radius: 0 0 16px 16px;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.crumb-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--brand-grad);
  box-shadow: 0 0 10px 2px var(--brand-mint);
}
.title { font-size: 17px; font-weight: 600; }
.right { display: flex; align-items: center; gap: 14px; }
.user { display: flex; align-items: center; gap: 8px; cursor: default; }
.user-avatar {
  background: var(--brand-grad) !important;
  color: #fff; font-weight: 600;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.32);
}
.user-name { color: var(--c-text-2); font-size: 13px; }
.logout-btn { transition: transform var(--dur-fast) var(--ease); }
.logout-btn:hover { transform: translateX(-2px); }

/* ---- 主题切换器 ---- */
.theme-btn { display: flex; align-items: center; gap: 6px; color: var(--c-text-2); margin-right: 2px; }
.theme-btn:hover { color: var(--brand-emerald); }
.theme-dot { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08); }
.theme-name { font-size: 13px; }
.theme-menu { padding: 6px; min-width: 168px; }
.theme-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; cursor: pointer; color: var(--c-text-1); font-size: 13px; transition: background var(--dur-fast) var(--ease); }
.theme-item:hover { background: var(--c-surface-2); }
.theme-item.active { color: var(--brand-emerald); font-weight: 600; }
.theme-item .tick { margin-left: auto; color: var(--brand-emerald); }

/* ---- 内容区 ---- */
/* 关键：为「应用视图」提供【确定高度】的定位画布。
   应用根节点多为 position:absolute; inset:0（自身不贡献流内高度），
   若承载容器高度依赖百分比或内容，切换应用时会塌陷为 0 → 整页空白。
   做法：让 .main 成为纵向弹性容器，.view-wrap 作为唯一弹性子项自动填满其确定高度——
   · 视图无流内高度（绝对定位）→ flex-basis=0 后被撑满，应用铺满；
   · 视图为普通文档流且很长 → flex-basis=auto 按内容撑开，由 .main 滚动。
   注意 .view-wrap 仍为 display:block，不改动任何子视图的内部布局。 */
.main { position: relative; z-index: 1; padding: 20px 22px; overflow-y: auto; display: flex; flex-direction: column; }
/* .view-wrap 先拿到确定高度；其直接子元素（各视图根节点）再由 flex 强制撑满，
   使各应用视图【不再依赖自身 height:100% 能否解析】：
   · 短内容视图 → 撑满容器；长内容视图 → 按内容撑开，由 .main 滚动；
   · 绝对定位的视图根（position:absolute; inset:0）照常铺满（flex 对其无效但不影响）。 */
.view-wrap { position: relative; flex: 1 0 auto; display: flex; flex-direction: column; }
.view-wrap > * { flex: 1 0 auto; min-width: 0; }

/* 视图未渲染时的兜底提示（不占满整屏，紧贴顶部） */
.view-fallback {
  flex: 0 0 auto;
  padding: 18px 20px;
  border: 1px dashed var(--c-border-strong, #c4e6da);
  border-radius: var(--radius-lg, 12px);
  background: var(--c-surface-2, #fff);
  color: var(--c-text-2);
}
.view-fallback__t { font-weight: 600; color: var(--c-text-1); margin-bottom: 6px; }
.view-fallback__s { font-size: 12.5px; line-height: 1.7; margin-bottom: 12px; }
.view-fallback__err {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(244, 63, 94, 0.08);
  color: #b91c1c;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  word-break: break-all;
}
</style>
