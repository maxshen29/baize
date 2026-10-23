import { ref } from 'vue'

/**
 * 最近一次「页面加载 / 渲染」错误。
 * 由 main.ts 的全局 errorHandler 与 router.onError 写入，
 * 供 MainLayout 的兜底面板直接展示——白屏时不必翻控制台即可看到原因。
 */
export const lastAppError = ref('')

export function setAppError(msg: unknown) {
  const text = msg instanceof Error ? msg.message : String(msg ?? '')
  lastAppError.value = text.slice(0, 400)
}

export function clearAppError() {
  lastAppError.value = ''
}
