<template>
  <el-card>
    <template #header>权限点总览（按模块）</template>
    <el-tree :data="treeData" :props="{ label: 'label', children: 'children' }" default-expand-all v-loading="loading">
      <template #default="{ data }">
        <span>{{ data.label }}</span>
        <el-tag v-if="data.code" size="small" class="code">{{ data.code }}</el-tag>
      </template>
    </el-tree>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/rbac'

const treeData = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api.permissionTree()
    const tree: any[] = []
    for (const [mod, perms] of Object.entries(res.data.data)) {
      tree.push({
        label: mod,
        children: (perms as any[]).map((p) => ({ label: p.name, code: p.code })),
      })
    }
    treeData.value = tree
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.code { margin-left: 8px; }
</style>
