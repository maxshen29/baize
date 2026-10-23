<template>
  <div class="pw-root">
    <div class="pw-toolbar">
      <div class="pw-brand">
        <el-icon><EditPen /></el-icon>
        <div>
          <div class="pw-brand__t">综合论文编写</div>
          <div class="pw-brand__s">上传论文 → 改写 · 润色 · 互译 · 提炼 · 重组 · 参考文献整理</div>
        </div>
      </div>
      <div class="pw-upload"><PaperUploader code="paper_writer" @parsed="onParsed" /></div>
      <div class="pw-model">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
      </div>
    </div>

    <div class="pw-body">
      <section class="pw-left">
        <el-card shadow="never" class="pw-card">
          <template #header><span class="pw-card__t">① 原文（可编辑）</span></template>
          <el-input v-model="text" type="textarea" :rows="24" resize="none" placeholder="上传文件，或在此粘贴论文内容…" />
          <div class="pw-count">{{ text.length }} 字</div>
        </el-card>
      </section>

      <section class="pw-mid">
        <el-card shadow="never" class="pw-card">
          <template #header><span class="pw-card__t">② 编辑操作</span></template>
          <el-radio-group v-model="action" class="pw-tasks">
            <el-radio-button label="rewrite">大篇幅改写</el-radio-button>
            <el-radio-button label="polish">学术润色</el-radio-button>
            <el-radio-button label="translate">中英互译</el-radio-button>
            <el-radio-button label="extract">内容提炼</el-radio-button>
            <el-radio-button label="restructure">结构重组</el-radio-button>
            <el-radio-button label="refs">参考文献整理</el-radio-button>
          </el-radio-group>
          <div v-if="action === 'translate'" class="pw-field">
            <span class="pw-field__l">目标语言</span>
            <el-select v-model="targetLang" size="small" style="width: 100%">
              <el-option label="中文" value="中文" />
              <el-option label="英文" value="英文" />
            </el-select>
          </div>
          <div class="pw-tip">{{ actionTip }}</div>
          <el-button type="primary" class="pw-run" :loading="running" :disabled="!ready || !text.trim()" :icon="MagicStick" @click="run">开始处理</el-button>
          <el-button v-if="running" text @click="stop">停止</el-button>
        </el-card>
      </section>

      <section class="pw-right">
        <el-card shadow="never" class="pw-card">
          <template #header>
            <span class="pw-card__t">③ 处理结果</span>
            <div class="pw-tools">
              <el-button size="small" text :icon="CopyDocument" :disabled="!result" @click="copy">复制</el-button>
              <el-button size="small" text :icon="Download" :disabled="!result" @click="downloadMd">下载 MD</el-button>
            </div>
          </template>
          <div v-if="!result && !running" class="pw-empty">
            <el-icon class="pw-empty__ico"><EditPen /></el-icon>
            <p>选择编辑操作后点击「开始处理」，结果将在此流式呈现。</p>
          </div>
          <div v-else class="pw-out">{{ result || '生成中…' }}</div>
        </el-card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { EditPen, CopyDocument, Download, MagicStick } from '@element-plus/icons-vue'
import * as llmApi from '@/api/llm'
import { runPaper } from '@/api/paper'
import PaperUploader from '@/components/paper/PaperUploader.vue'

const text = ref('')
const action = ref('rewrite')
const targetLang = ref('中文')
const result = ref('')
const running = ref(false)
const abort = ref<AbortController | null>(null)

const models = ref<string[]>([])
const model = ref('')
const defaultModel = ref('')
const modelLoading = ref(false)
const ready = computed(() => !!(models.value.length || defaultModel.value))

const ACTION_TIPS: Record<string, string> = {
  rewrite: '在保持原意、数据与结论不变的前提下重写表达，提升学术性与连贯度。',
  polish: '修正语法与用词，提升学术语体，不改变原意。',
  translate: '中英互译：术语统一、句式符合学术规范，保留引用编号。',
  extract: '提取核心论点、方法、结论与创新点，条理呈现。',
  restructure: '按标准论文结构重组内容并补充小标题（适合全文）。',
  refs: '将参考文献统一规范为 GB/T 7714 格式并排序。',
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
      'paper_writer',
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
  a.download = `论文编写_${action.value}.md`
  a.click()
  URL.revokeObjectURL(url)
}
onMounted(loadModels)
</script>

<style scoped>
.pw-root { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.pw-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 6px 14px; border-bottom: 1px solid var(--c-border); flex-wrap: wrap; }
.pw-brand { display: flex; align-items: center; gap: 10px; }
.pw-brand .el-icon { font-size: 22px; color: var(--brand-emerald); }
.pw-brand__t { font-size: 16px; font-weight: 600; }
.pw-brand__s { font-size: 12px; color: var(--c-text-3); }
.pw-model { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 220px; }
.pw-body { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 300px 1fr; gap: 14px; padding-top: 14px; overflow: hidden; }
.pw-card { height: 100%; display: flex; flex-direction: column; }
.pw-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.pw-card__t { font-weight: 600; }
.pw-count { text-align: right; font-size: 12px; color: var(--c-text-3); margin-top: 6px; }
.pw-tasks { display: flex; flex-wrap: wrap; gap: 8px; }
.pw-field { margin-top: 14px; }
.pw-field__l { display: block; font-size: 13px; color: var(--c-text-2); margin-bottom: 6px; }
.pw-tip { margin-top: 14px; font-size: 12px; color: var(--c-text-3); line-height: 1.7; }
.pw-run { width: 100%; margin-top: 18px; }
.pw-tools { float: right; }
.pw-empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 360px; }
.pw-empty__ico { font-size: 36px; opacity: 0.6; margin-bottom: 8px; }
.pw-empty p { font-size: 13px; line-height: 1.7; }
.pw-out { flex: 1; min-height: 0; overflow: auto; white-space: pre-wrap; word-break: break-word; line-height: 1.75; font-size: 14px; color: var(--c-text-1); }
</style>
