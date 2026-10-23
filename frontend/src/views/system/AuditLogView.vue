<template>
  <div>
    <div class="toolbar">
      <el-input v-model="kw" placeholder="路径关键字" style="width: 200px" @keyup.enter="load" />
      <el-select v-model="method" placeholder="方法" clearable style="width: 120px">
        <el-option label="GET" value="GET" /><el-option label="POST" value="POST" />
        <el-option label="PUT" value="PUT" /><el-option label="DELETE" value="DELETE" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border>
      <el-table-column prop="username" label="操作人" width="120" />
      <el-table-column prop="method" label="方法" width="90" />
      <el-table-column prop="path" label="路径" />
      <el-table-column prop="module_code" label="模块" width="120" />
      <el-table-column prop="response_code" label="状态码" width="90" />
      <el-table-column prop="duration_ms" label="耗时(ms)" width="100" />
      <el-table-column prop="created_at" label="时间" />
    </el-table>
    <el-pagination class="pager" background layout="total, prev, pager, next" :total="total" :current-page="page" :page-size="pageSize" @current-change="onPage" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/modules'

const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const kw = ref('')
const method = ref('')

async function load() {
  loading.value = true
  try {
    const res = await api.listLogs({
      page: page.value, page_size: pageSize.value,
      path: kw.value || undefined, method: method.value || undefined,
    })
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
onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 12px; }
.pager { margin-top: 12px; justify-content: flex-end; display: flex; }
</style>
