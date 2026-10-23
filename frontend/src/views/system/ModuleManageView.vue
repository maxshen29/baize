<template>
  <div>
    <div class="toolbar">
      <span class="toolbar__title gradient-text">AI 应用市场</span>
      <span class="toolbar__hint">应用随 backend/modules 自动注册，仅对拥有「使用权限」的用户开放</span>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border class="market-table">
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="应用名称" min-width="140" />
      <el-table-column prop="version" label="版本" width="90" />
      <el-table-column prop="entry" label="入口路由" min-width="150" />
      <el-table-column label="使用权限" min-width="170">
        <template #default="{ row }"><el-tag size="small" effect="light">app:{{ row.code }}:use</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }"><StatusTag :status="row.status" /></template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button size="small" v-perm="'module:module:update'" @click="onStatus(row, 'enable')">启用</el-button>
          <el-button size="small" v-perm="'module:module:update'" @click="onStatus(row, 'disable')">禁用</el-button>
          <el-button size="small" v-perm="'module:module:update'" @click="onStatus(row, 'stop')">停用</el-button>
          <el-button size="small" type="primary" link @click="openApp(row)">打开</el-button>
        </template>
      </el-table-column>
    </el-table>

    <ModuleConfigForm v-model="cfgVisible" :module="current" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import StatusTag from '@/components/StatusTag.vue'
import ModuleConfigForm from '@/components/ModuleConfigForm.vue'
import * as api from '@/api/modules'

const router = useRouter()
const rows = ref<any[]>([])
const loading = ref(false)
const cfgVisible = ref(false)
const current = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const res = await api.list()
    rows.value = res.data.data
  } finally {
    loading.value = false
  }
}
async function onStatus(row: any, action: 'enable' | 'disable' | 'stop') {
  await api.setStatus(row.code, action)
  ElMessage.success('操作成功')
  load()
}
function openApp(row: any) {
  if (row.status !== 'enabled') {
    ElMessage.warning('请先启用该应用')
    return
  }
  router.push(row.entry || `/apps/${row.code}`)
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.toolbar__title { font-size: 18px; font-weight: 700; }
.toolbar__hint { color: var(--c-text-3); font-size: 12px; }
.market-table { border-radius: var(--radius-lg); overflow: hidden; }
</style>
