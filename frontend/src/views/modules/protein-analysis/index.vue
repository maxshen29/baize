<template>
  <!-- 蛋白质界面分析（AbInterface X）已作为平台内的真实 Vue 视图集成：
       挂载时把原始工具 markup 注入容器、加载 3Dmol 引擎并运行分析引擎，
       不再是 iframe 静态托管。 -->
  <div ref="root" class="abx-root"></div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import htmlTemplate from './template.html?raw'
// @ts-ignore 引擎为纯 JS（迁移自原单文件工具），无类型声明
import { runEngine, cleanupEngine } from './engine'

// 平台路由会传入 code / name / entry（保持兼容，组件自身不依赖）
defineProps({
  code: { type: String, default: 'protein-analysis' },
  name: { type: String, default: '' },
  entry: { type: String, default: '' },
})

const root = ref(null)

// 加载 3Dmol.js：主源不可达时依次回退到公共镜像。
// 注意：Promise 必须在「加载成功」时 resolve，否则引擎的 __molReady.then 永不触发，
// 会一直停在「正在加载 3D 引擎…」状态。
function load3Dmol() {
  if (typeof window !== 'undefined' && window.$3Dmol && window.$3Dmol.createViewer) {
    return Promise.resolve(true)
  }
  const SRC = [
    'https://3Dmol.org/build/3Dmol-min.js',
    'https://cdn.jsdelivr.net/npm/3dmol@2/build/3Dmol-min.js',
    'https://unpkg.com/3dmol@2/build/3Dmol-min.js',
    'https://fastly.jsdelivr.net/npm/3dmol@2/build/3Dmol-min.js',
  ]
  return new Promise((resolve) => {
    let i = 0
    const next = () => {
      if (i >= SRC.length) {
        resolve(false)
        return
      }
      const s = document.createElement('script')
      s.async = true
      s.src = SRC[i++]
      s.onload = () => {
        // 该源没提供 $3Dmol（或加载到错误内容）→ 清理并尝试下一个镜像
        if (window.$3Dmol && window.$3Dmol.createViewer) {
          resolve(true)
        } else {
          s.remove()
          next()
        }
      }
      s.onerror = () => {
        s.remove()
        next()
      }
      document.head.appendChild(s)
    }
    next()
  })
}

onMounted(() => {
  if (!root.value) return
  try {
    // 注入原始工具 DOM
    root.value.innerHTML = htmlTemplate
    // 先约定引擎就绪 Promise，再启动引擎（引擎内部会读取 window.__molReady）
    window.__molReady = load3Dmol()
    runEngine()
  } catch (e) {
    // 引擎初始化异常不应连带影响平台：就地提示，避免整页空白
    console.error('[protein-analysis] 引擎初始化失败：', e)
    if (root.value) {
      root.value.innerHTML =
        '<div style="padding:28px;color:#8aab9f">分析引擎初始化失败，请刷新页面重试（详情见浏览器控制台）。</div>'
    }
  }
})

onUnmounted(() => {
  // 移除引擎在 document/window 上注册的全局监听，避免 SPA 重复挂载造成事件重复绑定。
  // 清理过程即便抛错也必须吞掉：否则会中断路由切换（离开本应用时导致下一个应用白屏）。
  try {
    cleanupEngine()
  } catch (e) {
    console.error('[protein-analysis] 清理全局监听失败：', e)
  }
  try {
    delete window.__molReady
  } catch (e) {
    /* noop */
  }
  // 主动清空容器，尽快释放 DOM 与 WebGL 上下文
  try {
    if (root.value) root.value.innerHTML = ''
  } catch (e) {
    /* noop */
  }
})
</script>

<style src="./abx.css"></style>
