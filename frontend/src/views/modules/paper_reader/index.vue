<template>
  <div class="pr-root">
    <div class="pr-toolbar">
      <div class="pr-brand">
        <el-icon><Reading /></el-icon>
        <div>
          <div class="pr-brand__t">综合论文阅读</div>
          <div class="pr-brand__s">上传 PDF/Word 或 URL → 提炼 · 翻译 · 脑图 · 摘要 · 交互问答</div>
        </div>
      </div>
      <div class="pr-upload"><PaperUploader code="paper_reader" :allow-url="true" @parsed="onParsed" /></div>
      <div class="pr-model">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
      </div>
    </div>

    <div class="pr-body">
      <section class="pr-left">
        <el-card shadow="never" class="pr-card">
          <template #header><span class="pr-card__t">① 文献原文</span></template>
          <el-input
            v-model="text"
            type="textarea"
            :rows="24"
            resize="none"
            readonly
            placeholder="上传文件或粘贴 URL 后，正文将显示在此（只读预览）；也可直接粘贴文本。"
          />
          <div class="pr-count">{{ text.length }} 字</div>
        </el-card>
      </section>

      <section class="pr-mid">
        <el-card shadow="never" class="pr-card">
          <template #header><span class="pr-card__t">② 阅读辅助</span></template>
          <el-radio-group v-model="action" class="pr-tasks">
            <el-radio-button label="summary">摘要生成</el-radio-button>
            <el-radio-button label="mindmap">核心脑图</el-radio-button>
            <el-radio-button label="translate">段落/全文翻译</el-radio-button>
            <el-radio-button label="extract">智能提炼</el-radio-button>
          </el-radio-group>
          <div v-if="action === 'translate'" class="pr-field">
            <span class="pr-field__l">目标语言</span>
            <el-select v-model="targetLang" size="small" style="width: 100%">
              <el-option label="中文" value="中文" />
              <el-option label="英文" value="英文" />
            </el-select>
          </div>
          <div class="pr-tip">{{ actionTip }}</div>
          <el-button type="primary" class="pr-run" :loading="running" :disabled="!ready || !text.trim()" :icon="MagicStick" @click="run">开始处理</el-button>
          <el-button v-if="running" text @click="stop">停止</el-button>
        </el-card>
      </section>

      <section class="pr-right">
        <el-card shadow="never" class="pr-card">
          <template #header><span class="pr-card__t">③ 输出 / 问答</span></template>
          <el-tabs v-model="tab" class="pr-tabs">
            <el-tab-pane label="处理结果" name="result">
              <div class="pr-tools">
                <el-button size="small" text :icon="CopyDocument" :disabled="!result" @click="copy">复制</el-button>
                <el-button size="small" text :icon="Download" :disabled="!result" @click="downloadMd">下载 MD</el-button>
              </div>
              <div v-if="!result && !running" class="pr-empty">
                <el-icon class="pr-empty__ico"><Reading /></el-icon>
                <p>选择阅读辅助功能后点击「开始处理」，结果将在此呈现。</p>
              </div>
              <div v-else class="pr-out">{{ result || '生成中…' }}</div>
            </el-tab-pane>

            <el-tab-pane label="交互问答" name="qa">
              <div class="pr-qa">
                <div class="pr-qa__list">
                  <div v-for="(m, i) in qaHistory" :key="i" class="pr-bubble" :class="m.role">
                    <div class="pr-bubble__role">{{ m.role === 'user' ? '你' : '助手' }}</div>
                    <div class="pr-bubble__c">{{ m.content }}</div>
                  </div>
                  <div v-if="qaRunning" class="pr-bubble assistant">
                    <div class="pr-bubble__role">助手</div>
                    <div class="pr-bubble__c">{{ qaAnswer || '思考中…' }}</div>
                  </div>
                </div>
                <div class="pr-qa__input">
                  <el-input
                    v-model="question"
                    type="textarea"
                    :rows="2"
                    resize="none"
                    placeholder="基于已上传文献提问，例如：本文的研究方法是什么？（Ctrl+Enter 发送）"
                    @keyup.ctrl.enter="ask"
                  />
                  <el-button type="primary" :loading="qaRunning" :disabled="!text.trim() || !question.trim()" @click="ask">发送</el-button>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Reading, CopyDocument, Download, MagicStick } from '@element-plus/icons-vue'
import * as llmApi from '@/api/llm'
import { runPaper, askPaper } from '@/api/paper'
import PaperUploader from '@/components/paper/PaperUploader.vue'

const text = ref('')
const action = ref('summary')
const targetLang = ref('中文')
const tab = ref('result')
const result = ref('')
const running = ref(false)
const abort = ref<AbortController | null>(null)

const question = ref('')
const qaHistory = ref<{ role: string; content: string }[]>([])
const qaAnswer = ref('')
const qaRunning = ref(false)
const qaAbort = ref<AbortController | null>(null)

const models = ref<string[]>([])
const model = ref('')
const defaultModel = ref('')
const modelLoading = ref(false)
const ready = computed(() => !!(models.value.length || defaultModel.value))

const ACTION_TIPS: Record<string, string> = {
  summary: '生成结构化摘要：问题、方法、结果、结论与意义。',
  mindmap: '提炼核心主题与分支要点，输出层级化脑图大纲（Markdown 列表）。',
  translate: '段落/全文翻译：术语统一、保留引用编号。',
  extract: '提取核心观点、关键论据与重要结论，便于快速把握全文。',
}
const actionTip = computed(() => ACTION_TIPS[action.value] || '')

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

function onParsed(data: any) {
  text.value = data.text
  tab.value = 'result'
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
    await runPaper(
      'paper_reader',
      {
        action: action.value,
        text: content,
        target_lang: action.value === 'translate' ? targetLang.value : '',
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
    if (e?.name !== 'AbortError') ElMessage.error(e?.message || '处理失败')
  } finally {
    running.value = false
    abort.value = null
  }
}
function stop() {
  abort.value?.abort()
}

async function ask() {
  const q = question.value.trim()
  if (!q || !text.value.trim() || qaRunning.value) return
  if (!model.value) {
    ElMessage.warning('请先选择模型')
    return
  }
  const history = [...qaHistory.value]
  qaHistory.value.push({ role: 'user', content: q })
  qaAnswer.value = ''
  qaRunning.value = true
  tab.value = 'qa'
  const ctrl = new AbortController()
  qaAbort.value = ctrl
  try {
    await askPaper(
      'paper_reader',
      { text: text.value, question: q, history, model: model.value },
      {
        onDelta: (d) => {
          qaAnswer.value += d
        },
        signal: ctrl.signal,
      },
    )
    qaHistory.value.push({ role: 'assistant', content: qaAnswer.value })
    question.value = ''
  } catch (e: any) {
    if (e?.name !== 'AbortError') ElMessage.error(e?.message || '问答失败')
  } finally {
    qaRunning.value = false
    qaAbort.value = null
  }
}

async function copy() {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value)
    ElMessage.success('已复制')
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
  a.download = `论文阅读_${action.value}.md`
  a.click()
  URL.revokeObjectURL(url)
}
onMounted(loadModels)
</script>

<style scoped>
.pr-root { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.pr-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 6px 14px; border-bottom: 1px solid var(--c-border); flex-wrap: wrap; }
.pr-brand { display: flex; align-items: center; gap: 10px; }
.pr-brand .el-icon { font-size: 22px; color: var(--brand-emerald); }
.pr-brand__t { font-size: 16px; font-weight: 600; }
.pr-brand__s { font-size: 12px; color: var(--c-text-3); }
.pr-model { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 220px; }
.pr-body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 300px 1fr; gap: 14px; padding-top: 14px; overflow: hidden; }
.pr-card { height: 100%; display: flex; flex-direction: column; }
.pr-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.pr-card__t { font-weight: 600; }
.pr-count { text-align: right; font-size: 12px; color: var(--c-text-3); margin-top: 6px; }
.pr-tasks { display: flex; flex-wrap: wrap; gap: 8px; }
.pr-field { margin-top: 14px; }
.pr-field__l { display: block; font-size: 13px; color: var(--c-text-2); margin-bottom: 6px; }
.pr-tip { margin-top: 14px; font-size: 12px; color: var(--c-text-3); line-height: 1.7; }
.pr-run { width: 100%; margin-top: 18px; }
.pr-tabs { height: 100%; display: flex; flex-direction: column; }
.pr-tabs :deep(.el-tabs__content) { flex: 1; min-height: 0; }
.pr-tabs :deep(.el-tab-pane) { height: 100%; }
.pr-tools { float: right; }
.pr-empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 360px; }
.pr-empty__ico { font-size: 36px; opacity: 0.6; margin-bottom: 8px; }
.pr-empty p { font-size: 13px; line-height: 1.7; }
.pr-out { height: 100%; overflow: auto; white-space: pre-wrap; word-break: break-word; line-height: 1.75; font-size: 14px; color: var(--c-text-1); }

.pr-qa { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.pr-qa__list { flex: 1; min-height: 0; overflow: auto; padding: 4px 2px; }
.pr-bubble { margin-bottom: 12px; max-width: 88%; }
.pr-bubble.user { margin-left: auto; }
.pr-bubble__role { font-size: 11px; color: var(--c-text-3); margin-bottom: 3px; }
.pr-bubble__c { padding: 8px 12px; border-radius: 8px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; font-size: 13px; background: var(--el-fill-color-light); }
.pr-bubble.user .pr-bubble__c { background: var(--el-color-primary-light-9); }
.pr-qa__input { display: flex; gap: 8px; margin-top: 8px; }
.pr-qa__input .el-textarea { flex: 1; }
</style>
