import http from './client'
import type {
  Template,
  TemplateSection,
  ReferenceDocument,
  SearchHit,
  WritingTask,
  WritingSection,
} from './types'

// ---- 能力① 模板 ----
export const listTemplates = (type?: string) =>
  http.get<Template[]>('/templates', { params: { type } }).then((r) => r.data)

export const getTemplate = (id: string) =>
  http.get<Template>(`/templates/${id}`).then((r) => r.data)

export const createTemplate = (payload: {
  type: string
  name: string
  scenario?: string
  author?: string
  tags?: string[]
  sections?: Partial<TemplateSection>[]
}) => http.post<Template>('/templates', payload).then((r) => r.data)

export const deleteTemplate = (id: string) =>
  http.delete(`/templates/${id}`).then((r) => r.data)

// ---- 能力② 文档 ----
export const listDocuments = () =>
  http.get<ReferenceDocument[]>('/documents').then((r) => r.data)

export const uploadDocument = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return http.post<ReferenceDocument>('/documents/upload', fd).then((r) => r.data)
}

export const getDocPreview = (id: string) =>
  http.get<{ id: string; title: string; status: string; chunk_count: number; preview: string }>(
    `/documents/${id}/preview`
  ).then((r) => r.data)

export const deleteDocument = (id: string) =>
  http.delete(`/documents/${id}`).then((r) => r.data)

// ---- 能力③ 知识库 ----
export const searchKnowledge = (payload: {
  query: string
  top_k?: number
  domain?: string
  applicable_template?: string
  source_type?: string
  document_ids?: string[]
}) => http.post<{ query: string; hits: SearchHit[] }>('/kb/search', payload).then((r) => r.data)

// ---- 能力④ 撰写 ----
export const listTasks = () => http.get<WritingTask[]>('/writing/tasks').then((r) => r.data)

export const createTask = (payload: {
  template_id?: string
  title: string
  kb_scope?: string[]
  global_facts?: Record<string, unknown>
}) => http.post<WritingTask>('/writing/tasks', payload).then((r) => r.data)

export const getTask = (id: string) =>
  http.get<WritingTask>(`/writing/tasks/${id}`).then((r) => r.data)

export const deleteTask = (id: string) =>
  http.delete(`/writing/tasks/${id}`).then((r) => r.data)

export const generateSection = (taskId: string, sectionId: string, regenerate = false) =>
  http
    .post<{ section: WritingSection; used_hits: number }>(
      `/writing/tasks/${taskId}/sections/${sectionId}/generate`,
      { regenerate }
    )
    .then((r) => r.data)

// 导出 Word：直接返回下载 URL（GET）
export const exportTaskUrl = (taskId: string) =>
  `/api/writing/tasks/${taskId}/export`
