<template>
  <div class="ss-root">
    <!-- 顶部：品牌 + 模型 + 历史 -->
    <div class="ss-toolbar">
      <div class="ss-brand">
        <el-icon class="ss-brand__ico"><Connection /></el-icon>
        <div>
          <div class="ss-brand__t">社会推演 · 数字沙盘</div>
          <div class="ss-brand__s">上传种子材料 → 构建平行世界 → 数字世界预览 → 多智能体推演 → 预测报告 → 与数字世界对话</div>
        </div>
      </div>
      <div class="ss-toolbar__right">
        <span class="lbl">模型</span>
        <el-select v-model="model" size="default" class="sel" :loading="modelLoading" placeholder="默认模型">
          <el-option v-for="m in models" :key="m" :label="m" :value="m" />
          <el-option v-if="defaultModel && !models.includes(defaultModel)" :label="defaultModel" :value="defaultModel" />
        </el-select>
        <el-button :icon="Clock" @click="openHistory">历史推演</el-button>
      </div>
    </div>

    <!-- 步骤条 -->
    <el-steps :active="step" align-center class="ss-steps" finish-status="success">
      <el-step title="① 构建世界" />
      <el-step title="② 数字世界预览" />
      <el-step title="③ 推演沙盘" />
      <el-step title="④ 预测报告" />
      <el-step title="⑤ 深度互动" />
    </el-steps>

    <div class="ss-body">
      <!-- ============ 步骤 1：构建世界 ============ -->
      <section v-show="step === 1" class="ss-panel">
        <div class="ss-cols">
          <el-card shadow="never" class="ss-card">
            <template #header><span class="ss-card__t">① 种子材料与预测需求</span></template>
            <div class="ss-field">
              <label>种子材料（新闻 / 政策草案 / 小说设定 / 数据分析…）</label>
              <el-input v-model="seedText" type="textarea" :rows="10" resize="none"
                placeholder="粘贴或描述你想推演的真实世界素材，例如一篇舆情事件报道、一份政策草案、一段故事背景……" />
              <div class="ss-count">{{ seedText.length }} 字</div>
            </div>
            <div class="ss-field">
              <label>预测需求（你想推演 / 预测的问题）</label>
              <el-input v-model="question" type="textarea" :rows="3" resize="none"
                placeholder="例如：该事件在 72 小时内会如何演变？舆论会反转吗？结局最可能如何？" />
            </div>
            <div class="ss-params">
              <div class="ss-param">
                <label>虚拟居民数量：{{ numAgents }}</label>
                <el-slider v-model="numAgents" :min="3" :max="16" :step="1" />
              </div>
              <div class="ss-param">
                <label>推演轮次：{{ rounds }}</label>
                <el-slider v-model="rounds" :min="3" :max="12" :step="1" />
              </div>
            </div>
            <el-button type="primary" :loading="building" :disabled="!ready" :icon="MagicStick" class="ss-run" @click="buildWorld">
              {{ building ? '正在构建数字世界…' : '构建世界' }}
            </el-button>
          </el-card>

          <el-card shadow="never" class="ss-card">
            <template #header><span class="ss-card__t">数字世界概览</span></template>
            <div v-if="!world && !building" class="ss-empty">
              <el-icon class="ss-empty__ico"><Connection /></el-icon>
              <p>填写左侧材料后点击「构建世界」，这里会展示自动生成的世界观与虚拟居民画像。</p>
            </div>
            <div v-else class="ss-world">
              <div v-if="world" class="ss-world__block">
                <div class="ss-world__h">🌐 世界观</div>
                <div class="ss-world__txt">{{ world }}</div>
              </div>
              <div v-if="setting" class="ss-world__block">
                <div class="ss-world__h">🗺️ 时空与群体设定</div>
                <div class="ss-world__txt">{{ setting }}</div>
              </div>
              <div v-if="personas.length" class="ss-world__block">
                <div class="ss-world__h">👥 虚拟居民（{{ personas.length }}）</div>
                <div class="ss-personas">
                  <div v-for="p in personas" :key="p.id" class="ss-persona">
                    <div class="ss-persona__top">
                      <span class="ss-persona__name">{{ p.name }}</span>
                      <el-tag size="small" :type="stanceTag(p.stance)">{{ stanceCN(p.stance) }}</el-tag>
                    </div>
                    <div class="ss-persona__role">{{ p.role }} · <span class="ss-persona__voice">{{ p.voice }}</span></div>
                    <div class="ss-persona__desc">{{ p.traits }} {{ p.background }}</div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
        <div class="ss-next">
          <el-button type="primary" :loading="extractingGraph" :disabled="!personas.length" @click="goToGraphPreview">
            {{ extractingGraph ? '正在抽取知识图谱…' : '进入数字世界预览 →' }}
          </el-button>
        </div>
      </section>

      <!-- ============ 步骤 2：数字世界预览（GraphRAG） ============ -->
      <section v-show="step === 2" class="ss-panel">
        <div class="ss-cols ss-cols--graph">
          <el-card shadow="never" class="ss-card ss-card--graph">
            <template #header>
              <span class="ss-card__t">② 数字世界预览 · GraphRAG 关系图谱</span>
              <el-button size="small" text :loading="graphLoading" :icon="Refresh" @click="runExtractGraph">重新抽取</el-button>
            </template>
            <GraphPreview v-if="graph.nodes.length" :graph="graph" class="ss-graph" @node-click="onNodeClick" />
            <div v-else class="ss-empty">
              <el-icon class="ss-empty__ico"><Share /></el-icon>
              <p>知识图谱正在构建中，请稍候…</p>
            </div>
          </el-card>

          <el-card shadow="never" class="ss-card">
            <template #header><span class="ss-card__t">世界设定与关键实体</span></template>
            <div class="ss-world__block">
              <div class="ss-world__h">🌐 世界观</div>
              <div class="ss-world__txt">{{ world || '（尚未构建世界）' }}</div>
            </div>
            <div class="ss-world__block">
              <div class="ss-world__h">🗺️ 时空与群体设定</div>
              <div class="ss-world__txt">{{ setting || '（尚未构建世界）' }}</div>
            </div>
            <div v-if="graph.nodes.length" class="ss-world__block">
              <div class="ss-world__h">🔗 关键实体</div>
              <div class="ss-entities">
                <el-tag v-for="n in topEntities" :key="n.id" size="small" :style="entityTagStyle(n)" class="ss-entity">
                  {{ n.name }}
                </el-tag>
              </div>
            </div>
            <div v-if="selectedNode" class="ss-world__block">
              <div class="ss-world__h">📍 选中实体</div>
              <div class="ss-entity__detail">
                <strong>{{ selectedNode.name }}</strong>
                <el-tag size="small" :style="entityTagStyle(selectedNode)">{{ selectedNode.type }}</el-tag>
                <p>{{ selectedNode.description || '暂无描述' }}</p>
              </div>
            </div>
          </el-card>
        </div>
        <div class="ss-next">
          <el-button @click="step = 1">← 返回构建世界</el-button>
          <el-button type="primary" :disabled="!graph.nodes.length" @click="step = 3">进入推演沙盘 →</el-button>
        </div>
      </section>

      <!-- ============ 步骤 3：推演沙盘 ============ -->
      <section v-show="step === 3" class="ss-panel">
        <div class="ss-cols ss-cols--sim">
          <el-card shadow="never" class="ss-card ss-card--config">
            <template #header><span class="ss-card__t">上帝视角 · 变量注入</span></template>
            <p class="ss-tip">在指定轮次注入外部冲击（如突发声明、政策出台），观察数字世界的反应。</p>
            <div v-for="(g, i) in godEvents" :key="i" class="ss-god">
              <el-input-number v-model="g.round" :min="1" :max="rounds" size="small" controls-position="right" />
              <span class="ss-god__at">轮</span>
              <el-input v-model="g.text" size="small" class="ss-god__txt" placeholder="注入的变量 / 事件…" />
              <el-button size="small" text type="danger" :icon="Delete" @click="godEvents.splice(i, 1)" />
            </div>
            <div class="ss-god ss-god--add">
              <el-input-number v-model="newGod.round" :min="1" :max="rounds" size="small" controls-position="right" />
              <span class="ss-god__at">轮</span>
              <el-input v-model="newGod.text" size="small" class="ss-god__txt" placeholder="新增注入变量…" @keyup.enter="addGod" />
              <el-button size="small" :icon="Plus" @click="addGod" />
            </div>
          </el-card>

          <el-card shadow="never" class="ss-card ss-card--console">
            <template #header>
              <span class="ss-card__t">推演控制台</span>
              <span v-if="simRunning" class="ss-progress">第 {{ simProgress.current }} / {{ simProgress.total }} 轮</span>
            </template>
            <div ref="feedEl" class="ss-feed">
              <div v-if="!feed.length && !simRunning" class="ss-empty">
                <el-icon class="ss-empty__ico"><VideoPlay /></el-icon>
                <p>点击「开始推演」，虚拟居民将在沙盘中自由互动、演化，过程实时呈现。</p>
              </div>
              <template v-for="(it, idx) in feed" :key="idx">
                <div v-if="it.kind === 'round'" class="ss-round">— 第 {{ it.round }} 轮 —</div>
                <div v-else class="ss-action">
                  <div class="ss-action__head">
                    <span class="ss-action__name">{{ it.name }}</span>
                    <el-tag size="small" effect="plain">{{ it.role }}</el-tag>
                    <el-tag size="small" :type="stanceTag(it.stance)" effect="plain">{{ stanceCN(it.stance) }}</el-tag>
                  </div>
                  <div class="ss-action__content">{{ it.content }}</div>
                </div>
              </template>
              <div v-if="simRunning" class="ss-typing"><span></span><span></span><span></span></div>
            </div>
            <div class="ss-sim-actions">
              <el-button type="primary" :loading="simRunning" :disabled="!personas.length" :icon="VideoPlay" @click="runSim">
                {{ simRunning ? '推演中…' : '开始推演' }}
              </el-button>
              <el-button v-if="simRunning" text @click="stopSim">停止</el-button>
              <el-button :disabled="!transcript.length" @click="step = 4">生成预测报告 →</el-button>
            </div>
          </el-card>
        </div>
      </section>

      <!-- ============ 步骤 4：预测报告 ============ -->
      <section v-show="step === 4" class="ss-panel">
        <div class="ss-cols">
          <el-card shadow="never" class="ss-card">
            <template #header>
              <span class="ss-card__t">④ 预测报告</span>
              <div class="ss-result__tools">
                <el-button size="small" text :icon="CopyDocument" :disabled="!reportText" @click="copyReport">复制</el-button>
                <el-button size="small" text :icon="Download" :disabled="!reportText" @click="downloadReport">下载 HTML</el-button>
                <el-button size="small" text :icon="Collection" :disabled="!transcript.length || saving" :loading="saving" @click="saveCurrent">存档</el-button>
              </div>
            </template>
            <div v-if="!reportText && !reportRunning" class="ss-empty">
              <el-icon class="ss-empty__ico"><Document /></el-icon>
              <p>完成推演后点击「生成预测报告」，系统会基于完整推演记录给出研判。</p>
            </div>
            <div v-else class="ss-report" v-html="reportHtml"></div>
          </el-card>
        </div>
        <div class="ss-next">
          <el-button :disabled="!reportText" @click="step = 3">← 返回沙盘</el-button>
          <el-button type="primary" :loading="reportRunning" :disabled="!transcript.length" :icon="MagicStick" @click="genReport">
            {{ reportRunning ? '生成中…' : '生成预测报告' }}
          </el-button>
          <el-button type="primary" :disabled="!reportText" @click="step = 5">进入深度互动 →</el-button>
        </div>
      </section>

      <!-- ============ 步骤 5：深度互动 ============ -->
      <section v-show="step === 5" class="ss-panel">
        <el-card shadow="never" class="ss-card ss-card--chat">
          <template #header>
            <span class="ss-card__t">⑤ 与数字世界对话</span>
            <el-select v-model="focusAgent" size="small" class="ss-chat__focus" placeholder="聚焦对象：全体">
              <el-option label="全体 / 数字世界" value="" />
              <el-option v-for="p in personas" :key="p.id" :label="p.name" :value="p.name" />
            </el-select>
          </template>
          <div ref="chatEl" class="ss-chat">
            <div v-if="!messages.length" class="ss-empty">
              <el-icon class="ss-empty__ico"><ChatDotRound /></el-icon>
              <p>向这个数字世界提问：结局是否如预测？若某居民改变立场会怎样？反事实推演也可以。</p>
            </div>
            <div v-for="(m, i) in messages" :key="i" class="ss-msg" :class="m.role === 'user' ? 'ss-msg--user' : 'ss-msg--ai'">
              <div class="ss-msg__bubble">{{ m.content }}</div>
            </div>
            <div v-if="chatRunning" class="ss-typing ss-typing--msg"><span></span><span></span><span></span></div>
          </div>
          <div class="ss-chat__input">
            <el-input v-model="chatInput" type="textarea" :rows="2" resize="none" placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
              @keydown.enter.exact.prevent="sendChat" />
            <el-button type="primary" :loading="chatRunning" :icon="Promotion" @click="sendChat">发送</el-button>
          </div>
        </el-card>
      </section>
    </div>

    <!-- 历史抽屉 -->
    <el-drawer v-model="historyVisible" title="历史推演" size="42%">
      <div v-loading="historyLoading" class="ss-history">
        <el-empty v-if="!historyItems.length" description="还没有存档的推演" />
        <div v-for="h in historyItems" :key="h.id" class="ss-hitem">
          <div class="ss-hitem__top">
            <span class="ss-hitem__title">{{ h.title }}</span>
            <span class="ss-hitem__time">{{ fmtTime(h.created_at) }}</span>
          </div>
          <div class="ss-hitem__meta">{{ h.question || '（无预测需求）' }}</div>
          <div class="ss-hitem__tags">
            <el-tag size="small" effect="plain">{{ h.persona_count }} 居民</el-tag>
            <el-tag size="small" effect="plain">{{ h.action_count }} 条推演</el-tag>
            <el-tag v-if="h.model" size="small" effect="plain">{{ h.model }}</el-tag>
          </div>
          <div class="ss-hitem__actions">
            <el-button size="small" :icon="View" @click="viewProject(h.id)">查看</el-button>
            <el-button size="small" type="danger" text :icon="Delete" @click="removeProject(h.id)">删除</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection, MagicStick, VideoPlay, Document, CopyDocument, Download, Collection,
  ChatDotRound, Clock, Delete, Plus, Promotion, View, Refresh, Share,
} from '@element-plus/icons-vue'
import * as llmApi from '@/api/llm'
import GraphPreview from '@/components/social_sim/GraphPreview.vue'
import {
  buildWorld as apiBuildWorld, extractGraph as apiExtractGraph, streamSimulate, streamReport, streamChat,
  listProjects, getProject, deleteProject, saveProject, updateProject,
  type Persona, type SimAction, type GraphData, type GraphNode,
} from '@/api/social_sim'

// ---------- 基础状态 ----------
const step = ref(1)
const seedText = ref('')
const question = ref('')
const numAgents = ref(8)
const rounds = ref(6)
const model = ref('')
const models = ref<string[]>([])
const defaultModel = ref('')
const modelLoading = ref(false)
const ready = computed(() => !!(models.value.length || defaultModel.value))
const topEntities = computed(() => {
  // 按度数排序取前 24 个关键实体
  const degree = new Map<string, number>()
  for (const n of graph.value.nodes) degree.set(n.id, 0)
  for (const e of graph.value.edges) {
    degree.set(e.source, (degree.get(e.source) || 0) + 1)
    degree.set(e.target, (degree.get(e.target) || 0) + 1)
  }
  return [...graph.value.nodes]
    .sort((a, b) => (degree.get(b.id) || 0) - (degree.get(a.id) || 0))
    .slice(0, 24)
})
function entityTagStyle(n: GraphNode) {
  return { '--el-tag-bg-color': n.color + '20', '--el-tag-border-color': n.color + '55', '--el-tag-text-color': n.color }
}

const world = ref('')
const setting = ref('')
const personas = ref<Persona[]>([])
const building = ref(false)

const graph = ref<GraphData>({ nodes: [], edges: [] })
const graphLoading = ref(false)
const extractingGraph = ref(false)
const selectedNode = ref<GraphNode | null>(null)

const godEvents = ref<{ round: number; text: string }[]>([])
const newGod = ref<{ round: number; text: string }>({ round: 1, text: '' })

const simRunning = ref(false)
const simProgress = ref({ current: 0, total: 0 })
const feed = ref<any[]>([])
const transcript = ref<SimAction[]>([])
const simAbort = ref<AbortController | null>(null)

const reportText = ref('')
const reportRunning = ref(false)
const reportAbort = ref<AbortController | null>(null)

const messages = ref<{ role: string; content: string }[]>([])
const chatInput = ref('')
const chatRunning = ref(false)
const chatAbort = ref<AbortController | null>(null)
const focusAgent = ref('')

const saving = ref(false)
const currentId = ref<string | null>(null)   // 已存档记录的 id：null=尚未存档(新建)，有值=更新
const feedEl = ref<HTMLElement | null>(null)
const chatEl = ref<HTMLElement | null>(null)

const historyVisible = ref(false)
const historyLoading = ref(false)
const historyItems = ref<any[]>([])

// ---------- 模型加载 ----------
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
  } catch { /* ignore */ } finally {
    modelLoading.value = false
  }
}

// ---------- 步骤 1：构建世界 ----------
async function buildWorld() {
  if (building.value) return
  building.value = true
  world.value = ''
  setting.value = ''
  personas.value = []
  currentId.value = null   // 新的推演，重置为新建
  try {
    const res = await apiBuildWorld({
      seed_text: seedText.value,
      question: question.value,
      num_agents: numAgents.value,
      model: model.value,
    })
    const d = res.data?.data
    if (d) {
      world.value = d.world || ''
      setting.value = d.setting || ''
      personas.value = d.personas || []
      ElMessage.success(`已生成世界与 ${personas.value.length} 位虚拟居民`)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '构建世界失败')
  } finally {
    building.value = false
  }
}

// ---------- 步骤 1b：GraphRAG 知识图谱 ----------
async function runExtractGraph() {
  if (graphLoading.value) return
  graphLoading.value = true
  try {
    const res = await apiExtractGraph({
      seed_text: seedText.value,
      question: question.value,
      model: model.value,
    })
    const d = res.data?.data
    if (d) {
      graph.value = { nodes: d.nodes || [], edges: d.edges || [] }
      ElMessage.success(`已抽取 ${graph.value.nodes.length} 个实体、${graph.value.edges.length} 条关系`)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '知识图谱抽取失败')
  } finally {
    graphLoading.value = false
  }
}

async function goToGraphPreview() {
  if (extractingGraph.value) return
  extractingGraph.value = true
  await runExtractGraph()
  extractingGraph.value = false
  if (graph.value.nodes.length) step.value = 2
}

function onNodeClick(node: GraphNode) {
  selectedNode.value = node
}

// ---------- 步骤 3：推演 ----------
function addGod() {
  if (!newGod.value.text.trim()) return
  godEvents.value.push({ round: newGod.value.round, text: newGod.value.text.trim() })
  newGod.value = { round: Math.min(rounds.value, newGod.value.round + 1), text: '' }
}

async function runSim() {
  if (simRunning.value || !personas.value.length) return
  feed.value = []
  transcript.value = []
  simRunning.value = true
  simProgress.value = { current: 0, total: rounds.value }
  const ge: Record<number, string> = {}
  godEvents.value.forEach((g) => { if (g.text.trim()) ge[g.round] = g.text.trim() })
  const ctrl = new AbortController()
  simAbort.value = ctrl
  try {
    await streamSimulate(
      {
        world: world.value, setting: setting.value, personas: personas.value,
        question: question.value, rounds: rounds.value, god_events: ge, model: model.value,
      },
      {
        onEvent: (ev: any) => {
          if (ev.type === 'round_start') {
            simProgress.value.current = ev.round
            feed.value.push({ kind: 'round', round: ev.round })
          } else if (ev.type === 'action') {
            feed.value.push({ kind: 'action', name: ev.name, role: ev.role, stance: ev.stance, content: ev.content })
            transcript.value.push({ round: ev.round, name: ev.name, role: ev.role, stance: ev.stance, content: ev.content })
          } else if (ev.type === 'done') {
            transcript.value = ev.transcript || transcript.value
          }
          scrollFeed()
        },
        signal: ctrl.signal,
      },
    )
  } catch (e: any) {
    if (e?.name !== 'AbortError') ElMessage.error(e?.message || '推演失败')
  } finally {
    simRunning.value = false
    simAbort.value = null
    // 推演完成后自动存档（带记录的推演记录）
    if (transcript.value.length) await saveCurrent(true)
  }
}

function stopSim() { simAbort.value?.abort() }

async function scrollFeed() {
  await nextTick()
  if (feedEl.value) feedEl.value.scrollTop = feedEl.value.scrollHeight
}

// ---------- 步骤 3：报告 ----------
async function genReport() {
  if (reportRunning.value || !transcript.value.length) return
  reportText.value = ''
  reportRunning.value = true
  const ctrl = new AbortController()
  reportAbort.value = ctrl
  try {
    await streamReport(
      {
        world: world.value, setting: setting.value, personas: personas.value,
        question: question.value, transcript: transcript.value, rounds: rounds.value, model: model.value,
      },
      { onDelta: (d) => { reportText.value += d }, signal: ctrl.signal },
    )
  } catch (e: any) {
    if (e?.name !== 'AbortError') ElMessage.error(e?.message || '生成报告失败')
  } finally {
    reportRunning.value = false
    reportAbort.value = null
    // 去除可能的代码围栏 / 整页包裹，保证展示干净
    reportText.value = cleanReportHtml(reportText.value)
    // 报告生成后自动存档（更新既有记录，带上报告）
    if (reportText.value) await saveCurrent(true)
  }
}

async function copyReport() {
  if (!reportText.value) return
  try { await navigator.clipboard.writeText(cleanReportHtml(reportText.value)); ElMessage.success('已复制') }
  catch { ElMessage.warning('复制失败，请手动选择') }
}
function downloadReport() {
  if (!reportText.value) return
  const body = cleanReportHtml(reportText.value)
  const inner = /class="r-doc"/i.test(body) ? body : `<div class="r-doc">${body}</div>`
  const title = (body.match(/<h1[^>]*>([^<]+)<\/h1>/i) || [])[1] || '数字沙盘推演报告'
  const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif; background:#f0f2f5; margin:0; padding:32px 16px; color:#1f2329; }
  .r-doc { max-width:880px; margin:0 auto; background:#fff; padding:38px 44px; border-radius:14px; box-shadow:0 6px 24px rgba(0,0,0,.08); line-height:1.85; font-size:15px; }
  .r-title { text-align:center; font-size:26px; font-weight:800; letter-spacing:1px; margin:0 0 6px; background:linear-gradient(90deg,#2b6cb0,#2f9e8f); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
  .r-subtitle { text-align:center; color:#6b7280; font-size:13px; margin:0 0 16px; }
  .r-meta { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin:0 0 18px; }
  .r-chip { font-size:12px; color:#6b7280; background:#f4f6f8; border:1px solid #e5e7eb; border-radius:999px; padding:3px 12px; }
  h2.r-h2 { display:flex; align-items:center; gap:10px; font-size:18px; margin:24px 0 10px; padding:8px 12px; background:linear-gradient(90deg, rgba(47,158,143,.10), rgba(47,158,143,.02)); border-left:4px solid #2f9e8f; border-radius:6px; }
  .r-h2__no { flex:none; width:26px; height:26px; border-radius:7px; background:#2f9e8f; color:#fff; font-size:12px; display:inline-flex; align-items:center; justify-content:center; }
  h3.r-h3 { font-size:15px; color:#2f9e8f; margin:14px 0 6px; }
  .r-card { margin:10px 0; padding:12px 16px; background:#f7f9fa; border:1px solid #e5e7eb; border-left:4px solid #cbd5e1; border-radius:8px; }
  .r-card__head { font-weight:700; margin-bottom:4px; }
  .r-card--verdict { border-left-color:#2f9e8f; background:rgba(47,158,143,.07); }
  .r-card--verdict .r-card__head { color:#2f9e8f; }
  .r-card--warn { border-left-color:#e0a100; background:rgba(224,161,0,.08); }
  .r-card--warn .r-card__head { color:#b9790a; }
  .r-quote, blockquote { margin:10px 0; padding:8px 14px; border-left:4px solid #2f9e8f; background:#f5f8f7; color:#4b5563; border-radius:0 8px 8px 0; font-style:italic; }
  .r-tag { display:inline-block; font-size:12px; line-height:1; padding:3px 9px; border-radius:999px; margin:0 4px 2px 0; font-weight:600; color:#fff; }
  .r-tag--up { background:#2f9e8f; } .r-tag--down { background:#e05252; } .r-tag--mid { background:#8a95a5; } .r-tag--watch { background:#3b7dd8; }
  table.r-table { width:100%; border-collapse:collapse; margin:10px 0; font-size:13px; border-radius:8px; overflow:hidden; }
  table.r-table th, table.r-table td { border:1px solid #e5e7eb; padding:8px 10px; text-align:left; }
  table.r-table thead th { background:rgba(47,158,143,.12); }
  table.r-table tbody tr:nth-child(even) { background:#fafbfc; }
  ul.r-list, ul, ol { padding-left:22px; margin:8px 0; } li { margin:4px 0; }
  .r-timeline { margin:10px 0 4px; border-left:2px solid #e5e7eb; padding-left:14px; }
  .r-tl-item { position:relative; margin:0 0 12px; }
  .r-tl-dot { position:absolute; left:-20px; top:4px; width:10px; height:10px; border-radius:50%; background:#2f9e8f; box-shadow:0 0 0 3px rgba(47,158,143,.18); }
  .r-tl-body { color:#1f2329; }
  code { background:#eef1f3; padding:1px 5px; border-radius:4px; font-size:12px; }
  p { margin:6px 0; }
</style></head>
<body>${inner}</body></html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${title}.html`
  a.click()
  URL.revokeObjectURL(url)
}

// ---------- 步骤 4：对话 ----------
async function sendChat() {
  const text = chatInput.value.trim()
  if (!text || chatRunning.value) return
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  chatInput.value = ''
  chatRunning.value = true
  const ctrl = new AbortController()
  chatAbort.value = ctrl
  try {
    await streamChat(
      {
        world: world.value, setting: setting.value, personas: personas.value,
        question: question.value, transcript: transcript.value, report_text: reportText.value,
        messages: messages.value.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
        focus: focusAgent.value,
        model: model.value,
      },
      {
        onDelta: (d) => { messages.value[messages.value.length - 1].content += d; scrollChat() },
        signal: ctrl.signal,
      },
    )
  } catch (e: any) {
    if (e?.name !== 'AbortError') ElMessage.error(e?.message || '对话失败')
  } finally {
    chatRunning.value = false
    chatAbort.value = null
  }
}
async function scrollChat() {
  await nextTick()
  if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
}

// ---------- 存档 / 历史 ----------
async function saveCurrent(silent = false) {
  // 至少有一项内容才存档（推演记录 / 报告 / 图谱）
  if (saving.value) return
  if (!transcript.value.length && !reportText.value && !graph.value.nodes.length) return
  saving.value = true
  const payload = {
    title: (question.value.trim() || '数字沙盘推演').slice(0, 50),
    seed_text: seedText.value,
    question: question.value,
    world: world.value,
    setting: setting.value,
    personas: personas.value,
        transcript: transcript.value,
        report: cleanReportHtml(reportText.value),
        graph_json: graph.value,
    params: { agents: personas.value.length, rounds: rounds.value, god_events: godEvents.value },
    model: model.value,
  }
  try {
    if (currentId.value) {
      await updateProject(currentId.value, payload)
    } else {
      const res = await saveProject(payload)
      const id = res.data?.data?.id
      if (id) currentId.value = id
    }
    if (!silent) ElMessage.success('已存档')
  } catch (e: any) {
    if (!silent) ElMessage.error(e?.message || '存档失败')
  } finally {
    saving.value = false
  }
}

async function openHistory() {
  historyVisible.value = true
  historyLoading.value = true
  try {
    const res = await listProjects(50, 0)
    historyItems.value = res.data?.data?.items || []
  } catch { /* ignore */ } finally {
    historyLoading.value = false
  }
}

async function viewProject(id: string) {
  try {
    const res = await getProject(id)
    const d = res.data?.data
    if (!d) return
    seedText.value = d.seed_text || ''
    question.value = d.question || ''
    world.value = d.world || ''
    setting.value = d.setting || ''
    personas.value = d.personas || []
    transcript.value = d.transcript || []
    reportText.value = cleanReportHtml(d.report || '')
    graph.value = d.graph || { nodes: [], edges: [] }
    rounds.value = (d.params?.rounds as number) || rounds.value
    // 重放推演记录到控制台
    feed.value = []
    const seen = new Set<number>()
    for (const a of transcript.value) {
      if (!seen.has(a.round)) { seen.add(a.round); feed.value.push({ kind: 'round', round: a.round }) }
      feed.value.push({ kind: 'action', name: a.name, role: a.role, stance: a.stance, content: a.content })
    }
    historyVisible.value = false
    step.value = d.report ? 4 : (transcript.value.length ? 3 : (graph.value.nodes.length ? 2 : 1))
    currentId.value = id     // 后续自动存档会更新这条记录，而非新建
    ElMessage.success('已载入历史推演')
  } catch (e: any) {
    ElMessage.error(e?.message || '查看失败')
  }
}

async function removeProject(id: string) {
  try {
    await ElMessageBox.confirm('确定删除该推演存档？', '提示', { type: 'warning' })
  } catch { return }
  try {
    await deleteProject(id)
    historyItems.value = historyItems.value.filter((h) => h.id !== id)
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

// ---------- 工具 ----------
function stanceCN(s: string) {
  return ({ supportive: '支持', opposing: '反对', neutral: '中立', observer: '旁观' } as Record<string, string>)[s] || '中立'
}
function stanceTag(s: string): 'success' | 'danger' | 'info' | 'warning' {
  return ({ supportive: 'success', opposing: 'danger', neutral: 'info', observer: 'warning' } as Record<string, any>)[s] || 'info'
}
function fmtTime(t?: string) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 19)
}

// 轻量 Markdown → HTML（先转义，再渲染常见语法）
function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function renderMd(src: string): string {
  const esc = escapeHtml(src)
  const lines = esc.split('\n')
  let html = ''
  let inUl = false
  let inOl = false
  const closeLists = () => {
    if (inUl) { html += '</ul>'; inUl = false }
    if (inOl) { html += '</ol>'; inOl = false }
  }
  const inline = (t: string) =>
    t
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+?)`/g, '<code>$1</code>')
  for (const raw of lines) {
    const line = raw.trimEnd()
    if (/^###\s+/.test(line)) { closeLists(); html += `<h3>${inline(line.replace(/^###\s+/, ''))}</h3>` }
    else if (/^##\s+/.test(line)) { closeLists(); html += `<h2>${inline(line.replace(/^##\s+/, ''))}</h2>` }
    else if (/^#\s+/.test(line)) { closeLists(); html += `<h1>${inline(line.replace(/^#\s+/, ''))}</h1>` }
    else if (/^>\s?/.test(line)) { closeLists(); html += `<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>` }
    else if (/^[-*]\s+/.test(line)) {
      if (!inUl) { closeLists(); html += '<ul>'; inUl = true }
      html += `<li>${inline(line.replace(/^[-*]\s+/, ''))}</li>`
    }
    else if (/^\d+\.\s+/.test(line)) {
      if (!inOl) { closeLists(); html += '<ol>'; inOl = true }
      html += `<li>${inline(line.replace(/^\d+\.\s+/, ''))}</li>`
    }
    else if (line === '') { closeLists() }
    else { closeLists(); html += `<p>${inline(line)}</p>` }
  }
  closeLists()
  return html
}
// 清理 LLM 可能附带的代码围栏 / 整页包裹 / 前后缀说明文字，得到可安全直渲的 HTML 片段。
// 否则 ```html 围栏或 <html>/<style> 会被原样注入 v-html，造成「展示错误」与样式泄漏。
function cleanReportHtml(raw: string): string {
  if (!raw) return ''
  let s = raw.trim()
  // 1) 去掉 ``` 或 ~~~ 代码围栏（含可选语言标识，如 ```html）
  s = s.replace(/^```[a-zA-Z0-9_-]*\s*\n?/i, '').replace(/```\s*$/i, '')
  s = s.replace(/^~~~[a-zA-Z0-9_-]*\s*\n?/i, '').replace(/~~~\s*$/i, '')
  s = s.trim()
  // 2) 去掉 <style>/<head> 并拆掉 <html>/<body> 外层，避免样式泄漏到应用内
  s = s.replace(/<style[\s\S]*?<\/style>/gi, '')
  s = s.replace(/<head[\s\S]*?<\/head>/gi, '')
  s = s.replace(/<\/?(?:html|body)[^>]*>/gi, '')
  // 3) 仅当确认是 HTML 时，裁掉首尾的解释性文字（取首 '<' 到末 '>'）
  if (HTML_HINT.test(s)) {
    const a = s.indexOf('<')
    const b = s.lastIndexOf('>')
    if (a !== -1 && b !== -1 && b > a && (a > 0 || b < s.length - 1)) {
      s = s.slice(a, b + 1)
    }
  }
  return s.trim()
}

// 报告现为 LLM 直接产出的 HTML 片段；若检测到 HTML 标签则原样渲染，
// 否则回退到 Markdown 渲染（兼容此前以 Markdown 保存的历史报告）。
const HTML_HINT = /<(div|h1|h2|h3|table|blockquote|ul|ol|p|section|span)\b|<[a-z]+ class="r-/i
const reportHtml = computed(() => {
  const s = cleanReportHtml(reportText.value)
  return HTML_HINT.test(s) ? s : renderMd(s)
})

onMounted(loadModels)
</script>

<style scoped>
.ss-root { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.ss-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 4px 6px 12px; border-bottom: 1px solid var(--c-border); }
.ss-brand { display: flex; align-items: center; gap: 10px; }
.ss-brand__ico { font-size: 24px; color: var(--brand-emerald); }
.ss-brand__t { font-size: 16px; font-weight: 600; }
.ss-brand__s { font-size: 12px; color: var(--c-text-3); }
.ss-toolbar__right { display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 13px; color: var(--c-text-3); }
.sel { width: 220px; }

.ss-steps { padding: 12px 8% 4px; }

.ss-body { flex: 1; min-height: 0; overflow: auto; padding: 14px 18px 24px; }
.ss-panel { height: 100%; }
.ss-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start; }
.ss-cols--sim { grid-template-columns: 320px 1fr; }
.ss-cols--graph { grid-template-columns: 1.4fr 0.6fr; }
.ss-card { height: 100%; display: flex; flex-direction: column; }
.ss-card--graph :deep(.el-card__header) { display: flex; align-items: center; justify-content: space-between; }
.ss-graph { flex: 1; min-height: 0; }
.ss-card :deep(.el-card__body) { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.ss-card__t { font-weight: 600; }
.ss-card--console :deep(.el-card__header), .ss-card--chat :deep(.el-card__header) { display: flex; align-items: center; justify-content: space-between; }

.ss-field { margin-bottom: 14px; }
.ss-field label { display: block; font-size: 13px; color: var(--c-text-2); margin-bottom: 6px; }
.ss-count { text-align: right; font-size: 12px; color: var(--c-text-3); margin-top: 4px; }
.ss-params { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 6px; }
.ss-param label { display: block; font-size: 13px; color: var(--c-text-2); margin-bottom: 2px; }
.ss-run { width: 100%; margin-top: 8px; }
.ss-next { text-align: right; margin-top: 14px; }

.ss-empty { margin: auto; text-align: center; color: var(--c-text-3); max-width: 380px; }
.ss-empty__ico { font-size: 36px; opacity: 0.55; margin-bottom: 8px; }
.ss-empty p { font-size: 13px; line-height: 1.7; }

.ss-world__block { margin-bottom: 14px; }
.ss-world__h { font-size: 13px; font-weight: 600; color: var(--brand-emerald); margin-bottom: 6px; }
.ss-world__txt { font-size: 13px; line-height: 1.7; color: var(--c-text-1); white-space: pre-wrap; }
.ss-personas { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.ss-persona { border: 1px solid var(--c-border); border-radius: 8px; padding: 8px 10px; background: var(--c-bg-soft, #fafafa); }
.ss-persona__top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.ss-persona__name { font-weight: 600; font-size: 13px; }
.ss-persona__role { font-size: 12px; color: var(--c-text-2); margin: 3px 0; }
.ss-persona__voice { color: var(--brand-emerald); }
.ss-persona__desc { font-size: 12px; color: var(--c-text-3); line-height: 1.5; }

.ss-entities { display: flex; flex-wrap: wrap; gap: 6px; }
.ss-entity { cursor: default; }
.ss-entity__detail { border: 1px solid var(--c-border); border-radius: 8px; padding: 10px; background: var(--c-bg-soft, #fafafa); }
.ss-entity__detail strong { display: inline-block; margin-right: 8px; }
.ss-entity__detail p { font-size: 12px; color: var(--c-text-2); margin: 6px 0 0; line-height: 1.5; }

.ss-tip { font-size: 12px; color: var(--c-text-3); margin: 0 0 12px; line-height: 1.6; }
.ss-god { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.ss-god__at { font-size: 12px; color: var(--c-text-3); }
.ss-god__txt { flex: 1; }
.ss-god--add { margin-top: 4px; }

.ss-progress { font-size: 12px; color: var(--brand-emerald); font-weight: 600; }
.ss-feed { flex: 1; min-height: 0; overflow: auto; padding: 4px 2px; }
.ss-round { text-align: center; font-size: 12px; color: var(--c-text-3); margin: 12px 0 8px; letter-spacing: 2px; }
.ss-action { border-left: 3px solid var(--brand-emerald); background: var(--c-bg-soft, #fafafa); border-radius: 0 8px 8px 0; padding: 8px 12px; margin-bottom: 10px; }
.ss-action__head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.ss-action__name { font-weight: 600; font-size: 13px; }
.ss-action__content { font-size: 13px; line-height: 1.75; color: var(--c-text-1); white-space: pre-wrap; word-break: break-word; }
.ss-sim-actions { display: flex; gap: 10px; padding-top: 10px; border-top: 1px solid var(--c-border); }

.ss-result__tools { float: right; }
.ss-report { font-size: 14px; line-height: 1.85; color: var(--c-text-1); padding: 4px 6px; }
.ss-report :deep(h1), .ss-report :deep(h2), .ss-report :deep(h3) { line-height: 1.45; margin: 18px 0 10px; font-weight: 700; }
.ss-report :deep(h1) { font-size: 22px; }
.ss-report :deep(h2) { font-size: 18px; }
.ss-report :deep(h3) { font-size: 15px; color: var(--brand-emerald); }
/* 报告标题：居中 + 品牌渐变 + 装饰线 */
.ss-report :deep(.r-title) {
  text-align: center; font-size: 24px; font-weight: 800; letter-spacing: 1px; margin: 4px 0 6px;
  background: linear-gradient(90deg, #2b6cb0, #2f9e8f);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.ss-report :deep(.r-subtitle) { text-align: center; color: var(--c-text-2); font-size: 13px; margin: 0 0 14px; }
/* 信息胶囊 */
.ss-report :deep(.r-meta) { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 0 0 16px; }
.ss-report :deep(.r-chip) {
  font-size: 12px; color: var(--c-text-2); background: var(--c-bg-soft, #f4f6f8);
  border: 1px solid var(--c-border); border-radius: 999px; padding: 3px 12px;
}
/* 一级章节：左侧色条 + 编号徽标 */
.ss-report :deep(.r-h2) {
  display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; color: var(--c-text-1);
  margin: 22px 0 10px; padding: 8px 12px;
  background: linear-gradient(90deg, rgba(47,158,143,0.10), rgba(47,158,143,0.02));
  border-left: 4px solid var(--brand-emerald); border-radius: 6px;
}
.ss-report :deep(.r-h2__no) {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 7px; background: var(--brand-emerald);
  color: #fff; font-size: 12px; font-weight: 700;
}
.ss-report :deep(.r-h3) { font-size: 15px; color: var(--brand-emerald); margin: 14px 0 6px; }
/* 卡片 */
.ss-report :deep(.r-card) {
  margin: 10px 0; padding: 12px 16px; background: var(--c-bg-soft, #f7f9fa);
  border: 1px solid var(--c-border); border-left: 4px solid var(--c-border); border-radius: 8px;
}
.ss-report :deep(.r-card__head) { font-weight: 700; margin-bottom: 4px; color: var(--c-text-1); }
.ss-report :deep(.r-card--verdict) { border-left-color: var(--brand-emerald); background: rgba(47,158,143,0.07); }
.ss-report :deep(.r-card--verdict .r-card__head) { color: var(--brand-emerald); }
.ss-report :deep(.r-card--warn) { border-left-color: #e0a100; background: rgba(224,161,0,0.08); }
.ss-report :deep(.r-card--warn .r-card__head) { color: #b9790a; }
/* 引用 */
.ss-report :deep(.r-quote), .ss-report :deep(blockquote) {
  margin: 10px 0; padding: 8px 14px; border-left: 4px solid var(--brand-emerald);
  background: var(--c-bg-soft, #f5f8f7); color: var(--c-text-2); border-radius: 0 8px 8px 0; font-style: italic;
}
/* 立场标签 */
.ss-report :deep(.r-tag) {
  display: inline-block; font-size: 12px; line-height: 1; padding: 3px 9px; border-radius: 999px;
  margin: 0 4px 2px 0; font-weight: 600; color: #fff;
}
.ss-report :deep(.r-tag--up) { background: #2f9e8f; }
.ss-report :deep(.r-tag--down) { background: #e05252; }
.ss-report :deep(.r-tag--mid) { background: #8a95a5; }
.ss-report :deep(.r-tag--watch) { background: #3b7dd8; }
/* 表格 */
.ss-report :deep(.r-table), .ss-report :deep(table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; border-radius: 8px; overflow: hidden; }
.ss-report :deep(.r-table th), .ss-report :deep(.r-table td), .ss-report :deep(table th), .ss-report :deep(table td) { border: 1px solid var(--c-border); padding: 8px 10px; text-align: left; }
.ss-report :deep(.r-table thead th) { background: rgba(47,158,143,0.12); color: var(--c-text-1); font-weight: 700; }
.ss-report :deep(.r-table tbody tr:nth-child(even)) { background: var(--c-bg-soft, #fafbfc); }
/* 列表 */
.ss-report :deep(.r-list), .ss-report :deep(ul), .ss-report :deep(ol) { padding-left: 22px; margin: 8px 0; }
.ss-report :deep(.r-list li), .ss-report :deep(li) { margin: 4px 0; }
/* 时间线 */
.ss-report :deep(.r-timeline) { margin: 10px 0 4px; border-left: 2px solid var(--c-border); padding-left: 14px; }
.ss-report :deep(.r-tl-item) { position: relative; margin: 0 0 12px; }
.ss-report :deep(.r-tl-dot) {
  position: absolute; left: -20px; top: 4px; width: 10px; height: 10px; border-radius: 50%;
  background: var(--brand-emerald); box-shadow: 0 0 0 3px rgba(47,158,143,0.18);
}
.ss-report :deep(.r-tl-body) { color: var(--c-text-1); }
.ss-report :deep(p) { margin: 6px 0; }
.ss-report :deep(code) { background: var(--c-bg-soft, #eef1f3); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.ss-report :deep(strong) { color: var(--c-text-1); }

.ss-card--chat :deep(.el-card__body) { padding: 0; }
.ss-chat__focus { width: 160px; }
.ss-chat { flex: 1; min-height: 0; overflow: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.ss-msg { display: flex; }
.ss-msg--user { justify-content: flex-end; }
.ss-msg--ai { justify-content: flex-start; }
.ss-msg__bubble { max-width: 78%; padding: 8px 12px; border-radius: 10px; font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.ss-msg--user .ss-msg__bubble { background: var(--brand-emerald); color: #fff; }
.ss-msg--ai .ss-msg__bubble { background: var(--c-bg-soft, #f2f2f2); color: var(--c-text-1); }
.ss-chat__input { display: flex; gap: 10px; padding: 10px 14px; border-top: 1px solid var(--c-border); align-items: flex-end; }
.ss-chat__input .el-textarea { flex: 1; }

.ss-typing { display: inline-flex; gap: 4px; padding: 6px 2px; }
.ss-typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--c-text-3); opacity: 0.5; animation: blink 1.2s infinite; }
.ss-typing span:nth-child(2) { animation-delay: 0.2s; }
.ss-typing span:nth-child(3) { animation-delay: 0.4s; }
.ss-typing--msg { margin: 2px 0; }
@keyframes blink { 0%, 100% { opacity: 0.2; } 50% { opacity: 0.8; } }

.ss-history { padding: 4px; }
.ss-hitem { border: 1px solid var(--c-border); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.ss-hitem__top { display: flex; justify-content: space-between; gap: 8px; }
.ss-hitem__title { font-weight: 600; font-size: 14px; }
.ss-hitem__time { font-size: 12px; color: var(--c-text-3); white-space: nowrap; }
.ss-hitem__meta { font-size: 12px; color: var(--c-text-2); margin: 6px 0; line-height: 1.6; }
.ss-hitem__tags { display: flex; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.ss-hitem__actions { display: flex; gap: 8px; }
</style>
