<template>
  <div class="dg-root">
    <div class="dg-toolbar">
      <div class="dg-brand">
        <el-icon><Document /></el-icon>
        <div>
          <div class="dg-brand__t">AI 文档提炼</div>
          <div class="dg-brand__s">粘贴文档 / 网页文本 → 摘要 · 翻译 · 要点 · 脑图大纲</div>
        </div>
      </div>
      <div class="dg-model">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
      </div>
    </div>

    <div class="dg-body">
      <section class="dg-left">
        <el-card shadow="never" class="dg-card">
          <template #header><span class="dg-card__t">① 输入文档 / 网页文本</span></template>
          <el-input
            v-model="text"
            type="textarea"
            :rows="16"
            resize="none"
            placeholder="将文档正文或网页内容粘贴到这里（可粘贴长文）..."
          />
          <div class="dg-count">{{ text.length }} 字</div>
        </el-card>
      </section>

      <section class="dg-mid">
        <el-card shadow="never" class="dg-card">
          <template #header><span class="dg-card__t">② 提炼方式</span></template>
          <el-radio-group v-model="task" class="dg-tasks">
            <el-radio-button label="summary">摘要</el-radio-button>
            <el-radio-button label="translate">翻译</el-radio-button>
            <el-radio-button label="extract">要点抽取</el-radio-button>
            <el-radio-button label="outline">脑图大纲</el-radio-button>
          </el-radio-group>

          <div v-if="task === 'translate'" class="dg-field">
            <span class="dg-field__l">目标语言</span>
            <el-select v-model="targetLang" size="small" style="width: 100%">
              <el-option label="中文" value="中文" />
              <el-option label="英文" value="英文" />
              <el-option label="日文" value="日文" />
              <el-option label="韩文" value="韩文" />
              <el-option label="法文" value="法文" />
              <el-option label="德文" value="德文" />
            </el-select>
          </div>

          <div v-if="task === 'summary'" class="dg-field">
            <span class="dg-field__l">篇幅</span>
            <el-select v-model="length" size="small" style="width: 100%">
              <el-option label="简短（1-2 句）" value="简短" />
              <el-option label="标准（要点式）" value="标准" />
              <el-option label="详细（分段）" value="详细" />
            </el-select>
          </div>

          <el-button
            type="primary"
            class="dg-run"
            :loading="running"
            :disabled="!ready || !text.trim()"
            :icon="MagicStick"
            @click="run"
          >开始提炼</el-button>
          <el-button v-if="running" text @click="stop">停止</el-button>
        </el-card>
      </section>

      <section class="dg-right">
        <el-card shadow="never" class="dg-card">
          <template #header>
            <span class="dg-card__t">③ 结果</span>
            <div class="dg-result__tools">
              <el-button size="small" text :icon="CopyDocument" :disabled="!result" @click="copy">复制</el-button>
              <el-button size="small" text :icon="Download" :disabled="!result" @click="downloadMd">下载 MD</el-button>
            </div>
          </template>
          <div v-if="!result && !running" class="dg-empty">
            <el-icon class="dg-empty__ico"><Document /></el-icon>
            <p>选择提炼方式后点击「开始提炼」，结果将在此流式呈现。</p>
          </div>
          <div v-else class="dg-out">{{ result || '生成中…' }}</div>
        </el-card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CopyDocument, Download, MagicStick } from '@element-plus/icons-vue'
import { getAccessToken } from '@/utils/auth'
import * as llmApi from '@/api/llm'
import { streamRefine, type DigestTask } from '@/api/digest'

const text = ref('')
const task = ref<DigestTask>('summary')
const targetLang = ref('中文')
const length = ref('标准')
const result = ref('')
const running = ref(false)
const abort = ref<AbortController | null>(null)

const models = ref<string[]>([])
const model = ref('')
const defaultModel = ref('')
const modelLoading = ref(false)
const ready = computed(() => !!(models.value.length || defaultModel.value))

const TASK_NAME: Record<DigestTask, string> = {
  summary: '摘要',
  translate: '翻译',
  extract: '要点',
  outline: '脑图大纲',
}

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
    await streamRefine(
      {
        text: content,
        task: task.value,
        target_lang: task.value === 'translate' ? targetLang.value : '',
        length: length.value,
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
      ElMessage.error(e?.message || '提炼失败')
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
  const blob = new Blob([result.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `AI文档${TASK_NAME[task.value]}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(loadModels)
</script>

<style scoped>
.dg-root { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.dg-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 6px 14px; border-bottom: 1px solid var(--c-border);
}
.dg-brand { display: flex; align-items: center; gap: 10px; }
.dg-brand .el-icon { font-size: 22px; color: var(--brand-emerald); }
.dg-brand__t { font-size: 16px; font-weight: 600; }
.dg-brand__s { font-size: 12px; color: var(--c-text-3); }
.dg-model { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 220px; }

.dg-body {
  flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 280px 1fr;
  gap: 14px; padding-top: 14px; overflow: hidden;
}
.dg-card { height: 100%; display: flex; flex-direction: column; }
.dg-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.dg-card__t { font-weight: 600; }
.dg-count { text-align: right; font-size: 12px; color: var(--c-text-3); margin-top: 6px; }

.dg-tasks { display: flex; flex-wrap: wrap; gap: 8px; }
.dg-field { margin-top: 14px; }
.dg-field__l { display: block; font-size: 13px; color: var(--c-text-2); margin-bottom: 6px; }
.dg-run { width: 100%; margin-top: 18px; }

.dg-result__tools { float: right; }
.dg-empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 360px; }
.dg-empty__ico { font-size: 36px; opacity: 0.6; margin-bottom: 8px; }
.dg-empty p { font-size: 13px; line-height: 1.7; }
.dg-out {
  flex: 1; min-height: 0; overflow: auto; white-space: pre-wrap;
  word-break: break-word; line-height: 1.75; font-size: 14px; color: var(--c-text-1);
}
</style>
