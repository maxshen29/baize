import http from './http'
import { getAccessToken } from '@/utils/auth'

export interface LlmProvider {
  id: string
  name: string
  base_url: string
  api_key_masked: string
  model: string
  is_default: boolean
  notes?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ProviderInput {
  name: string
  base_url: string
  api_key: string
  model: string
  is_default: boolean
  notes?: string | null
}

export function listProviders() {
  return http.get('/llm/providers')
}

export function createProvider(body: ProviderInput) {
  return http.post('/llm/providers', body)
}

export function updateProvider(id: string, body: ProviderInput) {
  return http.put(`/llm/providers/${id}`, body)
}

export function deleteProvider(id: string) {
  return http.delete(`/llm/providers/${id}`)
}

export function testProvider(id: string) {
  return http.post(`/llm/providers/${id}/test`, {})
}

export function setDefaultProvider(id: string) {
  return http.post(`/llm/providers/${id}/set-default`, {})
}

export function getDefaultProvider() {
  return http.get('/llm/default')
}

export function listModels() {
  return http.get('/llm/models')
}

export interface ChatMessage {
  role: string
  content: string
}

/**
 * 基于「AI 数据分析」模块数据画像的流式对话。
 * 直接以 fetch 读取 SSE（/api/v1/modules/data-analytics/ai/chat），
 * 逐字 yield 文本增量，供视图做打字机式渲染。
 */
export async function* streamDataChat(
  messages: ChatMessage[],
  dataProfile: string,
  opts?: { model?: string; temperature?: number; signal?: AbortSignal }
): AsyncGenerator<string> {
  const token = getAccessToken()
  const resp = await fetch('/api/v1/modules/data-analytics/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      messages,
      data_profile: dataProfile,
      model: opts?.model,
      temperature: opts?.temperature ?? 0.6,
    }),
    signal: opts?.signal,
  })
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
      const t = line.trim()
      if (!t.startsWith('data:')) continue
      const payload = t.slice(5).trim()
      if (payload === '[DONE]') return
      try {
        const json = JSON.parse(payload)
        const delta = json.choices?.[0]?.delta?.content || ''
        if (delta) yield delta
      } catch {
        /* 心跳或非 JSON 行忽略 */
      }
    }
  }
}

