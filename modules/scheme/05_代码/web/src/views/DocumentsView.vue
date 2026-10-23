<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listDocuments, uploadDocument, getDocPreview, deleteDocument, type ReferenceDocument } from '@/api'

const docs = ref<ReferenceDocument[]>([])
const loading = ref(false)
const preview = ref('')
const previewTitle = ref('')

// 对话框可见性：内容非空即显示，关闭时清空预览内容
const previewVisible = computed({
  get: () => Boolean(preview.value),
  set: (v) => { if (!v) preview.value = '' },
})

async function load() {
  loading.value = true
  try {
    docs.value = await listDocuments()
  } finally {
    loading.value = false
  }
}

async function onUpload(file: File) {
  try {
    await uploadDocument(file)
    ElMessage.success(`已导入并切片：${file.name}`)
    load()
  } catch (e: any) {
    ElMessage.error('导入失败：' + (e?.message || e))
  }
  return false // 阻止 el-upload 自动提交
}

async function showPreview(id: string, title: string) {
  previewTitle.value = title
  preview.value = await getDocPreview(id).then((r) => r.preview)
}

async function remove(id: string) {
  await deleteDocument(id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <h2>参考文档导入与管理</h2>
    <el-upload :auto-upload="false" :show-file-list="false" :on-change="(f: any) => onUpload(f.raw)">
      <el-button type="primary" icon="Upload">导入文档（docx / pdf / md）</el-button>
    </el-upload>
    <el-table :data="docs" v-loading="loading" style="margin-top: 12px">
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="source_type" label="类型" width="90" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ready' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="切片数" width="90" />
      <el-table-column prop="imported_at" label="导入时间" width="180" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link @click="showPreview(row.id, row.title)">预览</el-button>
          <el-button type="danger" link @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="previewVisible" :title="`解析预览：${previewTitle}`" width="60%">
      <pre style="max-height: 60vh; overflow: auto; white-space: pre-wrap">{{ preview }}</pre>
    </el-dialog>
  </div>
</template>
