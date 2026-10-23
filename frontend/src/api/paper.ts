import { getAccessToken } from '@/utils/auth'

export interface RunPayload {
  action: string
  text: string
  target_lang?: string
  model?: string | null
}

export interface AskPayload {
  text: string
  question: string
  history: { role: string; content: string }[]
  model?: string | null
}

export interface ParsedDoc {
  text: string
  char_count: number
  file_id?: string
  filename?: string
  url?: string
}

/** 上传 PDF / DOCX，返回解析后的纯文本。 */
export async function uploadPaper(code: string, file: File): Promise<ParsedDoc> {
  const fd = new FormData()
  fd.append('file', file)
  const token = getAccessToken()
  const resp = await fetch(`/api/v1/modules/${code}/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  })
  const json = await resp.json().catch(() => ({}))
  if (json.code !== 0) throw new Error(json.message || json.detail || '上传解析失败')
  return json.data
}

/** 抓取 URL 并返回正文文本。 */
export async function fetchUrlPaper(code: string, url: string): Promise<ParsedDoc> {
  const token = getAccessToken()
  const resp = await fetch(`/api/v1/modules/${code}/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ url }),
  })
  const json = await resp.json().catch(() => ({}))
  if (json.code !== 0) throw new Error(json.message || json.detail || 'URL 抓取失败')
  return json.data
}

async function streamSSE(
  url: string,
  payload: unknown,
  handlers: { onDelta: (t: string) => void; signal?: AbortSignal },
) {
  const token = getAccessToken()
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(payload),
    signal: handlers.signal,
  })
  const ct = resp.headers.get('Content-Type') || ''
  if (ct.includes('application/json')) {
    const json = await resp.json().catch(() => ({}))
    throw new Error(json?.message || json?.detail || '执行失败')
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
        /* 心跳 / 非 JSON 行忽略 */
      }
    }
  }
}

/** 编写工具：改写/润色/互译/提炼/重组/参考文献整理（SSE）。 */
export function runPaper(code: string, payload: RunPayload, handlers: { onDelta: (t: string) => void; signal?: AbortSignal }) {
  return streamSSE(`/api/v1/modules/${code}/run`, payload, handlers)
}

/** 阅读工具：交互问答（SSE，基于全文 BM25 召回 + 多轮）。 */
export function askPaper(code: string, payload: AskPayload, handlers: { onDelta: (t: string) => void; signal?: AbortSignal }) {
  return streamSSE(`/api/v1/modules/${code}/ask`, payload, handlers)
}
