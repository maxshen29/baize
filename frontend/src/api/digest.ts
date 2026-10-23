import { getAccessToken } from '@/utils/auth'

export type DigestTask = 'summary' | 'translate' | 'extract' | 'outline'

export interface RefinePayload {
  text: string
  task: DigestTask
  target_lang?: string
  length?: string
  model?: string | null
}

/**
 * 文档提炼流式生成（SSE）。逐段回调 onDelta；若后端未配置默认大模型返回 JSON，抛出其 message。
 */
export async function streamRefine(
  payload: RefinePayload,
  handlers: {
    onDelta: (text: string) => void
    signal?: AbortSignal
  },
): Promise<void> {
  const token = getAccessToken()
  const resp = await fetch('/api/v1/modules/digest/refine', {
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
    throw new Error(json?.message || json?.detail || '提炼失败')
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
