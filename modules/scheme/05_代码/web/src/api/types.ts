// 与后端 Pydantic 契约一致（可由 OpenAPI 生成）。
export interface TemplateSection {
  id: string
  template_id: string
  parent_id: string | null
  title: string
  level: number
  required: boolean
  order: number
  guidance: string
  placeholders: string[]
  source_tags: string[]
}

export interface Template {
  id: string
  type: string
  name: string
  scenario: string | null
  version: number
  author: string | null
  tags: string[]
  created_at: string
  updated_at: string
  sections: TemplateSection[]
}

export interface ReferenceDocument {
  id: string
  title: string
  source_type: string
  status: string
  checksum: string | null
  tags: string[]
  classification: string | null
  version: number
  chunk_count: number
  imported_at: string
}

export interface SearchHit {
  chunk_id: string
  document_id: string
  document_title: string
  heading_path: string | null
  content: string
  score: number
  keywords: string[]
}

export interface WritingSection {
  id: string
  task_id: string
  template_section_id: string | null
  title: string
  level: number
  order: number
  guidance: string
  content: string
  status: string
  citations: string[]
  version: number
  updated_at: string
}

export interface WritingTask {
  id: string
  template_id: string | null
  title: string
  kb_scope: string[]
  global_facts: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
  sections: WritingSection[]
}
