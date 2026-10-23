<template>
  <el-tag :type="type" effect="light">{{ label }}</el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()
const map: Record<string, { type: 'success' | 'info' | 'warning' | 'danger'; label: string }> = {
  active: { type: 'success', label: '启用' },
  enabled: { type: 'success', label: '已启用' },
  disabled: { type: 'info', label: '禁用' },
  locked: { type: 'danger', label: '锁定' },
  registered: { type: 'warning', label: '已注册' },
  stopped: { type: 'info', label: '已停用' },
}
const type = computed(() => map[props.status]?.type || 'info')
const label = computed(() => map[props.status]?.label || props.status)
</script>
