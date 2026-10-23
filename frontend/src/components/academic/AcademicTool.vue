<template>
  <div class="at-root">
    <div class="at-toolbar">
      <div class="at-brand">
        <el-icon><Reading /></el-icon>
        <div>
          <div class="at-brand__t">{{ label }}</div>
          <div class="at-brand__s">{{ desc }}</div>
        </div>
      </div>
      <div class="at-model">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
      </div>
    </div>

    <div class="at-body">
      <section class="at-mid">
        <el-card shadow="never" class="at-card">
          <template #header><span class="at-card__t">输入内容</span></template>
          <el-input
            v-model="text"
            type="textarea"
            :rows="20"
            resize="none"
            :placeholder="placeholder"
          />
          <div v-if="needsLang" class="at-lang">
            <span class="lbl">目标语言</span>
            <el-select v-model="targetLang" size="small" style="width: 100%">
              <el-option label="中文" value="中文" />
              <el-option label="英文" value="英文" />
            </el-select>
          </div>
          <div class="at-mid__foot">
            <span class="at-count">{{ text.length }} 字</span>
            <div>
              <el-button
                type="primary"
                :loading="running"
                :disabled="!ready || !text.trim()"
                :icon="MagicStick"
                @click="run"
              >开始处理</el-button>
              <el-button v-if="running" text @click="stop">停止</el-button>
            </div>
          </div>
        </el-card>
      </section>

      <section class="at-right">
        <el-card shadow="never" class="at-card">
          <template #header>
            <span class="at-card__t">结果</span>
            <div class="at-result__tools">
              <el-button size="small" text :icon="CopyDocument" :disabled="!result" @click="copy">复制</el-button>
              <el-button size="small" text :icon="Download" :disabled="!result" @click="downloadMd">下载 MD</el-button>
            </div>
          </template>
          <div v-if="!result && !running" class="at-empty">
            <el-icon class="at-empty__ico"><Reading /></el-icon>
            <p>粘贴内容后点击「开始处理」，结果将在此流式呈现。</p>
          </div>
          <div v-else class="at-out">{{ result || '生成中…' }}</div>
        </el-card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Reading, CopyDocument, Download, MagicStick } from '@element-plus/icons-vue'
import { getAccessToken } from '@/utils/auth'
import * as llmApi from '@/api/llm'
import { streamRun } from '@/api/academic'

const props = defineProps<{
  code: string
  tool: string
  label: string
  desc?: string
  needsLang?: boolean
  placeholder?: string
}>()

const text = ref('')
const targetLang = ref('中文')
const result = ref('')
const running = ref(false)
const abort = ref<AbortController | null>(null)

const models = ref<string[]>([])
const model = ref('')
const defaultModel = ref('')
const modelLoading = ref(false)
const ready = computed(() => !!(models.value.length || defaultModel.value))

async function loadModels() {
  modelLoading.value = true
  try {
    const res = await llmApi.getDefaultProvider()
    const data = res.data?.data
    if (data) {
      defaultModel.value = data.model
      models.value = data.models || []
      if (!model.value) model.value = data.model
    }
    if (!models.value.length) {
      const r2 = await llmApi.listModels()
      models.value = r2.data?.data || []
      if (!model.value && models.value.length) model.value = models.value[0]
    }
  } catch {
    /* ignore */
  } finally {
    modelLoading.value = false
  }
}

async function run() {
  const content = text.value.trim()
  if (!content || running.value) return
  if (!model.value) {
    ElMessage.warning('请先选择模型')
    return
  }
  result.value = ''
  running.value = true
  const ctrl = new AbortController()
  abort.value = ctrl
  try {
    await streamRun(
      props.code,
      {
        text: content,
        tool: props.tool,
        target_lang: props.needsLang ? targetLang.value : '',
        model: model.value,
      },
      {
        onDelta: (d) => {
          result.value += d
        },
        signal: ctrl.signal,
      },
    )
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      ElMessage.error(e?.message || '处理失败')
    }
  } finally {
    running.value = false
    abort.value = null
  }
}

function stop() {
  abort.value?.abort()
}

async function copy() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}

function downloadMd() {
  if (!result.value) return
  const blob = new Blob([`# ${props.label}\n\n${result.value}`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `学术-${props.label}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadModels)
</script>

<style scoped>
.at-root { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.at-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 6px 14px; border-bottom: 1px solid var(--c-border);
}
.at-brand { display: flex; align-items: center; gap: 10px; }
.at-brand .el-icon { font-size: 22px; color: var(--brand-emerald); }
.at-brand__t { font-size: 16px; font-weight: 600; }
.at-brand__s { font-size: 12px; color: var(--c-text-3); }
.at-model { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 220px; }

.at-body {
  flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr;
  gap: 14px; padding-top: 14px; overflow: hidden;
}
.at-card { height: 100%; display: flex; flex-direction: column; }
.at-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.at-card__t { font-weight: 600; }
.at-lang { margin-top: 12px; }
.at-mid__foot { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
.at-count { font-size: 12px; color: var(--c-text-3); }

.at-result__tools { float: right; }
.at-empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 320px; }
.at-empty__ico { font-size: 36px; opacity: 0.6; margin-bottom: 8px; }
.at-empty p { font-size: 13px; line-height: 1.7; }
.at-out {
  flex: 1; min-height: 0; overflow: auto; white-space: pre-wrap;
  word-break: break-word; line-height: 1.75; font-size: 14px; color: var(--c-text-1);
}
</style>
