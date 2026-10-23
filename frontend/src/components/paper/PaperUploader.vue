<template>
  <div class="pu">
    <el-upload
      class="pu-upload"
      :auto-upload="true"
      :show-file-list="false"
      accept=".pdf,.docx"
      :before-upload="beforeUpload"
      :http-request="doUpload"
    >
      <el-button type="primary" :icon="UploadFilled">上传 PDF / Word</el-button>
    </el-upload>
    <span class="pu-hint">PDF / DOCX（≤30MB）</span>

    <template v-if="allowUrl">
      <el-input v-model="url" class="pu-url" placeholder="或粘贴论文 URL（网页 / arXiv 等）">
        <template #append>
          <el-button :loading="loading" @click="doUrl">抓取</el-button>
        </template>
      </el-input>
    </template>

    <span v-if="loading" class="pu-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 解析中…
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { uploadPaper, fetchUrlPaper } from '@/api/paper'

const props = defineProps<{ code: string; allowUrl?: boolean }>()
const emit = defineEmits<{ (e: 'parsed', data: any): void }>()

const url = ref('')
const loading = ref(false)

function beforeUpload(file: File): boolean {
  const lower = file.name.toLowerCase()
  if (!lower.endsWith('.pdf') && !lower.endsWith('.docx')) {
    ElMessage.error('仅支持 PDF / DOCX')
    return false
  }
  if (file.size > 30 * 1024 * 1024) {
    ElMessage.error('文件过大（≤30MB）')
    return false
  }
  return true
}

async function doUpload(options: any) {
  const file: File = options.file
  loading.value = true
  try {
    const data = await uploadPaper(props.code, file)
    emit('parsed', data)
    ElMessage.success(`已解析：${data.filename}（${data.char_count} 字）`)
  } catch (e: any) {
    ElMessage.error(e?.message || '上传失败')
  } finally {
    loading.value = false
  }
}

async function doUrl() {
  const u = url.value.trim()
  if (!u) return
  loading.value = true
  try {
    const data = await fetchUrlPaper(props.code, u)
    emit('parsed', { ...data, filename: data.url })
    ElMessage.success(`已抓取：${data.char_count} 字`)
  } catch (e: any) {
    ElMessage.error(e?.message || '抓取失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.pu { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.pu-hint { font-size: 12px; color: var(--c-text-3); }
.pu-url { width: 320px; }
.pu-loading { font-size: 12px; color: var(--brand-emerald); }
</style>
