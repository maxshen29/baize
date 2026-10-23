import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as modulesApi from '@/api/modules'
import { hasPerm } from '@/utils/permission'

export interface ModuleInfo {
  code: string
  name: string
  description?: string
  version: string
  entry?: string
  api_prefix?: string
  status: string
  icon?: string
  order_index: number
}

// AI 应用「使用权限」约定码：app:<code>:use（与后端 MANIFEST.use_permission 一致）
export function appUsePerm(code: string): string {
  return `app:${code}:use`
}

export const useModuleStore = defineStore('modules', () => {
  const list = ref<ModuleInfo[]>([])

  async function fetchModules() {
    const res = await modulesApi.list()
    list.value = (res.data.data as ModuleInfo[])
      .filter((m) => m.status === 'enabled')
      .sort((a, b) => a.order_index - b.order_index)
    return list.value
  }

  // 当前用户有权使用的应用（按 app:<code>:use 权限过滤）
  const visibleList = computed(() =>
    list.value.filter((m) => hasPerm(appUsePerm(m.code))),
  )

  function enabled(code: string) {
    return list.value.some((m) => m.code === code)
  }

  function canUse(code: string) {
    return hasPerm(appUsePerm(code))
  }

  return { list, visibleList, fetchModules, enabled, canUse }
})
