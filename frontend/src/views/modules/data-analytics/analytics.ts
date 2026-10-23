/* =========================================================================
 * analytics.ts — 数据分析引擎
 * 移植并增强 DataScope Analytics 的纯前端计算层：
 *   CSV / Excel 解析、类型推断、聚合、描述统计、相关性矩阵、KDE / 直方图、
 *   趋势分析，以及「资助数据」识别与数据画像构建。
 * 本文件为纯 TS（无 Vue 依赖），可在任意视图中复用。
 * ========================================================================= */

export type FieldType = 'number' | 'date' | 'category'

export interface FieldInfo {
  name: string
  type: FieldType
  role: 'measure' | 'dimension'
  missing: number
  distinct: number
  min: number | null
  max: number | null
  sample: string[]
}

export interface Dataset {
  headers: string[]
  rows: Record<string, any>[]
}

export interface StatsResult {
  field: string
  count: number
  missing: number
  mean: number
  std: number
  min: number
  q1: number
  median: number
  q3: number
  max: number
  sum: number
}

/* ----------------------------- 数值 / 日期 ----------------------------- */
export function toNumber(v: any): number {
  if (v === null || v === undefined) return NaN
  const s = String(v).trim().replace(/,/g, '').replace(/[%$¥￥]/g, '')
  if (s === '') return NaN
  return Number(s)
}

const DATE_RE =
  /^(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}|\d{4}\d{2}\d{2})$/

export function parseDate(v: any): number | null {
  if (v == null || v === '') return null
  const s = String(v).trim()
  if (!DATE_RE.test(s)) return null
  const t = Date.parse(s.replace(/-/g, '/'))
  return isNaN(t) ? null : t
}

/* ----------------------------- CSV 解析 ----------------------------- */
export function parseCSV(text: string): Dataset {
  text = text.replace(/^\uFEFF/, '') // 去 BOM
  const delim = text.indexOf('\t') !== -1 && text.indexOf(',') === -1 ? '\t' : ','
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false
  let i = 0
  const n = text.length
  while (i < n) {
    const c = text[i]
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"'
          i += 2
          continue
        }
        inQuotes = false
        i++
        continue
      }
      field += c
      i++
      continue
    }
    if (c === '"') {
      inQuotes = true
      i++
      continue
    }
    if (c === delim) {
      row.push(field)
      field = ''
      i++
      continue
    }
    if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++
      row.push(field)
      field = ''
      rows.push(row)
      row = []
      i++
      continue
    }
    field += c
    i++
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field)
    rows.push(row)
  }
  while (rows.length && rows[rows.length - 1].every((x) => x.trim() === '')) rows.pop()
  if (!rows.length) return { headers: [], rows: [] }
  const headers = rows[0].map((h, idx) => h.trim() || 'col' + (idx + 1))
  const data: Record<string, any>[] = []
  for (let r = 1; r < rows.length; r++) {
    const cells = rows[r]
    if (cells.length === 1 && cells[0].trim() === '') continue
    const obj: Record<string, any> = {}
    for (let c = 0; c < headers.length; c++) obj[headers[c]] = cells[c] !== undefined ? cells[c] : ''
    data.push(obj)
  }
  return { headers, rows: data }
}

/* ----------------------------- Excel 解析 ----------------------------- */
export async function parseExcel(arrayBuffer: ArrayBuffer): Promise<Dataset> {
  const XLSX = await import('xlsx')
  const wb = XLSX.read(arrayBuffer, { type: 'array' })
  const ws = wb.Sheets[wb.SheetNames[0]]
  const json: Record<string, any>[] = XLSX.utils.sheet_to_json(ws, { defval: '', raw: false })
  if (!json.length) return { headers: [], rows: [] }
  const headers = Object.keys(json[0])
  return { headers, rows: json }
}

/* --------------------------- 类型推断 --------------------------- */
export function inferFields(dataset: Dataset): FieldInfo[] {
  const { headers, rows } = dataset
  const sampleSize = Math.min(rows.length, 200)
  return headers.map((name) => {
    let num = 0
    let date = 0
    let nonempty = 0
    let miss = 0
    const sampleVals: string[] = []
    for (let i = 0; i < sampleSize; i++) {
      const raw = rows[i][name]
      const s = raw === null || raw === undefined ? '' : String(raw).trim()
      if (s === '') {
        miss++
        continue
      }
      nonempty++
      if (sampleVals.length < 12) sampleVals.push(s)
      if (!isNaN(toNumber(s))) num++
      else if (parseDate(s) !== null) date++
    }
    let type: FieldType
    if (nonempty > 0 && num === nonempty) type = 'number'
    else if (nonempty > 0 && date === nonempty) type = 'date'
    else type = 'category'
    const uniq = new Set(rows.slice(0, sampleSize).map((r) => r[name]))
    const role = type === 'number' ? 'measure' : 'dimension'
    let min: number | null = null
    let max: number | null = null
    if (type === 'number') {
      let mn = Infinity
      let mx = -Infinity
      for (const r of rows) {
        const v = toNumber(r[name])
        if (!isNaN(v)) {
          if (v < mn) mn = v
          if (v > mx) mx = v
        }
      }
      if (mn !== Infinity) {
        min = mn
        max = mx
      }
    }
    return { name, type, role, missing: miss, distinct: uniq.size, min, max, sample: sampleVals }
  })
}

export function isNumField(fields: FieldInfo[], f: string): boolean {
  const fd = fields.find((x) => x.name === f)
  return !!fd && fd.type === 'number'
}

/* --------------------------- 聚合 / 统计 --------------------------- */
export function quantile(sortedArr: number[], q: number): number {
  const a = sortedArr
  if (!a.length) return NaN
  const pos = (a.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (a[base + 1] !== undefined) return a[base] + rest * (a[base + 1] - a[base])
  return a[base]
}

export function aggFn(mode: string) {
  return function (vals: number[]): number {
    const arr = vals.filter((v) => !isNaN(v))
    if (!arr.length) return 0
    switch (mode) {
      case 'sum':
        return arr.reduce((a, b) => a + b, 0)
      case 'avg':
        return arr.reduce((a, b) => a + b, 0) / arr.length
      case 'count':
        return vals.length
      case 'countDistinct':
        return new Set(vals.map((v) => String(v))).size
      case 'max':
        return Math.max.apply(null, arr)
      case 'min':
        return Math.min.apply(null, arr)
      case 'median':
        return quantile(arr.slice().sort((a, b) => a - b), 0.5)
      default:
        return arr.reduce((a, b) => a + b, 0)
    }
  }
}

export function aggregate(
  rows: Record<string, any>[],
  dims: string[],
  measure: string,
  mode: string
): { key: string; dims: any[]; value: number }[] {
  const fn = aggFn(mode)
  const map = new Map<string, { key: string; dims: any[]; vals: number[] }>()
  for (const r of rows) {
    const key = dims.map((d) => String(r[d] == null ? '' : r[d])).join('')
    if (!map.has(key)) map.set(key, { key, dims: dims.map((d) => r[d]), vals: [] })
    const m = toNumber(r[measure])
    map.get(key)!.vals.push(isNaN(m) ? NaN : m)
  }
  const out: { key: string; dims: any[]; value: number }[] = []
  map.forEach((v) => out.push({ key: v.key, dims: v.dims, value: fn(v.vals) }))
  return out
}

export function stats(rows: Record<string, any>[], field: string): StatsResult | null {
  const vals = rows
    .map((r) => toNumber(r[field]))
    .filter((v) => !isNaN(v))
    .sort((a, b) => a - b)
  const n = vals.length
  if (!n) return null
  const mean = vals.reduce((a, b) => a + b, 0) / n
  const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / n
  const std = Math.sqrt(variance)
  const missing = rows.length - n
  return {
    field,
    count: n,
    missing,
    mean,
    std,
    min: vals[0],
    q1: quantile(vals, 0.25),
    median: quantile(vals, 0.5),
    q3: quantile(vals, 0.75),
    max: vals[n - 1],
    sum: vals.reduce((a, b) => a + b, 0),
  }
}

/* --------------------------- 相关性矩阵 --------------------------- */
export function correlationMatrix(rows: Record<string, any>[], numericFields: string[]): {
  fields: string[]
  matrix: number[][]
} {
  const cols = numericFields.filter((f) => rows.some((r) => !isNaN(toNumber(r[f]))))
  const data: number[][] = cols.map((f) => rows.map((r) => toNumber(r[f])).map((v) => (isNaN(v) ? 0 : v)))
  const k = cols.length
  const matrix: number[][] = Array.from({ length: k }, () => new Array(k).fill(0))
  for (let a = 0; a < k; a++) {
    for (let b = 0; b < k; b++) {
      if (a === b) {
        matrix[a][b] = 1
        continue
      }
      const xa = data[a]
      const xb = data[b]
      const n = xa.length
      const ma = xa.reduce((s, v) => s + v, 0) / n
      const mb = xb.reduce((s, v) => s + v, 0) / n
      let sxy = 0
      let sxx = 0
      let syy = 0
      for (let i = 0; i < n; i++) {
        sxy += (xa[i] - ma) * (xb[i] - mb)
        sxx += (xa[i] - ma) ** 2
        syy += (xb[i] - mb) ** 2
      }
      matrix[a][b] = sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0
    }
  }
  return { fields: cols, matrix }
}

/* --------------------------- KDE / 直方图 --------------------------- */
function silverman(values: number[]): number {
  const n = values.length
  if (n < 2) return 1
  const mean = values.reduce((a, b) => a + b, 0) / n
  const std = Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / n)
  const sorted = values.slice().sort((a, b) => a - b)
  const q1 = quantile(sorted, 0.25)
  const q3 = quantile(sorted, 0.75)
  const iqr = q3 - q1
  const sigma = Math.min(std, iqr / 1.34) || std || 1
  return 1.06 * sigma * Math.pow(n, -1 / 5) || 1
}

export function kde(values: number[], grid: number[], bandwidth?: number): number[] {
  const n = values.length
  const bw = bandwidth || silverman(values)
  const norm = 1 / (n * bw * Math.sqrt(2 * Math.PI))
  return grid.map((x) => {
    let sum = 0
    for (const v of values) {
      const u = (x - v) / bw
      sum += Math.exp(-0.5 * u * u)
    }
    return norm * sum
  })
}

export function histogram(values: number[], bins: number): { center: number; count: number }[] {
  if (!values.length) return []
  const min = Math.min.apply(null, values)
  const max = Math.max.apply(null, values)
  const span = max - min || 1
  const width = span / bins
  const counts = new Array(bins).fill(0)
  for (const v of values) {
    let idx = Math.floor((v - min) / width)
    if (idx >= bins) idx = bins - 1
    if (idx < 0) idx = 0
    counts[idx]++
  }
  return counts.map((c, i) => ({ center: min + (i + 0.5) * width, count: c }))
}

/* --------------------------- 趋势分析 --------------------------- */
export function trendAnalysis(
  rows: Record<string, any>[],
  dateField: string,
  valueField: string
): { points: { period: string; value: number }[]; slope: number; direction: 'up' | 'down' | 'flat'; r2: number } | null {
  if (!dateField || !valueField) return null
  const byPeriod = new Map<string, number[]>()
  for (const r of rows) {
    const d = parseDate(r[dateField])
    if (d == null) continue
    const dt = new Date(d)
    const period = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`
    if (!byPeriod.has(period)) byPeriod.set(period, [])
    const v = toNumber(r[valueField])
    if (!isNaN(v)) byPeriod.get(period)!.push(v)
  }
  const periods = [...byPeriod.keys()].sort()
  if (periods.length < 2) return null
  const points = periods.map((p) => {
    const arr = byPeriod.get(p)!
    return { period: p, value: arr.reduce((a, b) => a + b, 0) / arr.length }
  })
  const xs = points.map((_, i) => i)
  const ys = points.map((p) => p.value)
  const n = xs.length
  const mx = xs.reduce((a, b) => a + b, 0) / n
  const my = ys.reduce((a, b) => a + b, 0) / n
  let sxy = 0
  let sxx = 0
  let syy = 0
  for (let i = 0; i < n; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my)
    sxx += (xs[i] - mx) ** 2
    syy += (ys[i] - my) ** 2
  }
  const slope = sxx ? sxy / sxx : 0
  const r2 = sxx && syy ? (sxy * sxy) / (sxx * syy) : 0
  const direction: 'up' | 'down' | 'flat' = slope > 1e-9 ? 'up' : slope < -1e-9 ? 'down' : 'flat'
  return { points, slope, direction, r2 }
}

/* --------------------------- 资助数据识别 --------------------------- */
const FUNDING_KEYWORDS: Record<string, string[]> = {
  org: ['机构', '单位', '承担单位', '依托单位', 'organization', 'institution', 'org'],
  amount: ['经费', '金额', '资助额', '拨款', '预算', 'amount', 'fund', 'budget', 'grant_amount'],
  project: ['项目', '课题', 'project', 'title', '课题名称'],
  year: ['年份', '年度', '立项年', 'year', '批准年'],
  region: ['地区', '省份', '省市', 'region', 'province', 'area'],
  category: ['类别', '类型', '专项', 'category', 'type', 'field', '学科', '领域', 'discipline'],
  status: ['状态', '进度', 'status', 'phase'],
  pi: ['负责人', '主持', 'pi', 'principal'],
}

export interface FundingSchema {
  isFunding: boolean
  amount?: string
  org?: string
  project?: string
  year?: string
  region?: string
  category?: string
  status?: string
  pi?: string
  score: number
}

function matchKey(field: string, keys: string[]): boolean {
  const f = field.toLowerCase()
  return keys.some((k) => f.includes(k))
}

export function detectFundingSchema(fields: FieldInfo[]): FundingSchema {
  const names = fields.map((f) => f.name)
  const find = (keys: string[]): string | undefined => names.find((n) => matchKey(n, keys))
  const amount = find(FUNDING_KEYWORDS.amount)
  const org = find(FUNDING_KEYWORDS.org)
  const project = find(FUNDING_KEYWORDS.project)
  const year = find(FUNDING_KEYWORDS.year)
  const region = find(FUNDING_KEYWORDS.region)
  const category = find(FUNDING_KEYWORDS.category)
  const status = find(FUNDING_KEYWORDS.status)
  const pi = find(FUNDING_KEYWORDS.pi)
  let score = 0
  if (amount) score += 2
  if (org) score += 1
  if (project) score += 1
  if (year) score += 1
  if (region) score += 1
  if (category) score += 1
  if (status) score += 0.5
  if (pi) score += 0.5
  const isFunding = score >= 3 && !!amount
  return { isFunding, amount, org, project, year, region, category, status, pi, score }
}

/* --------------------------- 数据画像（供 AI） --------------------------- */
export function buildProfile(
  dataset: Dataset,
  fields: FieldInfo[],
  funding?: FundingSchema
): string {
  const nums = fields.filter((f) => f.type === 'number')
  const cats = fields.filter((f) => f.type === 'category')
  const dates = fields.filter((f) => f.type === 'date')
  const lines: string[] = []
  lines.push(`数据集规模：${dataset.rows.length} 行 × ${dataset.headers.length} 列。`)
  lines.push(
    `字段：${fields
      .map((f) => `${f.name}(${f.type === 'number' ? '数值' : f.type === 'date' ? '日期' : '分类'}, 缺${f.missing}, 唯一${f.distinct})`)
      .join('；')}。`
  )
  if (nums.length) {
    lines.push('数值字段描述统计：')
    nums.forEach((f) => {
      const s = stats(dataset.rows, f.name)
      if (s) {
        lines.push(
          `- ${f.name}：均值 ${s.mean.toFixed(2)}，标准差 ${s.std.toFixed(2)}，最小 ${s.min.toFixed(
            2
          )}，中位 ${s.median.toFixed(2)}，最大 ${s.max.toFixed(2)}，合计 ${s.sum.toFixed(2)}，缺失 ${s.missing}。`
        )
      }
    })
  }
  if (nums.length >= 2) {
    const cm = correlationMatrix(dataset.rows, nums.map((f) => f.name))
    const strong: string[] = []
    for (let a = 0; a < cm.fields.length; a++) {
      for (let b = a + 1; b < cm.fields.length; b++) {
        const r = cm.matrix[a][b]
        if (Math.abs(r) >= 0.5) strong.push(`${cm.fields[a]} ~ ${cm.fields[b]} (r=${r.toFixed(2)})`)
      }
    }
    lines.push(strong.length ? `强相关性（|r|≥0.5）：${strong.join('；')}。` : '未检出强相关（|r|≥0.5）的数值字段对。')
  }
  if (funding && funding.isFunding) {
    lines.push('该数据集被识别为「资助 / 科研经费」数据。')
    if (funding.amount) {
      const total = dataset.rows.reduce((s, r) => s + (toNumber(r[funding.amount!]) || 0), 0)
      const byOrg = aggregate(dataset.rows, funding.org ? [funding.org] : [], funding.amount, 'sum')
      byOrg.sort((a, b) => b.value - a.value)
      lines.push(`资助总额（${funding.amount}）合计约 ${total.toFixed(0)}。`)
      if (byOrg.length) lines.push(`主要${funding.org || '机构'}资助排名：${byOrg.slice(0, 5).map((x) => `${x.dims[0]}=${x.value.toFixed(0)}`).join('，')}。`)
    }
    if (funding.year) {
      const byYear = aggregate(dataset.rows, [funding.year], funding.amount || funding.project || funding.org || '', 'count')
      byYear.sort((a, b) => String(a.dims[0]).localeCompare(String(b.dims[0])))
      lines.push(`各年度记录数：${byYear.map((x) => `${x.dims[0]}:${x.value}`).join('，')}。`)
    }
  }
  // 样本数据（前 3 行）
  const sample = dataset.rows.slice(0, 3).map((r) => JSON.stringify(r)).join('\n')
  lines.push(`样本数据（前 3 行）：\n${sample}`)
  return lines.join('\n')
}

/* --------------------------- 示例数据集 --------------------------- */
function mulberry32(a: number) {
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const IRIS_CSV =
  'sepal_length,sepal_width,petal_length,petal_width,species\n' +
  [
    [5.1, 3.5, 1.4, 0.2, 'setosa'], [4.9, 3.0, 1.4, 0.2, 'setosa'], [4.7, 3.2, 1.3, 0.2, 'setosa'],
    [4.6, 3.1, 1.5, 0.2, 'setosa'], [5.0, 3.6, 1.4, 0.2, 'setosa'], [5.4, 3.9, 1.7, 0.4, 'setosa'],
    [4.6, 3.4, 1.4, 0.3, 'setosa'], [5.0, 3.4, 1.5, 0.2, 'setosa'], [4.4, 2.9, 1.4, 0.2, 'setosa'],
    [4.9, 3.1, 1.5, 0.1, 'setosa'], [5.4, 3.7, 1.5, 0.2, 'setosa'], [4.8, 3.4, 1.6, 0.2, 'setosa'],
    [4.8, 3.0, 1.4, 0.1, 'setosa'], [4.3, 3.0, 1.1, 0.1, 'setosa'], [5.8, 4.0, 1.2, 0.2, 'setosa'],
    [5.7, 4.4, 1.5, 0.4, 'setosa'], [5.4, 3.9, 1.3, 0.4, 'setosa'], [5.1, 3.5, 1.4, 0.3, 'setosa'],
    [5.7, 3.8, 1.7, 0.3, 'setosa'], [5.1, 3.8, 1.5, 0.3, 'setosa'], [5.4, 3.4, 1.7, 0.2, 'setosa'],
    [5.1, 3.7, 1.5, 0.4, 'setosa'], [4.6, 3.6, 1.0, 0.2, 'setosa'], [5.1, 3.3, 1.7, 0.5, 'setosa'],
    [4.8, 3.4, 1.9, 0.2, 'setosa'], [5.0, 3.0, 1.6, 0.2, 'setosa'], [5.0, 3.4, 1.6, 0.4, 'setosa'],
    [5.2, 3.4, 1.5, 0.2, 'setosa'], [5.2, 3.5, 1.5, 0.2, 'setosa'], [4.7, 3.2, 1.6, 0.2, 'setosa'],
    [4.8, 3.1, 1.6, 0.2, 'setosa'], [5.4, 3.4, 1.5, 0.4, 'setosa'], [5.2, 4.1, 1.5, 0.1, 'setosa'],
    [5.5, 4.2, 1.4, 0.2, 'setosa'], [4.9, 3.1, 1.5, 0.1, 'setosa'], [5.0, 3.2, 1.2, 0.2, 'setosa'],
    [5.5, 3.5, 1.3, 0.2, 'setosa'], [4.9, 3.1, 1.5, 0.1, 'setosa'], [4.4, 3.0, 1.3, 0.2, 'setosa'],
    [5.1, 3.4, 1.5, 0.2, 'setosa'], [5.0, 3.5, 1.3, 0.3, 'setosa'], [4.5, 2.3, 1.3, 0.3, 'setosa'],
    [4.4, 3.2, 1.3, 0.2, 'setosa'], [5.0, 3.5, 1.6, 0.6, 'setosa'], [5.1, 3.8, 1.9, 0.4, 'setosa'],
    [4.8, 3.0, 1.4, 0.3, 'setosa'], [5.1, 3.8, 1.6, 0.2, 'setosa'], [4.6, 3.2, 1.4, 0.2, 'setosa'],
    [5.3, 3.7, 1.5, 0.2, 'setosa'], [5.0, 3.3, 1.4, 0.2, 'setosa'],
    [7.0, 3.2, 4.7, 1.4, 'versicolor'], [6.4, 3.2, 4.5, 1.5, 'versicolor'], [6.9, 3.1, 4.9, 1.5, 'versicolor'],
    [5.5, 2.3, 4.0, 1.3, 'versicolor'], [6.5, 2.8, 4.6, 1.5, 'versicolor'], [5.7, 2.8, 4.5, 1.3, 'versicolor'],
    [6.3, 3.3, 4.7, 1.6, 'versicolor'], [4.9, 2.4, 3.3, 1.0, 'versicolor'], [6.6, 2.9, 4.6, 1.3, 'versicolor'],
    [5.2, 2.7, 3.9, 1.4, 'versicolor'], [5.0, 2.0, 3.5, 1.0, 'versicolor'], [5.9, 3.0, 4.2, 1.5, 'versicolor'],
    [6.0, 2.9, 4.5, 1.5, 'versicolor'], [5.6, 2.9, 3.9, 1.1, 'versicolor'], [5.7, 3.3, 5.7, 2.5, 'versicolor'],
    [5.7, 2.6, 3.5, 1.0, 'versicolor'], [5.5, 2.4, 3.8, 1.1, 'versicolor'], [5.5, 2.4, 3.7, 1.0, 'versicolor'],
    [5.8, 2.7, 3.9, 1.2, 'versicolor'], [6.0, 2.7, 5.1, 1.6, 'versicolor'], [5.4, 3.0, 4.5, 1.5, 'versicolor'],
    [6.0, 3.4, 4.5, 1.6, 'versicolor'], [6.7, 3.1, 4.7, 1.5, 'versicolor'], [6.3, 2.3, 4.4, 1.3, 'versicolor'],
    [5.6, 3.0, 4.1, 1.3, 'versicolor'], [5.5, 2.5, 4.0, 1.3, 'versicolor'], [5.5, 2.6, 4.4, 1.2, 'versicolor'],
    [6.1, 3.0, 4.6, 1.4, 'versicolor'], [5.8, 2.6, 4.0, 1.2, 'versicolor'], [5.0, 2.3, 3.3, 1.0, 'versicolor'],
    [5.6, 2.7, 4.2, 1.3, 'versicolor'], [5.7, 3.0, 4.2, 1.2, 'versicolor'], [5.7, 2.9, 4.2, 1.3, 'versicolor'],
    [6.2, 2.9, 4.3, 1.3, 'versicolor'], [5.1, 2.5, 3.0, 1.1, 'versicolor'], [5.7, 2.8, 4.1, 1.3, 'versicolor'],
    [6.3, 3.3, 6.0, 2.5, 'versicolor'], [5.8, 2.7, 5.1, 1.9, 'versicolor'], [7.1, 3.0, 5.9, 2.1, 'versicolor'],
    [6.3, 2.9, 5.6, 1.9, 'versicolor'], [6.5, 3.0, 5.8, 2.2, 'versicolor'], [7.6, 3.0, 6.6, 2.1, 'versicolor'],
    [4.9, 2.5, 4.5, 1.7, 'versicolor'], [7.3, 2.9, 6.3, 1.8, 'versicolor'], [6.7, 2.5, 5.8, 1.8, 'versicolor'],
    [7.2, 3.6, 6.1, 2.5, 'versicolor'], [6.5, 3.2, 5.1, 2.0, 'versicolor'], [6.4, 2.7, 5.3, 1.9, 'versicolor'],
    [6.8, 3.0, 5.5, 2.1, 'versicolor'], [5.7, 2.5, 5.0, 2.0, 'versicolor'], [5.8, 2.8, 5.1, 2.4, 'versicolor'],
    [6.4, 3.2, 5.3, 2.3, 'versicolor'], [6.5, 3.0, 5.5, 1.8, 'versicolor'], [7.7, 3.8, 6.7, 2.2, 'versicolor'],
    [6.3, 3.3, 6.0, 2.5, 'virginica'], [5.8, 2.7, 5.1, 1.9, 'virginica'], [7.1, 3.0, 5.9, 2.1, 'virginica'],
    [6.3, 2.9, 5.6, 1.9, 'virginica'], [6.5, 3.0, 5.8, 2.2, 'virginica'], [7.6, 3.0, 6.6, 2.1, 'virginica'],
    [4.9, 2.5, 4.5, 1.7, 'virginica'], [7.3, 2.9, 6.3, 1.8, 'virginica'], [6.7, 2.5, 5.8, 1.8, 'virginica'],
    [7.2, 3.6, 6.1, 2.5, 'virginica'], [6.5, 3.2, 5.1, 2.0, 'virginica'], [6.4, 2.7, 5.3, 1.9, 'virginica'],
    [6.8, 3.0, 5.5, 2.1, 'virginica'], [5.7, 2.5, 5.0, 2.0, 'virginica'], [5.8, 2.8, 5.1, 2.4, 'virginica'],
    [6.4, 3.2, 5.3, 2.3, 'virginica'], [6.5, 3.0, 5.5, 1.8, 'virginica'], [7.7, 3.8, 6.7, 2.2, 'virginica'],
    [7.7, 2.6, 6.9, 2.3, 'virginica'], [6.0, 2.2, 5.0, 1.5, 'virginica'], [6.9, 3.2, 5.7, 2.3, 'virginica'],
    [5.6, 2.8, 4.9, 2.0, 'virginica'], [7.7, 2.8, 6.7, 2.0, 'virginica'], [6.3, 2.7, 4.9, 1.8, 'virginica'],
    [6.7, 3.3, 5.7, 2.1, 'virginica'], [7.2, 3.2, 6.0, 1.8, 'virginica'], [6.2, 2.8, 4.8, 1.8, 'virginica'],
    [6.1, 3.0, 4.9, 1.8, 'virginica'], [6.4, 2.8, 5.6, 2.1, 'virginica'], [7.2, 3.0, 5.8, 1.6, 'virginica'],
    [7.4, 2.8, 6.1, 1.9, 'virginica'], [7.9, 3.8, 6.4, 2.0, 'virginica'], [6.4, 2.8, 5.6, 2.2, 'virginica'],
    [6.3, 2.8, 5.1, 1.5, 'virginica'], [6.1, 2.6, 5.6, 1.4, 'virginica'], [7.7, 3.0, 6.1, 2.3, 'virginica'],
    [6.3, 3.4, 5.6, 2.4, 'virginica'], [6.4, 3.1, 5.5, 1.8, 'virginica'], [6.0, 3.0, 4.8, 1.8, 'virginica'],
    [6.9, 3.1, 5.4, 2.1, 'virginica'], [6.7, 3.1, 5.6, 2.4, 'virginica'], [6.9, 3.1, 5.1, 2.3, 'virginica'],
    [5.8, 2.7, 5.1, 1.9, 'virginica'], [6.8, 3.2, 5.9, 2.3, 'virginica'], [6.7, 3.3, 5.7, 2.5, 'virginica'],
    [6.7, 3.0, 5.2, 2.3, 'virginica'], [6.3, 2.5, 5.0, 1.9, 'virginica'], [6.5, 3.0, 5.2, 2.0, 'virginica'],
    [6.2, 3.4, 5.4, 2.3, 'virginica'], [5.9, 3.0, 5.1, 1.8, 'virginica'],
  ]
    .map((r) => r.join(','))
    .join('\n')

const CARS_CSV =
  'model,mpg,cylinders,displacement,horsepower,weight,acceleration,year,origin\n' +
  [
    ['chevrolet chevelle malibu', 18, 8, 307, 130, 3504, 12, 1970, 'usa'],
    ['buick skylark 320', 15, 8, 350, 165, 3693, 11.5, 1970, 'usa'],
    ['datsun pl510', 27, 4, 97, 88, 2130, 14.5, 1970, 'japan'],
    ['volkswagen 1131 deluxe', 26, 4, 97, 46, 1835, 20.5, 1970, 'europe'],
    ['ford torino', 17, 8, 302, 140, 3449, 10.5, 1970, 'usa'],
    ['ford galaxie 500', 15, 8, 429, 198, 4341, 10, 1970, 'usa'],
    ['chevrolet impala', 14.5, 8, 454, 220, 4354, 9, 1970, 'usa'],
    ['plymouth fury iii', 15.5, 8, 318, 150, 4096, 11, 1970, 'usa'],
    ['pontiac catalina', 16, 8, 400, 150, 4425, 10.5, 1970, 'usa'],
    ['amc rebel sst', 16, 8, 304, 150, 3892, 12, 1970, 'usa'],
    ['toyota corona', 24, 4, 113, 95, 2278, 15.5, 1970, 'japan'],
    ['dodge dart custom', 22.5, 6, 198, 100, 2962, 15, 1970, 'usa'],
    ['mazda rx2 coupe', 22, 4, 120, 97, 2303, 14.5, 1973, 'japan'],
    ['amc matador', 17, 8, 304, 150, 4130, 12, 1973, 'usa'],
    ['chevrolet monte carlo', 16, 8, 400, 150, 4464, 11.5, 1973, 'usa'],
    ['buick century 350', 14.5, 8, 350, 175, 3988, 11, 1973, 'usa'],
    ['plymouth卫星', 20, 6, 225, 100, 3283, 15, 1973, 'usa'],
    ['ford gran torino', 18, 8, 302, 140, 3449, 10.5, 1973, 'usa'],
    ['dodge coronet custom', 16, 8, 318, 150, 4082, 11, 1973, 'usa'],
    ['mercedes 280s', 16, 8, 240, 120, 3765, 13, 1973, 'europe'],
    ['volvo 145e', 21, 4, 121, 112, 2868, 15.5, 1973, 'europe'],
    ['saab 99e', 23, 4, 121, 110, 2675, 16, 1973, 'europe'],
    ['toyota mark ii', 23, 4, 140, 108, 2960, 16.5, 1973, 'japan'],
    ['datsun 710', 24, 4, 120, 97, 2503, 18, 1973, 'japan'],
    ['honda civic', 32, 4, 71, 65, 1836, 19, 1976, 'japan'],
    ['fiat 128', 31, 4, 79, 67, 1962, 19.5, 1976, 'europe'],
    ['opel manta', 25, 4, 98, 78, 2219, 16.5, 1976, 'europe'],
    ['audi 100ls', 25, 4, 121, 71, 2700, 16, 1976, 'europe'],
    ['peugeot 504', 20, 4, 130, 84, 2765, 15.5, 1976, 'europe'],
    ['volkswagen dasher', 30, 4, 97, 68, 2125, 18, 1976, 'europe'],
    ['bmw 2002', 27, 4, 121, 110, 2430, 16, 1976, 'europe'],
    ['maxda glc', 34, 4, 105, 70, 2201, 16.5, 1982, 'japan'],
  ]
    .map((r) => r.join(','))
    .join('\n')

function salesSampleCSV(): string {
  const regions = ['华东', '华北', '华南', '西部']
  const cats = ['电子', '服饰', '食品', '家居']
  const months = ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05']
  const rand = mulberry32(20240901)
  const lines = ['region,category,month,revenue,units,cost']
  for (const rg of regions)
    for (const ct of cats)
      for (const mo of months) {
        const base = 5000 + rand() * 15000
        const rev = Math.round(base * (0.8 + rand() * 0.5))
        const u = Math.round(rev / (20 + rand() * 30))
        const c = Math.round(rev * (0.5 + rand() * 0.2))
        lines.push([rg, ct, mo, rev, u, c].join(','))
      }
  return lines.join('\n')
}

function fundingSampleCSV(): string {
  const orgs = ['国家自然科学基金委', '科技部', '教育部', '中科院', '省级科技厅']
  const regions = ['北京', '上海', '江苏', '广东', '浙江', '湖北', '陕西', '四川']
  const cats = ['面上项目', '重点项目', '青年基金', '重大专项', '国际合作']
  const disciplines = ['信息科学', '生命科学', '材料科学', '数理科学', '医学科学', '地球科学']
  const statuses = ['在研', '结题', '待启动']
  const rand = mulberry32(20260601)
  const lines = ['项目类别,项目名称,承担单位,资助机构,经费_万元,立项年份,地区,学科领域,负责人,状态']
  const projNames = ['面向边缘计算的高可靠推理系统', '新型钙钛矿光伏材料', '脑机接口信号解码', '城市洪涝预报模型', '工业软件内核', '靶向药物递送', '量子通信组网', 'AI 辅助诊断', '新能源电池管理', '高精度传感网络']
  for (let i = 0; i < 64; i++) {
    const cat = cats[Math.floor(rand() * cats.length)]
    const org = orgs[Math.floor(rand() * orgs.length)]
    const region = regions[Math.floor(rand() * regions.length)]
    const discipline = disciplines[Math.floor(rand() * disciplines.length)]
    const amount = Math.round((20 + rand() * 480) * 10) / 10
    const year = 2019 + Math.floor(rand() * 7)
    const status = statuses[Math.floor(rand() * statuses.length)]
    const pi = 'PI-' + (1000 + Math.floor(rand() * 9000))
    lines.push([cat, projNames[i % projNames.length] + '（' + (i + 1) + '）', org + '实验室', org, amount, year, region, discipline, pi, status].join(','))
  }
  return lines.join('\n')
}

export interface SampleDef {
  key: string
  label: string
  csv: string
  note?: string
}

export const SAMPLES: SampleDef[] = [
  { key: 'iris', label: '鸢尾花 Iris（150 行）', csv: IRIS_CSV },
  { key: 'cars', label: '汽车 MPG（32 行）', csv: CARS_CSV },
  { key: 'sales', label: '零售销售（区域×品类×月份）', csv: salesSampleCSV() },
  { key: 'funding', label: '科研资助数据（64 行 · 含经费/机构/年份）', csv: fundingSampleCSV(), note: '资助分析示例' },
]

export function loadSample(key: string): Dataset {
  const s = SAMPLES.find((x) => x.key === key)
  if (!s) return { headers: [], rows: [] }
  return parseCSV(s.csv)
}

/* ------------------------------ 通用工具 ------------------------------ */
export function fmt(v: number): string {
  if (v == null || isNaN(v)) return '—'
  if (Math.abs(v) >= 1e6 || (Math.abs(v) < 1e-3 && v !== 0)) return v.toExponential(2)
  return String(Math.round(v * 1000) / 1000)
}

export function escapeHtml(s: any): string {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string)
  )
}
