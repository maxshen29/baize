<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" v-perm="'perm:role:create'" @click="onCreate">新建角色</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="code" label="编码" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="系统">
        <template #default="{ row }"><el-tag v-if="row.is_system" type="warning">系统</el-tag><span v-else>—</span></template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" v-perm="'perm:role:update'" @click="onPerm(row)">权限</el-button>
          <el-button size="small" type="danger" v-perm="'perm:role:delete'" :disabled="row.is_system" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <RolePermissionDrawer v-model="drawer" :role="current" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import RolePermissionDrawer from '@/components/RolePermissionDrawer.vue'
import * as api from '@/api/rbac'

const rows = ref<any[]>([])
const loading = ref(false)
const drawer = ref(false)
const current = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const res = await api.listRoles()
    rows.value = res.data.data
  } finally {
    loading.value = false
  }
}
function onCreate() {
  ElMessage.info('可复用权限抽屉创建（演示略）')
}
function onPerm(row: any) {
  current.value = row
  drawer.value = true
}
async function onDelete(row: any) {
  await ElMessageBox.confirm('确认删除该角色？', '提示', { type: 'warning' })
  await api.deleteRole(row.id)
  ElMessage.success('已删除')
  load()
}
onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 12px; }
</style>
