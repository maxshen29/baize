import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 暗色主题变量（仅在 data-theme="dark" 时由 .dark 类激活）
import 'element-plus/theme-chalk/dark/css-vars.css'
// 清雅科技风设计系统（须在 element-plus 样式之后引入以覆盖主题变量）
import './styles/theme.css'
import './styles/global.css'
import './styles/tech.css'
import './styles/components.css'
import App from './App.vue'
import router from './router'
import { hasPerm } from './utils/permission'
import { getAccessToken } from './utils/auth'
import { setAppError } from './utils/appErrors'
import { useAppStore } from './store/app'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.directive('perm', {
  mounted(el, binding) {
    if (!hasPerm(binding.value)) el.style.display = 'none'
  },
  updated(el, binding) {
    el.style.display = hasPerm(binding.value) ? '' : 'none'
  },
})

// 应用配色方案：先按本地/平台默认初始化；
// 仅当已登录（存在 token）时才异步拉取管理员设定的默认主题，避免未登录 401 引发跳转闪烁。
const appStore = useAppStore()
appStore.initTheme()
if (getAccessToken()) appStore.loadDefaultTheme()

// 全局错误兜底：组件渲染异常 / 异步 chunk 加载失败不再静默白屏，而是明确提示
app.config.errorHandler = (err: any, _instance, info) => {
  console.error('[Baize] 渲染异常:', err, info)
  setAppError(`渲染异常：${err?.message || String(err)}`)
  try {
    ElMessage.error('页面渲染出错：' + (err?.message || String(err)))
  } catch {
    /* ignore */
  }
}
router.onError((err: any) => {
  console.error('[Baize] 路由加载失败:', err)
  setAppError(`页面加载失败：${err?.message || String(err)}`)
  try {
    ElMessage.error('页面加载失败：' + (err?.message || String(err)))
  } catch {
    /* ignore */
  }
})

app.mount('#app')
