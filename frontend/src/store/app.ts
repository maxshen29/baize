import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as themeApi from '@/api/theme'
import { getAccessToken } from '@/utils/auth'

export interface ThemeOption {
  key: string
  name: string
  swatch: string
}

// 与 theme.css 中 :root[data-theme="..."] 块一一对应
export const THEMES: ThemeOption[] = [
  { key: 'mint', name: '薄荷青', swatch: 'linear-gradient(135deg,#34d399,#06b6d4)' },
  { key: 'ocean', name: '海洋蓝', swatch: 'linear-gradient(135deg,#22d3ee,#2563eb)' },
  { key: 'violet', name: '紫罗兰', swatch: 'linear-gradient(135deg,#a78bfa,#7c3aed)' },
  { key: 'rose', name: '玫红', swatch: 'linear-gradient(135deg,#f472b6,#e11d48)' },
  { key: 'amber', name: '琥珀金', swatch: 'linear-gradient(135deg,#fcd34d,#f59e0b)' },
  { key: 'dark', name: '暗夜', swatch: 'linear-gradient(135deg,#1f2937,#10b981)' },
]

const LS_KEY = 'baize-theme'
const DEFAULT_THEME = 'mint'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentTheme = ref<string>(DEFAULT_THEME)
  const defaultTheme = ref<string>(DEFAULT_THEME) // 管理员设定的平台默认

  function applyTheme(key: string) {
    const el = document.documentElement
    // 薄荷青即默认（:root），不设置 data-theme 属性
    if (key === 'mint') {
      el.removeAttribute('data-theme')
    } else {
      el.setAttribute('data-theme', key)
    }
    // 暗夜主题需启用 Element Plus 暗色变量
    if (key === 'dark') {
      el.classList.add('dark')
    } else {
      el.classList.remove('dark')
    }
  }

  // 用户手动选择（持久化到本地）
  function setTheme(key: string) {
    currentTheme.value = key
    try {
      localStorage.setItem(LS_KEY, key)
    } catch {
      /* ignore */
    }
    applyTheme(key)
  }

  // 启动时应用：优先本地选择，否则跟随平台默认
  function initTheme() {
    let saved: string | null = null
    try {
      saved = localStorage.getItem(LS_KEY)
    } catch {
      /* ignore */
    }
    const key = saved || defaultTheme.value || DEFAULT_THEME
    currentTheme.value = key
    applyTheme(key)
  }

  const themeLoaded = ref(false)

  // 拉取管理员设定的平台默认主题（不覆盖用户已保存的选择）。
  // 仅在已登录时请求，避免未登录时触发 401 → 跳登录页 → 重挂载的闪烁循环。
  async function loadDefaultTheme(force = false) {
    if (themeLoaded.value && !force) return
    if (!getAccessToken()) return
    try {
      const res = await themeApi.getDefault()
      const t = res.data?.data?.theme
      if (t) {
        defaultTheme.value = t
        let saved: string | null = null
        try {
          saved = localStorage.getItem(LS_KEY)
        } catch {
          /* ignore */
        }
        if (!saved) {
          currentTheme.value = t
          applyTheme(t)
        }
      }
      themeLoaded.value = true
    } catch {
      /* 忽略：主题为增强项，失败不应影响登录/使用 */
    }
  }

  const isDark = computed(() => currentTheme.value === 'dark')
  const currentThemeName = computed(
    () => THEMES.find((t) => t.key === currentTheme.value)?.name || '薄荷青',
  )

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    sidebarCollapsed,
    currentTheme,
    defaultTheme,
    isDark,
    currentThemeName,
    THEMES,
    setTheme,
    initTheme,
    loadDefaultTheme,
    toggleSidebar,
  }
})
