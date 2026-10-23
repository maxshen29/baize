<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" v-perm="'user:user:create'" @click="onCreate">新建用户</el-button>
      <el-input v-model="keyword" placeholder="搜索用户名/昵称" style="width: 220px" @keyup.enter="load" />
      <el-button @click="load">查询</el-button>
    </div>

    <DataTable :data="rows" :total="total" :page="page" :page-size="pageSize" :loading="loading" @page-change="onPage">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="昵称" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="状态">
        <template #default="{ row }"><StatusTag :status="row.status" /></template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button size="small" v-perm="'user:user:update'" @click="onStatus(row, 'enable')">启用</el-button>
          <el-button size="small" v-perm="'user:user:update'" @click="onStatus(row, 'disable')">禁用</el-button>
          <el-button size="small" type="danger" v-perm="'user:user:delete'" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </DataTable>

    <UserFormDialog v-model="dialogVisible" :edit="editUser" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataTable from '@/components/DataTable.vue'
import StatusTag from '@/components/StatusTag.vue'
import UserFormDialog from '@/components/UserFormDialog.vue'
import * as api from '@/api/users'

const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const keyword = ref('')
const dialogVisible = ref(false)
const editUser = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const res = await api.listUsers({ page: page.value, page_size: pageSize.value, keyword: keyword.value || undefined })
    rows.value = res.data.data.items
    total.value = res.data.data.total
  } finally {
    loading.value = false
  }
}
function onPage(p: number) {
  page.value = p
  load()
}
function onCreate() {
  editUser.value = null
  dialogVisible.value = true
}
async function onStatus(row: any, action: 'enable' | 'disable') {
  await api.setStatus(row.id, action)
  ElMessage.success('操作成功')
  load()
}
async function onDelete(row: any) {
  await ElMessageBox.confirm('确认删除该用户？', '提示', { type: 'warning' })
  await api.deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 12px; }
</style>
