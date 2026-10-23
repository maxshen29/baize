<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listTasks,
  createTask,
  deleteTask,
  generateSection,
  getTask,
  listTemplates,
  exportTaskUrl,
  type WritingTask,
  type Template,
} from '@/api'

const tasks = ref<WritingTask[]>([])
const templates = ref<Template[]>([])
const current = ref<WritingTask | null>(null)
const genId = ref('')
const creating = ref(false)
const form = ref({ template_id: '', title: '新建方案', kb_scope: [] as string[] })

async function load() {
  tasks.value = await listTasks()
  templates.value = await listTemplates()
}

async function create() {
  creating.value = true
  try {
    const t = await createTask({ ...form.value })
    ElMessage.success('已创建撰写任务（基于模板生成大纲）')
    await open(t.id)
    load()
  } finally {
    creating.value = false
  }
}

async function open(id: string) {
  current.value = await getTask(id)
}

async function gen(sectionId: string) {
  if (!current.value) return
  genId.value = sectionId
  try {
    const r = await generateSection(current.value.id, sectionId)
    ElMessage.success(`生成完成，引用 ${r.used_hits} 条资料`)
    await open(current.value.id)
  } catch (e: any) {
    ElMessage.error('生成失败：' + (e?.message || e))
  } finally {
    genId.value = ''
  }
}

function doExport() {
  if (current.value) window.open(exportTaskUrl(current.value.id), '_blank')
}

async function remove(id: string) {
  await deleteTask(id)
  if (current.value?.id === id) current.value = null
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>撰写工作台</h2>
      <div>
        <el-select v-model="form.template_id" placeholder="选择模板" style="width: 160px; margin-right: 8px">
          <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-input v-model="form.title" style="width: 180px; margin-right: 8px" />
        <el-button type="primary" :loading="creating" @click="create">新建任务</el-button>
      </div>
    </div>

    <el-row :gutter="16" style="margin-top: 12px">
      <el-col :span="8">
        <el-card>
          <template #header>任务列表</template>
          <el-empty v-if="!tasks.length" description="暂无任务" />
          <div v-for="t in tasks" :key="t.id" style="margin-bottom: 8px">
            <el-button link @click="open(t.id)">{{ t.title }}</el-button>
            <el-button type="danger" link @click="remove(t.id)">删</el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card v-if="current">
          <template #header>
            <div style="display: flex; justify-content: space-between">
              <span>{{ current.title }}</span>
              <el-button size="small" type="success" @click="doExport">导出 Word</el-button>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item v-for="s in current.sections" :key="s.id">
              <div style="display: flex; justify-content: space-between; align-items: center">
                <strong>{{ s.title }}</strong>
                <el-button size="small" :loading="genId === s.id" @click="gen(s.id)">
                  {{ s.content ? '重新生成' : '生成' }}
                </el-button>
              </div>
              <el-tag size="small" :type="s.status === 'review' ? 'warning' : 'info'">{{ s.status }}</el-tag>
              <p v-if="s.content" style="white-space: pre-wrap; margin-top: 6px">{{ s.content }}</p>
              <p v-if="s.citations?.length" style="color: #999">引用：{{ s.citations.length }} 条</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>
        <el-empty v-else description="选择或新建一个撰写任务" />
      </el-col>
    </el-row>
  </div>
</template>
