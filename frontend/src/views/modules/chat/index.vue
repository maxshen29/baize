<template>
  <div class="chat">
    <div class="chat-head">
      <div class="title gradient-text">AI 对话</div>
      <div class="model-pick">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
      </div>
    </div>

    <div class="messages" ref="scrollEl">
      <div v-if="!messages.length" class="empty">
        <el-icon class="empty-ico"><ChatDotRound /></el-icon>
        <p>基于已接入的大模型开始对话。先在「系统管理 → 大模型接入」中配置可用的模型服务。</p>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="row" :class="m.role">
        <div class="bubble" :class="m.role">
          <span v-if="m.role === 'assistant' && m.streaming && !m.content" class="typing">
            <i></i><i></i><i></i>
          </span>
          <span class="content" v-else>{{ m.content || '…' }}</span>
        </div>
      </div>
    </div>

    <div class="composer">
      <el-input
        v-model="input"
        type="textarea"
        :rows="3"
        resize="none"
        :placeholder="ready ? '输入消息，Enter 发送 / Shift+Enter 换行' : '未配置可用大模型，请先在系统管理中接入'"
        :disabled="!ready || sending"
        @keydown.enter.exact.prevent="send"
      />
      <div class="actions">
        <el-button v-if="messages.length" text :icon="Delete" @click="clear">清空</el-button>
        <el-button type="primary" :icon="Promotion" :loading="sending" :disabled="!ready" @click="send">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, nextTick, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Delete, Promotion } from '@element-plus/icons-vue'
import { getAccessToken } from '@/utils/auth'
import * as llmApi from '@/api/llm'

interface Msg {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

const messages = ref<Msg[]>([])
const input = ref('')
const sending = ref(false)
const models = ref<string[]>([])
const model = ref<string>('')
const defaultModel = ref<string>('')
const modelLoading = ref(false)
const scrollEl = ref<HTMLElement | null>(null)
const ready = computed(() => models.value.length > 0 || !!defaultModel.value)

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

function scrollToBottom() {
  nextTick(() => {
    const el = scrollEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  if (!model.value) {
    ElMessage.warning('请先选择模型')
    return
  }
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  const assistant: Msg = { role: 'assistant', content: '', streaming: true }
  messages.value.push(assistant)
  scrollToBottom()
  sending.value = true

  const history = messages.value
    .filter((m) => !m.streaming)
    .map((m) => ({ role: m.role, content: m.content }))

  try {
    const token = getAccessToken()
    const resp = await fetch('/api/v1/llm/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ messages: history, model: model.value }),
    })
    if (!resp.ok || !resp.body) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err?.message || `请求失败 (${resp.status})`)
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (data === '[DONE]') continue
        try {
          const json = JSON.parse(data)
          if (json.error) throw new Error(json.error)
          const delta =
            json.choices?.[0]?.delta?.content ||
            json.choices?.[0]?.message?.content ||
            ''
          if (delta) {
            assistant.content += delta
            scrollToBottom()
          }
        } catch (e) {
          if (e instanceof Error) throw e
        }
      }
    }
  } catch (e: any) {
    assistant.content = `⚠️ ${e?.message || '对话出错'}`
  } finally {
    assistant.streaming = false
    sending.value = false
    scrollToBottom()
  }
}

function clear() {
  messages.value = []
}

onMounted(loadModels)
</script>

<style scoped>
.chat { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.chat-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 6px 14px; border-bottom: 1px solid var(--c-border);
}
.title { font-size: 18px; font-weight: 700; }
.model-pick { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 240px; }

.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 18px 6px; display: flex; flex-direction: column; gap: 14px; }
.empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 420px; }
.empty-ico { font-size: 40px; color: var(--brand-emerald); opacity: 0.7; margin-bottom: 8px; }
.empty p { font-size: 13px; line-height: 1.7; }

.row { display: flex; }
.row.user { justify-content: flex-end; }
.row.assistant { justify-content: flex-start; }
.bubble {
  max-width: 76%; padding: 11px 14px; border-radius: 14px; line-height: 1.7;
  font-size: 14px; white-space: pre-wrap; word-break: break-word;
}
.bubble.user { background: var(--brand-grad); color: #fff; border-bottom-right-radius: 4px; }
.bubble.assistant { background: var(--c-surface); border: 1px solid var(--c-border); color: var(--c-text-1); border-bottom-left-radius: 4px; }

.typing { display: inline-flex; gap: 4px; align-items: center; }
.typing i { width: 6px; height: 6px; border-radius: 50%; background: var(--c-text-3); animation: blink 1.2s infinite; }
.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 1; } }

.composer { border-top: 1px solid var(--c-border); padding-top: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }
</style>
