<template>
  <div class="da-root">
    <!-- 顶部工具栏 -->
    <div class="da-toolbar">
      <div class="da-brand">
        <el-icon><DataAnalysis /></el-icon>
        <div>
          <div class="da-brand__t">AI 数据分析</div>
          <div class="da-brand__s">上传数据 · 自主探索 · ECharts 可视化 · AI 科学解读</div>
        </div>
      </div>
      <div class="da-tools">
        <el-button type="primary" :icon="Upload" @click="openFile">上传数据</el-button>
        <el-button :icon="Document" @click="showPaste = true">粘贴数据</el-button>
        <el-button :icon="MagicStick" :loading="autoLoading" @click="runAutoAnalysis">AI 自动分析</el-button>
        <el-button :icon="Picture" @click="exportPNG">导出图片</el-button>
        <el-button :icon="Download" @click="exportCSV">导出 CSV</el-button>
        <el-select v-model="sampleKey" placeholder="示例数据集" style="width: 170px" @change="onSample">
          <el-option v-for="s in SAMPLES" :key="s.key" :label="s.label" :value="s.key" />
        </el-select>
        <input ref="fileInput" type="file" accept=".csv,.tsv,.txt,.xlsx,.xls" hidden @change="onFileInput" />
      </div>
    </div>

    <div class="da-body">
      <!-- 左：数据来源 + 字段 + 编码 + 图型 -->
      <aside class="da-left">
        <div v-if="funding?.isFunding" class="da-fund-badge">
          <el-icon><Coin /></el-icon> 已识别为「资助 / 科研经费」数据
        </div>

        <div class="da-block">
          <div class="da-block__t">字段（{{ fields.length }}）</div>
          <div class="da-fields">
            <span v-for="f in fields" :key="f.name" class="da-field" :class="f.type">
              <i class="dot" :class="f.type"></i>{{ f.name }}
              <em>{{ f.type === 'number' ? '数值' : f.type === 'date' ? '日期' : '分类' }}</em>
            </span>
          </div>
        </div>

        <div class="da-block">
          <div class="da-block__t">字段编码</div>
          <div class="da-enc">
            <div v-for="z in ZONES" :key="z.key" class="da-enc__row">
              <label>{{ z.label }}</label>
              <el-select
                :model-value="(enc as any)[z.key]"
                clearable
                placeholder="--"
                size="small"
                @update:model-value="(v: string | null) => setEnc(z.key, v)"
              >
                <el-option
                  v-for="f in encOptions(z.key)"
                  :key="f.name"
                  :label="f.name"
                  :value="f.name"
                />
              </el-select>
            </div>
          </div>
        </div>

        <div class="da-block">
          <div class="da-block__t">图表类型</div>
          <div v-for="grp in chartGroups" :key="grp.cat" class="da-chgrp">
            <div class="da-chgrp__l">{{ grp.cat }}</div>
            <div class="da-charts">
              <button
                v-for="t in grp.items"
                :key="t.id"
                class="da-chart"
                :class="{ active: chartType === t.id }"
                @click="selectChart(t.id)"
              >
                {{ t.name }}
              </button>
            </div>
          </div>
        </div>

        <div class="da-block">
          <div class="da-block__t">选项</div>
          <div class="da-opts">
            <label>聚合</label>
            <el-select v-model="agg" size="small" @change="render">
              <el-option v-for="o in AGG_OPTS" :key="o[0]" :label="o[1]" :value="o[0]" />
            </el-select>
            <label>配色</label>
            <el-select v-model="colorTheme" size="small" @change="render">
              <el-option v-for="o in PALETTE_OPTS" :key="o[0]" :label="o[1]" :value="o[0]" />
            </el-select>
            <label>Top N</label>
            <el-select v-model="topN" size="small" @change="render">
              <el-option v-for="o in TOPN_OPTS" :key="o[0]" :label="o[1]" :value="o[0]" />
            </el-select>
            <label class="da-check">
              <el-checkbox v-model="binX" @change="render" /> X 轴分箱
            </label>
            <label class="da-check">
              <el-checkbox v-model="stack" @change="render" /> 颜色堆叠
            </label>
          </div>
        </div>
      </aside>

      <!-- 中：视图 + 图表 -->
      <main class="da-center">
        <div class="da-viewtabs">
          <button
            v-for="v in viewTabs"
            :key="v.id"
            class="da-vt"
            :class="{ active: view === v.id }"
            @click="switchView(v.id)"
          >
            {{ v.name }}
          </button>
          <span class="da-status">{{ status }}</span>
        </div>

        <div v-show="view === 'chart'" ref="chartEl" class="da-chartbox"></div>

        <div v-show="view === 'pivot'" class="da-html" v-html="pivotHtml"></div>
        <div v-show="view === 'table'" class="da-html" v-html="tableHtml"></div>
        <div v-show="view === 'stats'" class="da-html" v-html="statsHtml"></div>
        <div v-show="view === 'corr'" class="da-html" v-html="corrHtml"></div>

        <div v-show="view === 'funding'" v-if="funding?.isFunding" class="da-funding">
          <div class="da-fund-cards">
            <div class="da-fc"><span>资助总额</span><b>{{ fundTotal }}</b></div>
            <div class="da-fc"><span>项目数</span><b>{{ rawRows.length }}</b></div>
            <div class="da-fc"><span>承担机构</span><b>{{ fundByOrg.length }}</b></div>
            <div class="da-fc"><span>覆盖年份</span><b>{{ fundByYear.length }}</b></div>
          </div>
          <el-row :gutter="12">
            <el-col :span="12">
              <div class="da-sub">各机构资助排名（Top 10）</div>
              <div ref="fundBarEl" class="da-mini"></div>
            </el-col>
            <el-col :span="12">
              <div class="da-sub">资助类别分布</div>
              <div ref="fundPieEl" class="da-mini"></div>
            </el-col>
          </el-row>
          <div class="da-sub">各年度资助趋势</div>
          <div ref="fundLineEl" class="da-mini da-mini--lg"></div>
        </div>
      </main>

      <!-- 右：AI 面板 -->
      <aside class="da-right">
        <div class="da-ai">
          <div class="da-ai__t"><el-icon><MagicStick /></el-icon> AI 自动分析</div>
          <el-button size="small" type="primary" :loading="autoLoading" @click="runAutoAnalysis">
            {{ autoInsight ? '重新生成' : '生成分析' }}
          </el-button>
          <pre class="da-ai__body" v-if="autoInsight">{{ autoInsight }}</pre>
          <div class="da-ai__empty" v-else>基于已载入数据，自动生成统计指标、趋势、相关性与建议。</div>
        </div>

        <div class="da-ai da-ai--chat">
          <div class="da-ai__t"><el-icon><ChatDotRound /></el-icon> AI 数据对话</div>
          <div class="da-chat" ref="chatBox">
            <div
              v-for="(m, i) in aiMessages"
              :key="i"
              class="da-msg"
              :class="m.role"
            >
              <div class="da-msg__role">{{ m.role === 'user' ? '我' : 'AI' }}</div>
              <pre class="da-msg__c">{{ m.content }}</pre>
            </div>
            <div v-if="aiStreaming" class="da-msg assistant"><div class="da-msg__role">AI</div><div class="da-typing">思考中…</div></div>
          </div>
          <div class="da-chatin">
            <el-input
              v-model="aiInput"
              type="textarea"
              :rows="2"
              resize="none"
              placeholder="就这份数据提问，如：哪些机构的资助额度最高？"
              @keydown.ctrl.enter="sendChat"
            />
            <el-button type="primary" :loading="aiStreaming" @click="sendChat">发送</el-button>
          </div>
        </div>
      </aside>
    </div>

    <!-- 粘贴对话框 -->
    <el-dialog v-model="showPaste" title="粘贴 CSV / TSV 数据" width="560px">
      <p class="da-muted">首行作为表头；支持逗号或制表符分隔。</p>
      <el-input v-model="pasteText" type="textarea" :rows="10" placeholder="col1,col2,col3&#10;1,2,3&#10;4,5,6" />
      <template #footer>
        <el-button @click="showPaste = false">取消</el-button>
        <el-button type="primary" @click="applyPaste">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { DataAnalysis, MagicStick, Upload, Document, Picture, Download, Coin, ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  parseCSV,
  parseExcel,
  inferFields,
  detectFundingSchema,
  buildProfile,
  loadSample,
  SAMPLES,
  stats,
  correlationMatrix,
  aggregate,
  fmt,
  escapeHtml,
  type Dataset,
  type FieldInfo,
  type FundingSchema,
} from './analytics'
import { build, CHART_TYPES, echarts, ensure3D, type Enc } from './chartEngine'
import { streamDataChat } from '@/api/llm'

const props = defineProps<{ code?: string; name?: string }>()

/* ----------------------------- 状态 ----------------------------- */
const fileInput = ref<HTMLInputElement | null>(null)
const chartEl = ref<HTMLElement | null>(null)
const fundBarEl = ref<HTMLElement | null>(null)
const fundPieEl = ref<HTMLElement | null>(null)
const fundLineEl = ref<HTMLElement | null>(null)
const chatBox = ref<HTMLElement | null>(null)

const rawRows = ref<Record<string, any>[]>([])
const fields = ref<FieldInfo[]>([])
const enc = reactive<Enc>({ x: null, y: null, z: null, color: null, size: null, filter: null })
const filterValues = reactive<Record<string, Set<string>>>({})
const chartType = ref('bar')
const agg = ref('sum')
const colorTheme = ref('classic')
const topN = ref(0)
const binX = ref(false)
const stack = ref(false)
type ViewId = 'chart' | 'pivot' | 'table' | 'stats' | 'corr' | 'funding'
const view = ref<ViewId>('chart')
const status = ref('请上传或选择数据')
const sampleKey = ref('')

const funding = ref<FundingSchema | null>(null)
let chartInst: any = null
let fundBarInst: any = null
let fundPieInst: any = null
let fundLineInst: any = null

/* ----------------------------- 常量 ----------------------------- */
const ZONES = [
  { key: 'x', label: 'X 轴 / 行' },
  { key: 'y', label: 'Y 轴 / 值' },
  { key: 'z', label: 'Z 轴 (3D)' },
  { key: 'color', label: '颜色' },
  { key: 'size', label: '大小' },
  { key: 'filter', label: '筛选' },
] as const

const AGG_OPTS: [string, string][] = [['sum', '求和'], ['avg', '均值'], ['count', '计数'], ['max', '最大值'], ['min', '最小值'], ['median', '中位数']]
const PALETTE_OPTS: [string, string][] = [['classic', '经典'], ['academic', '学术'], ['vivid', '鲜明']]
const TOPN_OPTS: [string, number][] = [['0', 0], ['5', 5], ['10', 10], ['15', 15], ['20', 20]]

const chartGroups = computed(() => {
  const cats: Record<string, typeof CHART_TYPES> = {}
  CHART_TYPES.forEach((t) => { (cats[t.cat] = cats[t.cat] || []).push(t) })
  return Object.keys(cats).map((cat) => ({ cat, items: cats[cat] }))
})

const viewTabs = computed<{ id: ViewId; name: string }[]>(() => {
  const base: { id: ViewId; name: string }[] = [
    { id: 'chart', name: '📊 图表' },
    { id: 'pivot', name: '📑 透视' },
    { id: 'table', name: '🔢 数据表' },
    { id: 'stats', name: '📈 统计' },
    { id: 'corr', name: '🔗 相关性' },
  ]
  if (funding.value?.isFunding) base.push({ id: 'funding', name: '💰 资助分析' })
  return base
})

/* ----------------------------- 计算 ----------------------------- */
const dataset = computed<Dataset>(() => ({ headers: fields.value.map((f) => f.name), rows: rawRows.value }))
const filteredRows = computed(() => {
  let rows = rawRows.value
  const f = enc.filter
  if (f && filterValues[f] && filterValues[f].size) {
    const allowed = filterValues[f]
    rows = rows.filter((r) => allowed.has(String(r[f] == null ? '' : r[f])))
  }
  return rows
})
const dataProfile = computed(() => (rawRows.value.length ? buildProfile(dataset.value, fields.value, funding.value || undefined) : ''))

const numericFields = computed(() => fields.value.filter((f) => f.type === 'number'))
const catFields = computed(() => fields.value.filter((f) => f.type !== 'number'))

function encOptions(key: string): FieldInfo[] {
  if (key === 'color' || key === 'filter') return catFields.value
  if (key === 'x' || key === 'y' || key === 'z' || key === 'size') return fields.value
  return fields.value
}

/* ----------------------------- 资助聚合 ----------------------------- */
const fundTotal = computed(() => {
  if (!funding.value?.amount) return '—'
  const t = rawRows.value.reduce((s, r) => s + (Number(r[funding.value!.amount!]) || 0), 0)
  return fmt(t)
})
const fundByOrg = computed(() => {
  if (!funding.value?.org || !funding.value?.amount) return []
  return aggregate(rawRows.value, [funding.value.org], funding.value.amount, 'sum')
    .sort((a, b) => b.value - a.value)
})
const fundByRegion = computed(() => {
  if (!funding.value?.region || !funding.value?.amount) return []
  return aggregate(rawRows.value, [funding.value.region], funding.value.amount, 'sum').sort((a, b) => b.value - a.value)
})
const fundByCategory = computed(() => {
  if (!funding.value?.category || !funding.value?.amount) return []
  return aggregate(rawRows.value, [funding.value.category], funding.value.amount, 'sum')
})
const fundByYear = computed(() => {
  if (!funding.value?.year) return []
  const m = funding.value.amount || funding.value.project || funding.value.org || ''
  return aggregate(rawRows.value, [funding.value.year], m, 'count').sort((a, b) => String(a.dims[0]).localeCompare(String(b.dims[0])))
})

/* ----------------------------- HTML 视图 ----------------------------- */
const pivotHtml = computed(() => buildPivot(filteredRows.value))
const tableHtml = computed(() => buildTable(filteredRows.value))
const statsHtml = computed(() => buildStats(filteredRows.value))
const corrHtml = computed(() => buildCorr(filteredRows.value))

function buildPivot(rows: Record<string, any>[]): string {
  const xf = enc.x
  const cf = enc.color
  const mf = enc.y
  if (!xf) return '<div class="da-empty">将字段拖入「X 轴 / 行」作为透视行维度。</div>'
  const measure = mf || xf
  const mode = mf && isNum(fields.value, mf) ? agg.value : 'count'
  const rowCats = [...new Set(rows.map((r) => String(r[xf] == null ? '' : r[xf])))].sort()
  const colCats = cf ? [...new Set(rows.map((r) => String(r[cf] == null ? '' : r[cf])))].sort() : ['合计']
  const aggV = (rc: string, cc: string) => {
    const sub = rows.filter((r) => String(r[xf] == null ? '' : r[xf]) === rc && (!cf || String(r[cf] == null ? '' : r[cf]) === cc))
    const vals = sub.map((r) => Number(r[measure])).filter((v) => !isNaN(v))
    return aggFnLocal(mode, vals)
  }
  let html = `<h3>数据透视表</h3><p class="da-muted">行：${xf} ｜ 列：${cf || '—'} ｜ 值：${measure}（${mode}）｜ ${rows.length} 行</p><div class="da-scroll"><table class="da-tbl"><thead><tr><th>${xf}</th>${colCats.map((c) => `<th>${escapeHtml(c)}</th>`).join('')}<th>行合计</th></tr></thead><tbody>`
  let grand = 0
  const colTotals = colCats.map(() => 0)
  rowCats.forEach((rc) => {
    let rowTotal = 0
    html += `<tr><th>${escapeHtml(rc)}</th>`
    colCats.forEach((cc, ci) => {
      const v = aggV(rc, cc)
      rowTotal += v
      colTotals[ci] += v
      html += `<td>${fmt(v)}</td>`
    })
    grand += rowTotal
    html += `<td class="da-tot">${fmt(rowTotal)}</td></tr>`
  })
  html += `<tr class="da-tot"><th>列合计</th>${colTotals.map((c) => `<td class="da-tot">${fmt(c)}</td>`).join('')}<td class="da-tot">${fmt(grand)}</td></tr></tbody></table></div>`
  return html
}

function buildTable(rows: Record<string, any>[]): string {
  const headers = fields.value.map((f) => f.name)
  const limit = Math.min(rows.length, 300)
  let html = `<h3>数据表（前 ${limit} / ${rows.length} 行）</h3><div class="da-scroll"><table class="da-tbl"><thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('')}</tr></thead><tbody>`
  for (let i = 0; i < limit; i++) html += `<tr>${headers.map((h) => `<td>${escapeHtml(rows[i][h])}</td>`).join('')}</tr>`
  return html + '</tbody></table></div>'
}

function buildStats(rows: Record<string, any>[]): string {
  if (!numericFields.value.length) return '<div class="da-empty">无数值字段可统计。</div>'
  let html = '<h3>描述性统计摘要</h3><div class="da-scroll"><table class="da-tbl"><thead><tr><th>字段</th><th>计数</th><th>缺失</th><th>均值</th><th>标准差</th><th>最小</th><th>Q1</th><th>中位</th><th>Q3</th><th>最大</th><th>总和</th></tr></thead><tbody>'
  numericFields.value.forEach((f) => {
    const s = stats(rows, f.name)
    if (!s) return
    html += `<tr><th>${escapeHtml(f.name)}</th><td>${s.count}</td><td>${s.missing}</td><td>${fmt(s.mean)}</td><td>${fmt(s.std)}</td><td>${fmt(s.min)}</td><td>${fmt(s.q1)}</td><td>${fmt(s.median)}</td><td>${fmt(s.q3)}</td><td>${fmt(s.max)}</td><td>${fmt(s.sum)}</td></tr>`
  })
  return html + '</tbody></table></div>'
}

function buildCorr(rows: Record<string, any>[]): string {
  if (numericFields.value.length < 2) return '<div class="da-empty">至少需要 2 个数值字段才能计算相关性。</div>'
  const cm = correlationMatrix(rows, numericFields.value.map((f) => f.name))
  const color = (r: number) => {
    const a = Math.min(1, Math.abs(r))
    return r >= 0 ? `rgba(16,185,129,${0.12 + a * 0.6})` : `rgba(239,68,68,${0.12 + a * 0.6})`
  }
  let html = '<h3>相关性矩阵（Pearson r）</h3><div class="da-scroll"><table class="da-tbl da-corr"><thead><tr><th></th>' + cm.fields.map((f) => `<th>${escapeHtml(f)}</th>`).join('') + '</tr></thead><tbody>'
  cm.fields.forEach((f, i) => {
    html += `<tr><th>${escapeHtml(f)}</th>`
    cm.fields.forEach((_, j) => {
      const v = cm.matrix[i][j]
      html += `<td style="background:${color(v)}">${v.toFixed(2)}</td>`
    })
    html += '</tr>'
  })
  return html + '</tbody></table></div><p class="da-muted">绿色为正相关、红色为负相关；|r|≥0.5 视为强相关。</p>'
}

function aggFnLocal(mode: string, vals: number[]): number {
  const a = vals.filter((v) => !isNaN(v))
  if (!a.length) return 0
  switch (mode) {
    case 'sum': return a.reduce((s, v) => s + v, 0)
    case 'avg': return a.reduce((s, v) => s + v, 0) / a.length
    case 'count': return vals.length
    case 'max': return Math.max.apply(null, a)
    case 'min': return Math.min.apply(null, a)
    case 'median': return quantileLocal(a.slice().sort((x, y) => x - y), 0.5)
    default: return a.reduce((s, v) => s + v, 0)
  }
}
function quantileLocal(sorted: number[], q: number): number {
  if (!sorted.length) return NaN
  const pos = (sorted.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  return sorted[base + 1] !== undefined ? sorted[base] + rest * (sorted[base + 1] - sorted[base]) : sorted[base]
}
function isNum(fs: FieldInfo[], f: string): boolean {
  return !!fs.find((x) => x.name === f && x.type === 'number')
}

/* ----------------------------- 渲染 ----------------------------- */
function chartName(): string {
  const t = CHART_TYPES.find((x) => x.id === chartType.value)
  return t ? t.name : chartType.value
}

async function render() {
  if (view.value !== 'chart') return
  if (!chartEl.value) return
  if (!chartInst) chartInst = echarts.init(chartEl.value)
  // 3D 图表依赖 echarts-gl，按需加载；不可用时给出提示而非静默失败
  if (chartType.value === 'scatter3d') {
    const ok = await ensure3D()
    if (!ok) {
      status.value = '⚠ 3D 图表组件（echarts-gl）加载失败，请改用其他图表类型'
      chartInst.clear()
      return
    }
  }
  const ctx = {
    rows: filteredRows.value,
    fields: fields.value,
    enc: { ...enc },
    chartType: chartType.value,
    agg: agg.value,
    colorTheme: colorTheme.value,
    topN: topN.value,
    binX: binX.value,
    stack: stack.value,
  }
  let option: any
  try {
    option = build(ctx)
  } catch (e: any) {
    status.value = '⚠ ' + (e?.message || '图表构建失败')
    chartInst.clear()
    return
  }
  if (option && option._warn) {
    status.value = '⚠ ' + option._warn
    chartInst.clear()
    return
  }
  status.value = `当前：${chartName()} · ${ctx.rows.length} 行（已筛选）`
  chartInst.setOption(option, true)
  chartInst.resize()
}

function renderFundCharts() {
  if (!funding.value?.isFunding) return
  nextTick(() => {
    if (fundBarEl.value) {
      if (!fundBarInst) fundBarInst = echarts.init(fundBarEl.value)
      const top = fundByOrg.value.slice(0, 10).reverse()
      fundBarInst.setOption({
        grid: { left: 90, right: 16, top: 10, bottom: 20 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: top.map((d) => String(d.dims[0])) },
        series: [{ type: 'bar', data: top.map((d) => d.value), itemStyle: { color: '#10b981' }, barMaxWidth: 18 }],
      })
    }
    if (fundPieEl.value) {
      if (!fundPieInst) fundPieInst = echarts.init(fundPieEl.value)
      const palette = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6', '#ec4899', '#6366f1']
      fundPieInst.setOption({
        color: palette,
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { type: 'scroll', orient: 'vertical', right: 4, top: 6 },
        series: [{
          type: 'pie', radius: ['35%', '68%'], center: ['38%', '52%'],
          data: fundByCategory.value.map((d) => ({ name: String(d.dims[0]), value: d.value })),
          label: { formatter: '{b}\n{d}%' },
        }],
      })
    }
    if (fundLineEl.value) {
      if (!fundLineInst) fundLineInst = echarts.init(fundLineEl.value)
      fundLineInst.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 50, right: 20, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: fundByYear.value.map((d) => String(d.dims[0])) },
        yAxis: { type: 'value', name: '项目数' },
        series: [{ type: 'line', smooth: true, data: fundByYear.value.map((d) => d.value), areaStyle: { opacity: 0.2 }, itemStyle: { color: '#3b82f6' } }],
      })
    }
  })
}

function switchView(v: ViewId) {
  view.value = v
  if (v === 'funding') renderFundCharts()
  else if (v === 'chart') nextTick(render)
}

/* ----------------------------- 编码 / 图型 ----------------------------- */
function setEnc(key: keyof Enc, v: string | null) {
  ;(enc as any)[key] = v
  if (key === 'filter' && v) {
    if (!filterValues[v]) filterValues[v] = new Set()
  }
  if (view.value === 'chart') render()
}

function suggestEncodings(type: string) {
  const nums = fields.value.filter((f) => f.type === 'number')
  const cats = fields.value.filter((f) => f.type !== 'number')
  const set = (k: keyof Enc, v?: string) => { if (!enc[k]) (enc as any)[k] = v || null }
  if (type === 'scatter3d') {
    set('x', nums[0]?.name); set('y', nums[1]?.name); set('z', nums[2]?.name); set('color', cats[0]?.name)
  } else if (type === 'scatter' || type === 'regression') {
    set('x', nums[0]?.name); set('y', nums[1]?.name); set('color', cats[0]?.name)
  } else if (type === 'boxplot' || type === 'violin') {
    set('x', cats[0]?.name); set('y', nums[0]?.name); set('color', cats[1]?.name)
  } else if (type === 'histogram' || type === 'density') {
    set('y', nums[0]?.name); set('color', cats[0]?.name)
  } else if (type === 'pie' || type === 'radar') {
    set('x', cats[0]?.name); set('y', nums[0]?.name); set('color', cats[1]?.name)
  } else if (type === 'heatmap' || type === 'sankey') {
    set('x', cats[0]?.name); set('y', cats[1]?.name); set('size', nums[0]?.name)
  } else if (type === 'parallel') {
    set('x', nums[0]?.name); set('y', nums[1]?.name); set('z', nums[2]?.name); set('size', nums[3]?.name); set('color', cats[0]?.name)
  } else {
    set('x', cats[0]?.name); set('y', nums[0]?.name); set('color', cats[1]?.name)
  }
}

function selectChart(type: string) {
  chartType.value = type
  suggestEncodings(type)
  if (view.value === 'chart') render()
}

/* ----------------------------- 数据载入 ----------------------------- */
function ingest(ds: Dataset, name: string) {
  if (!ds.headers.length) {
    ElMessage.error('未识别到表头或数据，请检查文件格式。')
    return
  }
  rawRows.value = ds.rows
  fields.value = inferFields(ds)
  enc.x = enc.y = enc.z = enc.color = enc.size = enc.filter = null
  Object.keys(filterValues).forEach((k) => delete filterValues[k])
  funding.value = detectFundingSchema(fields.value)
  if (funding.value?.isFunding) {
    // 资助数据：预置编码，直接给出分析视图
    enc.x = funding.value.year || catFields.value[0]?.name || null
    enc.y = funding.value.amount || numericFields.value[0]?.name || null
    enc.color = funding.value.org || catFields.value[1]?.name || null
    chartType.value = 'bar'
  } else {
    suggestEncodings(chartType.value)
  }
  status.value = `已载入「${name}」：${ds.rows.length} 行 × ${ds.headers.length} 列`
  if (funding.value?.isFunding) view.value = 'funding'
  else view.value = 'chart'
  nextTick(() => { render(); if (funding.value?.isFunding) renderFundCharts() })
}

function openFile() {
  fileInput.value?.click()
}

function onFileInput(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) handleFile(f)
  ;(e.target as HTMLInputElement).value = ''
}
async function handleFile(f: File) {
  const name = f.name.toLowerCase()
  try {
    if (name.endsWith('.csv') || name.endsWith('.txt') || name.endsWith('.tsv')) {
      const text = await f.text()
      ingest(parseCSV(text), f.name)
    } else if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
      const buf = await f.arrayBuffer()
      ingest(await parseExcel(buf), f.name)
    } else {
      ElMessage.warning('仅支持 CSV / TSV / Excel(.xlsx/.xls) 文件')
    }
  } catch (e: any) {
    ElMessage.error('解析失败：' + (e?.message || e))
  }
}
function onSample(key: string) {
  if (!key) return
  const ds = loadSample(key)
  const s = SAMPLES.find((x) => x.key === key)
  ingest(ds, s?.label || key)
}
const showPaste = ref(false)
const pasteText = ref('')
function applyPaste() {
  const t = pasteText.value.trim()
  if (!t) return
  ingest(parseCSV(t), '粘贴数据')
  showPaste.value = false
  pasteText.value = ''
}

/* ----------------------------- 导出 ----------------------------- */
function exportPNG() {
  if (!chartInst) return
  const url = chartInst.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url
  a.download = `analysis_${chartType.value}.png`
  a.click()
}
function exportCSV() {
  const rows = filteredRows.value
  if (!rows.length) return
  const headers = fields.value.map((f) => f.name)
  const cell = (v: any) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
  }
  const lines = [headers.join(',')]
  rows.forEach((r) => lines.push(headers.map((h) => cell(r[h])).join(',')))
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'analysis_filtered.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

/* ----------------------------- AI ----------------------------- */
const autoInsight = ref('')
const autoLoading = ref(false)
async function runAutoAnalysis() {
  if (!rawRows.value.length) {
    ElMessage.warning('请先上传或选择数据')
    return
  }
  autoLoading.value = true
  autoInsight.value = ''
  const profile = dataProfile.value
  const prompt =
    '请对这份数据做整体科学分析：1) 总体画像与关键指标；2) 主要趋势（尤其随时间/维度的变化）；3) 数值字段间的相关性及业务含义；4) 异常或风险点；5) 给出 3-5 条可操作建议。结论前置，使用 Markdown。'
  try {
    for await (const delta of streamDataChat([{ role: 'user', content: prompt }], profile, { temperature: 0.5 })) {
      autoInsight.value += delta
    }
    if (!autoInsight.value) autoInsight.value = '（模型未返回内容，请检查大模型配置）'
  } catch (e: any) {
    autoInsight.value = '⚠ ' + (e?.message || '分析失败') + '\n\n请先在「系统管理 → 大模型接入」配置并设默认一个 OpenAI 兼容服务。'
  } finally {
    autoLoading.value = false
  }
}

const aiMessages = ref<{ role: string; content: string }[]>([])
const aiInput = ref('')
const aiStreaming = ref(false)
let aiAbort: AbortController | null = null
async function sendChat() {
  const text = aiInput.value.trim()
  if (!text || aiStreaming.value) return
  if (!rawRows.value.length) {
    ElMessage.warning('请先上传或选择数据，AI 才能基于数据作答')
    return
  }
  aiMessages.value.push({ role: 'user', content: text })
  aiInput.value = ''
  const assistant = { role: 'assistant', content: '' }
  aiMessages.value.push(assistant)
  aiStreaming.value = true
  const history = aiMessages.value.filter((m) => m !== assistant).map((m) => ({ role: m.role, content: m.content }))
  await nextTick(() => chatBox.value && (chatBox.value.scrollTop = chatBox.value.scrollHeight))
  try {
    aiAbort = new AbortController()
    for await (const delta of streamDataChat(history, dataProfile.value, { signal: aiAbort.signal })) {
      assistant.content += delta
      if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  } catch (e: any) {
    assistant.content += '\n\n⚠ ' + (e?.message || '对话失败')
  } finally {
    aiStreaming.value = false
    aiAbort = null
  }
}

/* ----------------------------- 生命周期 ----------------------------- */
function onResize() {
  chartInst?.resize()
  fundBarInst?.resize()
  fundPieInst?.resize()
  fundLineInst?.resize()
}
onMounted(() => {
  window.addEventListener('resize', onResize)
  // 默认载入示例，便于即时体验
  onSample('sales')
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chartInst?.dispose()
  fundBarInst?.dispose()
  fundPieInst?.dispose()
  fundLineInst?.dispose()
  aiAbort?.abort()
})
</script>

<style scoped>
.da-root { position: absolute; inset: 0; display: flex; flex-direction: column; background: var(--c-surface, #f5f7fa); color: var(--c-text-1); font-size: 13px; }
.da-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; background: var(--c-surface-2, #fff); border-bottom: 1px solid var(--c-border, #e5e7eb); }
.da-brand { display: flex; align-items: center; gap: 10px; }
.da-brand .el-icon { font-size: 26px; color: var(--brand-emerald, #10b981); }
.da-brand__t { font-weight: 700; font-size: 16px; }
.da-brand__s { color: var(--c-text-3, #94a3b8); font-size: 12px; }
.da-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.da-body { flex: 1; display: grid; grid-template-columns: 280px 1fr 340px; min-height: 0; }
.da-left { overflow: auto; padding: 12px; border-right: 1px solid var(--c-border, #e5e7eb); background: var(--c-surface-2, #fff); }
.da-center { overflow: auto; padding: 12px; min-width: 0; }
.da-right { overflow: auto; padding: 12px; border-left: 1px solid var(--c-border, #e5e7eb); background: var(--c-surface-2, #fff); display: flex; flex-direction: column; gap: 12px; }

.da-fund-badge { display: flex; align-items: center; gap: 6px; background: rgba(16,185,129,0.12); color: #047857; border: 1px solid rgba(16,185,129,0.4); padding: 6px 10px; border-radius: 8px; font-size: 12px; margin-bottom: 10px; }
.da-fund-badge .el-icon { color: #10b981; }

.da-block { margin-bottom: 14px; }
.da-block__t { font-weight: 600; color: var(--c-text-2); margin-bottom: 8px; font-size: 12px; }
.da-fields { display: flex; flex-wrap: wrap; gap: 6px; }
.da-field { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 6px; background: var(--c-surface-3, #f1f5f9); font-size: 12px; border: 1px solid var(--c-border, #e5e7eb); }
.da-field em { font-style: normal; color: var(--c-text-3); font-size: 11px; }
.da-field .dot { width: 7px; height: 7px; border-radius: 50%; }
.dot.number { background: #3b82f6; } .dot.category { background: #f59e0b; } .dot.date { background: #8b5cf6; }

.da-enc__row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.da-enc__row label { width: 72px; color: var(--c-text-2); font-size: 12px; }

.da-chgrp { margin-bottom: 8px; }
.da-chgrp__l { font-size: 11px; color: var(--c-text-3); margin: 4px 0; }
.da-charts { display: flex; flex-wrap: wrap; gap: 5px; }
.da-chart { cursor: pointer; border: 1px solid var(--c-border, #e5e7eb); background: var(--c-surface-3, #f1f5f9); border-radius: 6px; padding: 4px 8px; font-size: 12px; color: var(--c-text-1); transition: all 0.15s; }
.da-chart:hover { border-color: var(--brand-emerald, #10b981); }
.da-chart.active { background: var(--brand-grad-soft, rgba(16,185,129,0.15)); border-color: var(--brand-emerald, #10b981); color: #047857; font-weight: 600; }

.da-opts { display: grid; grid-template-columns: auto 1fr; gap: 6px 8px; align-items: center; }
.da-opts label { color: var(--c-text-2); font-size: 12px; }
.da-check { grid-column: 1 / -1; display: flex; align-items: center; gap: 6px; }

.da-viewtabs { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
.da-vt { cursor: pointer; border: 1px solid var(--c-border, #e5e7eb); background: var(--c-surface-2, #fff); border-radius: 6px; padding: 5px 10px; font-size: 12px; }
.da-vt.active { background: var(--brand-emerald, #10b981); color: #fff; border-color: var(--brand-emerald, #10b981); }
.da-status { margin-left: auto; color: var(--c-text-3); font-size: 12px; }

.da-chartbox { width: 100%; height: 560px; background: #fff; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; }
.da-html { background: #fff; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; padding: 12px; }
.da-empty { color: var(--c-text-3); padding: 30px; text-align: center; }
.da-muted { color: var(--c-text-3); font-size: 12px; }
.da-scroll { overflow: auto; max-height: 520px; }
.da-tbl { border-collapse: collapse; width: 100%; font-size: 12px; }
.da-tbl th, .da-tbl td { border: 1px solid var(--c-border, #e5e7eb); padding: 5px 8px; text-align: right; white-space: nowrap; }
.da-tbl th { background: var(--c-surface-3, #f1f5f9); position: sticky; top: 0; }
.da-tbl td:first-child, .da-tbl th:first-child { text-align: left; }
.da-tot { font-weight: 700; background: rgba(16,185,129,0.08); }
.da-corr td { text-align: center; font-variant-numeric: tabular-nums; }

.da-funding { background: #fff; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; padding: 12px; }
.da-fund-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; }
.da-fc { background: var(--c-surface-3, #f1f5f9); border-radius: 8px; padding: 10px; text-align: center; }
.da-fc span { display: block; color: var(--c-text-3); font-size: 11px; }
.da-fc b { font-size: 18px; color: var(--brand-emerald, #10b981); }
.da-sub { font-weight: 600; margin: 10px 0 4px; color: var(--c-text-2); }
.da-mini { width: 100%; height: 240px; }
.da-mini--lg { height: 220px; }

.da-ai { border: 1px solid var(--c-border, #e5e7eb); border-radius: 10px; padding: 10px; background: #fff; display: flex; flex-direction: column; }
.da-ai__t { display: flex; align-items: center; gap: 6px; font-weight: 600; margin-bottom: 8px; }
.da-ai__t .el-icon { color: var(--brand-emerald, #10b981); }
.da-ai__body { white-space: pre-wrap; word-break: break-word; font-size: 12.5px; line-height: 1.6; max-height: 280px; overflow: auto; margin: 8px 0 0; color: var(--c-text-1); }
.da-ai__empty { color: var(--c-text-3); font-size: 12px; padding: 12px 0; }
.da-ai--chat { flex: 1; min-height: 0; }

.da-chat { flex: 1; overflow: auto; min-height: 160px; max-height: 360px; display: flex; flex-direction: column; gap: 8px; padding: 4px; }
.da-msg { max-width: 92%; }
.da-msg.user { align-self: flex-end; text-align: right; }
.da-msg.assistant { align-self: flex-start; }
.da-msg__role { font-size: 11px; color: var(--c-text-3); margin-bottom: 2px; }
.da-msg__c { white-space: pre-wrap; word-break: break-word; margin: 0; padding: 8px 10px; border-radius: 8px; font-size: 12.5px; line-height: 1.55; text-align: left; background: var(--c-surface-3, #f1f5f9); }
.da-msg.user .da-msg__c { background: var(--brand-emerald, #10b981); color: #fff; }
.da-typing { color: var(--c-text-3); font-size: 12px; padding: 8px 10px; }
.da-chatin { display: flex; gap: 6px; margin-top: 8px; align-items: flex-end; }
.da-chatin .el-button { flex: none; }

@media (max-width: 1200px) { .da-body { grid-template-columns: 240px 1fr; } .da-right { grid-column: 1 / -1; border-left: none; border-top: 1px solid var(--c-border); } }
</style>
