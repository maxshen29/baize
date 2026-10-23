import http from './http'
import { getAccessToken } from '@/utils/auth'

export interface Persona {
  id: number
  name: string
  role: string
  traits: string
  stance: 'supportive' | 'opposing' | 'neutral' | 'observer'
  background: string
  voice: string
}

export interface SimAction {
  round: number
  name: string
  role: string
  stance: string
  content: string
}

export interface BuildWorldPayload {
  seed_text: string
  question: string
  num_agents?: number
  model?: string | null
}

export interface BuildWorldData {
  world: string
  setting: string
  personas: Persona[]
}

// 一次性 LLM 调用（构建世界 / 抽取图谱）耗时较长，单独放大超时，避免被默认 15s 掐断
const LONG_TIMEOUT = { timeout: 180000 }

export async function buildWorld(payload: BuildWorldPayload) {
  return http.post('/modules/social_sim/build-world', payload, LONG_TIMEOUT)
}

export interface GraphNode {
  id: string
  name: string
  type: string
  description?: string
  color?: string
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
  description?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface ExtractGraphPayload {
  seed_text: string
  question: string
  model?: string | null
}

export async function extractGraph(payload: ExtractGraphPayload) {
  return http.post('/modules/social_sim/extract-graph', payload, LONG_TIMEOUT)
}

export interface SimulatePayload {
  world: string
  setting: string
  personas: Persona[]
  question: string
  rounds: number
  god_events: Record<number, string>
  model?: string | null
}

/** 推演事件流：每个事件为结构化 JSON（type 字段区分）。 */
export async function streamSimulate(
  payload: SimulatePayload,
  handlers: { onEvent: (ev: any) => void; signal?: AbortSignal },
): Promise<void> {
  const token = getAccessToken()
  const resp = await fetch('/api/v1/modules/social_sim/simulate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal: handlers.signal,
  })
  const ct = resp.headers.get('Content-Type') || ''
  if (ct.includes('application/json')) {
    const json = await resp.json().catch(() => ({}))
    throw new Error(json?.message || json?.detail || '推演失败')
  }
  if (!resp.ok || !resp.body) {
    const text = await resp.text().catch(() => '')
    throw new Error(text || `请求失败 (${resp.status})`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() || ''
    for (const line of lines) {
      const s = line.trim()
      if (!s.startsWith('data:')) continue
      const p = s.slice(5).trim()
      if (p === '[DONE]') return
      try {
        handlers.onEvent(JSON.parse(p))
      } catch {
        /* 心跳 / 非 JSON 行忽略 */
      }
    }
  }
}

export interface ReportPayload {
  world: string
  setting: string
  personas: Persona[]
  question: string
  transcript: SimAction[]
  rounds?: number
  model?: string | null
}

export interface ChatPayload {
  world: string
  setting: string
  personas: Persona[]
  question: string
  transcript: SimAction[]
  report_text: string
  messages: { role: string; content: string }[]
  focus?: string
  model?: string | null
}

/** OpenAI 风格 SSE 文本流（report / chat 共用）。 */
async function streamText(
  url: string,
  payload: any,
  handlers: { onDelta: (text: string) => void; signal?: AbortSignal },
): Promise<void> {
  const token = getAccessToken()
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal: handlers.signal,
  })
  const ct = resp.headers.get('Content-Type') || ''
  if (ct.includes('application/json')) {
    const json = await resp.json().catch(() => ({}))
    throw new Error(json?.message || json?.detail || '请求失败')
  }
  if (!resp.ok || !resp.body) {
    const text = await resp.text().catch(() => '')
    throw new Error(text || `请求失败 (${resp.status})`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() || ''
    for (const line of lines) {
      const s = line.trim()
      if (!s.startsWith('data:')) continue
      const p = s.slice(5).trim()
      if (p === '[DONE]') return
      try {
        const j = JSON.parse(p)
        const delta = j.choices?.[0]?.delta?.content || ''
        if (delta) handlers.onDelta(delta)
      } catch {
        /* 忽略 */
      }
    }
  }
}

export function streamReport(payload: ReportPayload, handlers: { onDelta: (t: string) => void; signal?: AbortSignal }) {
  return streamText('/api/v1/modules/social_sim/report', payload, handlers)
}

export function streamChat(payload: ChatPayload, handlers: { onDelta: (t: string) => void; signal?: AbortSignal }) {
  return streamText('/api/v1/modules/social_sim/chat', payload, handlers)
}

export function listProjects(limit = 50, offset = 0) {
  return http.get('/modules/social_sim/projects', { params: { limit, offset } })
}

export function getProject(id: string) {
  return http.get(`/modules/social_sim/projects/${id}`)
}

export function deleteProject(id: string) {
  return http.delete(`/modules/social_sim/projects/${id}`)
}

export function saveProject(body: any) {
  return http.post('/modules/social_sim/projects', body)
}

export function updateProject(id: string, body: any) {
  return http.put(`/modules/social_sim/projects/${id}`, body)
}
