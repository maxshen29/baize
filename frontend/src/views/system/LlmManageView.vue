<template>
  <div class="page">
    <el-card class="panel tech-card" shadow="never">
      <template #header>
        <div class="panel-head">
          <div>
            <h2 class="panel-title gradient-text">大模型接入管理</h2>
            <p class="panel-sub">按 OpenAI 兼容规范（/v1/chat/completions、/v1/models）接入并链接大模型服务。</p>
          </div>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增接入</el-button>
        </div>
      </template>

      <el-table :data="rows" v-loading="loading" class="tbl" row-key="id" empty-text="尚未接入任何大模型">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="base_url" label="API 基地址" min-width="220" show-overflow-tooltip />
        <el-table-column prop="model" label="默认模型" min-width="140" />
        <el-table-column label="默认" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" effect="dark" size="small">默认</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="160" show-overflow-tooltip>
          <template #default="{ row }"><span class="muted">{{ row.notes || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Connection" @click="test(row)">测试</el-button>
            <el-button v-if="!row.is_default" link type="success" @click="setDefault(row)">设为默认</el-button>
            <el-button link type="warning" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="editing ? '编辑接入' : '新增接入'" width="540px" destroy-on-close>
      <el-form :model="form" label-width="96px" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如：本地 Ollama / OpenAI / DeepSeek" />
        </el-form-item>
        <el-form-item label="API 基地址">
          <el-input v-model="form.base_url" placeholder="https://api.openai.com/v1 或 http://localhost:11434/v1" />
          <div class="hint">填写到 /v1 的地址；若为 /v1/models、/v1/chat/completions 的上级目录。</div>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="Bearer 令牌（本地服务可填任意非空串）" />
        </el-form-item>
        <el-form-item label="默认模型">
          <el-input v-model="form.model" placeholder="gpt-3.5-turbo / deepseek-chat / qwen2.5-7b ..." />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Connection, Edit, Delete } from '@element-plus/icons-vue'
import * as llmApi from '@/api/llm'
import type { LlmProvider, ProviderInput } from '@/api/llm'

const rows = ref<LlmProvider[]>([])
const loading = ref(false)
const dialog = ref(false)
const editing = ref<string | null>(null)
const saving = ref(false)

const emptyForm: ProviderInput & { notes: string | null } = {
  name: '',
  base_url: '',
  api_key: '',
  model: 'gpt-3.5-turbo',
  is_default: false,
  notes: null,
}
const form = reactive({ ...emptyForm })

async function load() {
  loading.value = true
  try {
    const res = await llmApi.listProviders()
    rows.value = (res.data.data as LlmProvider[]) || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, emptyForm)
  dialog.value = true
}

function openEdit(row: LlmProvider) {
  editing.value = row.id
  Object.assign(form, {
    name: row.name,
    base_url: row.base_url,
    api_key: '',
    model: row.model,
    is_default: row.is_default,
    notes: row.notes ?? null,
  })
  dialog.value = true
}

async function save() {
  if (!form.name || !form.base_url || !form.model) {
    ElMessage.warning('请填写名称、基地址与默认模型')
    return
  }
  // 编辑时若未改密钥则保留原值：传占位空串会被后端覆盖为空，故编辑且未填时回退为原值
  const payload: ProviderInput = {
    name: form.name,
    base_url: form.base_url,
    api_key: form.api_key,
    model: form.model,
    is_default: form.is_default,
    notes: form.notes,
  }
  if (editing.value && !form.api_key) {
    // 未填写新密钥：用特殊标记让后端保留原值
    payload.api_key = '__KEEP__'
  }
  saving.value = true
  try {
    if (editing.value) {
      await llmApi.updateProvider(editing.value, payload)
    } else {
      await llmApi.createProvider(payload)
    }
    ElMessage.success('已保存')
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function test(row: LlmProvider) {
  const res = await llmApi.testProvider(row.id)
  const data = res.data.data || {}
  if (data.ok) {
    ElMessage.success(`连接成功，可用模型 ${data.model_count} 个`)
  } else {
    ElMessage.error(`连接失败：${data.error || '未知错误'}`)
  }
}

async function setDefault(row: LlmProvider) {
  await llmApi.setDefaultProvider(row.id)
  ElMessage.success('已设为默认')
  await load()
}

async function remove(row: LlmProvider) {
  await ElMessageBox.confirm(`确认删除接入「${row.name}」？`, '删除确认', { type: 'warning' })
  await llmApi.deleteProvider(row.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.page { padding: 4px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.panel-title { font-size: 18px; font-weight: 700; margin: 0; }
.panel-sub { margin: 4px 0 0; font-size: 13px; color: var(--c-text-3); }
.tbl { --el-table-bg-color: transparent; }
.muted { color: var(--c-text-3); }
.hint { font-size: 12px; color: var(--c-text-3); margin-top: 4px; line-height: 1.5; }
.tech-card { border: 1px solid var(--c-border); border-radius: var(--radius-lg); background: var(--c-surface); }
</style>
