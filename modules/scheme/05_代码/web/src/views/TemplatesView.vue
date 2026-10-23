<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listTemplates, deleteTemplate, type Template } from '@/api'

const templates = ref<Template[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    templates.value = await listTemplates()
  } finally {
    loading.value = false
  }
}

async function remove(id: string) {
  await deleteTemplate(id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>参考结构模板</h2>
      <el-tag type="info">种子模板已随 schema.sql 初始化</el-tag>
    </div>
    <el-table :data="templates" v-loading="loading" style="margin-top: 12px">
      <el-table-column prop="type" label="类型" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="scenario" label="适用场景" />
      <el-table-column label="章节数" width="100">
        <template #default="{ row }">{{ row.sections?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="danger" link @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
      <el-table-column type="expand" label="章节" width="80">
        <template #default="{ row }">
          <ol>
            <li v-for="s in row.sections" :key="s.id">
              {{ s.title }} <el-tag size="small" v-if="s.required">必填</el-tag>
              <span style="color: #999">（{{ s.guidance || '无写作指引' }}）</span>
            </li>
          </ol>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
