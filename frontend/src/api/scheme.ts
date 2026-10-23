import http from './http'
import { getAccessToken } from '@/utils/auth'

export interface Section {
  title: string
  hint?: string | null
}

export interface SchemeTemplate {
  id: string
  code: string
  name: string
  category: string
  description?: string | null
  sections: Array<Section | string>
  tags: string[]
  is_system: boolean
  usage_count: number
  status: string
}

export interface SchemeCase {
  id: string
  title: string
  industry?: string | null
  category?: string | null
  summary?: string | null
  content: string
  tags: string[]
  quality: number
  source?: string | null
  usage_count: number
  status: string
}

export interface SchemeProject {
  id: string
  title: string
  brief: Record<string, any>
  template_id?: string | null
  case_ids: string[]
  model?: string | null
  status: string
  created_by?: string | null
  created_by_name?: string | null
  created_at?: string | null
  content?: string
}

export interface Brief {
  goal: string
  background?: string
  audience?: string
  constraints?: string
  budget?: string
  timeline?: string
  extra?: string
}

export interface MatchedTemplate {
  id: string
  code?: string
  name: string
  category?: string
  score: number
  sections: string[]
}

export interface MatchedCase {
  id: string
  title: string
  industry?: string | null
  category?: string | null
  quality: number
  score: number
  excerpt: string
}

/* ------------------------------- 模板 ------------------------------- */
export function listTemplates() {
  return http.get('/modules/scheme/templates')
}
export function createTemplate(body: Partial<SchemeTemplate>) {
  return http.post('/modules/scheme/templates', body)
}
export function updateTemplate(id: string, body: Partial<SchemeTemplate>) {
  return http.put(`/modules/scheme/templates/${id}`, body)
}
export function deleteTemplate(id: string) {
  return http.delete(`/modules/scheme/templates/${id}`)
}

/* ------------------------------- 案例 ------------------------------- */
export function listCases() {
  return http.get('/modules/scheme/cases')
}
export function createCase(body: Partial<SchemeCase>) {
  return http.post('/modules/scheme/cases', body)
}
export function updateCase(id: string, body: Partial<SchemeCase>) {
  return http.put(`/modules/scheme/cases/${id}`, body)
}
export function deleteCase(id: string) {
  return http.delete(`/modules/scheme/cases/${id}`)
}

/* ------------------------------- RAG 检索 ------------------------------- */
export function search(brief: Brief, topkTemplates = 3, topkCases = 4) {
  return http.post('/modules/scheme/search', {
    brief,
    topk_templates: topkTemplates,
    topk_cases: topkCases,
  })
}

/* ------------------------------- 方案库 ------------------------------- */
// scope: 'mine' 仅自己；'all' 需管理员权限（app:scheme:view_all），后端对普通用户强制忽略为 mine。
export function listProjects(limit = 30, offset = 0, scope: 'mine' | 'all' = 'mine') {
  return http.get('/modules/scheme/projects', { params: { limit, offset, scope } })
}
export function getProject(id: string) {
  return http.get(`/modules/scheme/projects/${id}`)
}
export function saveProject(body: Record<string, any>) {
  return http.post('/modules/scheme/projects', body)
}
export function deleteProject(id: string) {
  return http.delete(`/modules/scheme/projects/${id}`)
}

/* ------------------------------- 导出 ------------------------------- */
export function exportScheme(content: string, fmt: string, title: string) {
  return http.post('/modules/scheme/export', { content, fmt, title }, { responseType: 'blob' })
}

/* ------------------------------- 流式生成 ------------------------------- */
export interface GeneratePayload {
  brief: Brief
  template_id?: string | null
  case_ids?: string[]
  tone?: string
  length?: string
  model?: string | null
}

/**
 * RAG 流式生成（SSE）。逐段回调 onDelta；响应头回传本次实际引用的模板与案例。
 * 若后端未配置默认大模型，会返回 JSON（非 SSE），此处抛出其 message 以便提示。
 */
export async function streamGenerate(
  payload: GeneratePayload,
  handlers: {
    onDelta: (text: string) => void
    onMeta?: (templateId: string, caseIds: string[]) => void
    signal?: AbortSignal
  },
): Promise<void> {
  const token = getAccessToken()
  const resp = await fetch('/api/v1/modules/scheme/generate', {
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
    throw new Error(json?.message || json?.detail || '生成失败')
  }
  if (!resp.ok || !resp.body) {
    const text = await resp.text().catch(() => '')
    throw new Error(text || `请求失败 (${resp.status})`)
  }

  const rawTpl = resp.headers.get('X-Scheme-Template') || ''
  const rawCases = resp.headers.get('X-Scheme-Cases') || ''
  try {
    handlers.onMeta?.(
      decodeURIComponent(rawTpl),
      decodeURIComponent(rawCases).split(',').filter(Boolean),
    )
  } catch {
    /* 忽略头部解析异常 */
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
        /* 心跳/非 JSON 忽略 */
      }
    }
  }
}
