<template>
  <div class="sg-root">
    <!-- 顶栏 -->
    <div class="sg-toolbar">
      <div class="sg-brand">
        <el-icon><MagicStick /></el-icon>
        <div>
          <div class="sg-brand__t">AI 方案生成</div>
          <div class="sg-brand__s">素材 → 模板匹配 → 案例复用（RAG）→ 完整方案 → 导出</div>
        </div>
      </div>
      <div class="sg-tools">
        <el-button v-if="canManage" :icon="Files" @click="openTplDrawer">模板管理</el-button>
        <el-button v-if="canManage" :icon="Collection" @click="openCaseDrawer">案例库</el-button>
        <el-button :disabled="!content" :icon="Document" @click="exportAs('md')">导出 MD</el-button>
        <el-button :disabled="!content" :icon="Document" @click="exportAs('docx')">导出 Word</el-button>
        <el-button :disabled="!content" :icon="Document" @click="exportAs('html')">导出 HTML</el-button>
        <el-button type="primary" :disabled="!content || saving" :loading="saving" :icon="FolderAdd" @click="save">
          存入方案库
        </el-button>
      </div>
    </div>

    <div class="sg-body">
      <!-- 左：素材 / 匹配 / 方案库 -->
      <aside class="sg-left">
        <el-card shadow="never" class="sg-card">
          <template #header><span class="sg-card__t">① 素材输入</span></template>
          <el-form label-position="top" size="small" class="sg-form">
            <el-form-item label="方案目标 *">
              <el-input v-model="brief.goal" type="textarea" :rows="3" placeholder="例如：为中小企业搭建一个基于大模型的 AI 客服助手" />
            </el-form-item>
            <el-form-item label="背景与现状">
              <el-input v-model="brief.background" type="textarea" :rows="2" placeholder="业务现状、痛点、已有系统" />
            </el-form-item>
            <el-form-item label="目标受众 / 客户">
              <el-input v-model="brief.audience" placeholder="如：中小企业主 / 技术决策者" />
            </el-form-item>
            <el-form-item label="约束条件">
              <el-input v-model="brief.constraints" type="textarea" :rows="2" placeholder="合规、技术栈、交付周期等限制" />
            </el-form-item>
            <div class="sg-row2">
              <el-form-item label="预算 / 资源"><el-input v-model="brief.budget" placeholder="如：50 万以内" /></el-form-item>
              <el-form-item label="时间要求"><el-input v-model="brief.timeline" placeholder="如：3 个月上线" /></el-form-item>
            </div>
            <el-form-item label="其他补充">
              <el-input v-model="brief.extra" type="textarea" :rows="2" placeholder="参考标准、必须包含的章节等" />
            </el-form-item>
            <div class="sg-row2">
              <el-form-item label="语气">
                <el-select v-model="tone">
                  <el-option v-for="t in TONES" :key="t" :label="t" :value="t" />
                </el-select>
              </el-form-item>
              <el-form-item label="篇幅">
                <el-select v-model="length">
                  <el-option v-for="l in LENGTHS" :key="l" :label="l" :value="l" />
                </el-select>
              </el-form-item>
            </div>
          </el-form>
        </el-card>

        <el-card shadow="never" class="sg-card">
          <template #header>
            <span class="sg-card__t">② 模板与案例匹配（RAG）</span>
            <el-button size="small" text type="primary" :loading="matching" @click="runMatch">智能匹配</el-button>
          </template>
          <el-form label-position="top" size="small">
            <el-form-item label="方案模板">
              <el-select v-model="templateId" clearable placeholder="自动按素材匹配" style="width: 100%">
                <el-option v-for="t in templates" :key="t.id" :label="`${t.name}（${t.category}）`" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-form>
          <div class="sg-hint" v-if="matched.templates.length">
            <span class="sg-hint__t">推荐模板</span>
            <div v-for="m in matched.templates" :key="m.id" class="sg-match" :class="{ active: templateId === m.id }" @click="templateId = m.id">
              <span>{{ m.name }}</span>
              <em>{{ pct(m.score) }}</em>
            </div>
          </div>
          <div class="sg-hint" v-if="matched.cases.length">
            <span class="sg-hint__t">推荐案例（勾选复用，{{ caseIds.length }} 已选）</span>
            <el-checkbox-group v-model="caseIds" class="sg-cases">
              <label v-for="c in matched.cases" :key="c.id" class="sg-case">
                <el-checkbox :value="c.id" />
                <span class="sg-case__body">
                  <span class="sg-case__t">{{ c.title }} <em>{{ pct(c.score) }}</em></span>
                  <span class="sg-case__d">{{ c.excerpt }}</span>
                </span>
              </label>
            </el-checkbox-group>
          </div>
          <div class="sg-empty-mini" v-else-if="!matched.templates.length">填写素材后点击「智能匹配」，系统将检索最相关的模板与历史案例。</div>
        </el-card>

        <el-card shadow="never" class="sg-card">
          <template #header>
            <span class="sg-card__t">方案库</span>
            <div class="sg-proj-head__r">
              <el-radio-group v-if="canViewAll" v-model="projectScope" size="small" @change="loadProjects">
                <el-radio-button value="mine">我的</el-radio-button>
                <el-radio-button value="all">全部</el-radio-button>
              </el-radio-group>
              <el-button size="small" text @click="loadProjects">刷新</el-button>
            </div>
          </template>
          <div class="sg-projects">
            <div v-for="p in projects" :key="p.id" class="sg-proj" @click="openProject(p.id)">
              <span class="sg-proj__t">{{ p.title }}</span>
              <span v-if="projectScope === 'all' && p.created_by_name" class="sg-proj__owner">{{ p.created_by_name }}</span>
              <span class="sg-proj__d">{{ fmtTime(p.created_at) }}</span>
              <el-icon class="sg-proj__x" @click.stop="removeProject(p.id)"><Delete /></el-icon>
            </div>
            <div v-if="!projects.length" class="sg-empty-mini">暂无已保存方案。</div>
          </div>
        </el-card>
      </aside>

      <!-- 中：生成结果 -->
      <main class="sg-center">
        <div class="sg-resultbar">
          <span class="sg-status">{{ statusText }}</span>
          <span class="sg-refs" v-if="refInfo">{{ refInfo }}</span>
          <div class="sg-actions">
            <el-button v-if="!generating" type="primary" :disabled="!brief.goal" :icon="MagicStick" @click="generate">
              {{ content ? '重新生成' : '生成方案' }}
            </el-button>
            <el-button v-else type="danger" :icon="VideoPause" @click="stop">停止</el-button>
            <el-button :disabled="!content" @click="content = ''">清空</el-button>
          </div>
        </div>
        <div v-if="content" class="sg-preview" v-html="rendered"></div>
        <div v-else class="sg-placeholder">
          <el-icon><Document /></el-icon>
          <p>填写左侧素材后点击「生成方案」</p>
          <p class="sg-placeholder__s">系统将按模板骨架检索并复用历史案例，自动生成完整方案正文</p>
        </div>
      </main>
    </div>

    <!-- 抽屉：模板管理 -->
    <el-drawer v-model="tplDrawer" title="模板管理" size="640px">
      <el-button type="primary" size="small" :icon="Plus" @click="openEdit('template')">新建模板</el-button>
      <el-table :data="templates" size="small" class="sg-table" max-height="70vh">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="章节" width="70">
          <template #default="{ row }">{{ (row.sections || []).length }}</template>
        </el-table-column>
        <el-table-column label="类型" width="70">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'info' : 'success'">{{ row.is_system ? '内置' : '自定义' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="usage_count" label="用量" width="60" />
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEdit('template', row)">编辑</el-button>
            <el-button size="small" text @click="duplicateTemplate(row)">复制</el-button>
            <el-button size="small" text type="danger" :disabled="row.is_system" @click="removeTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 抽屉：案例库 -->
    <el-drawer v-model="caseDrawer" title="案例库" size="820px">
      <el-button type="primary" size="small" :icon="Plus" @click="openEdit('case')">新增案例</el-button>
      <el-table :data="cases" size="small" class="sg-table" max-height="70vh">
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="industry" label="行业" width="90" />
        <el-table-column prop="category" label="类别" width="100" />
        <el-table-column prop="quality" label="质量" width="70" />
        <el-table-column prop="usage_count" label="用量" width="60" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEdit('case', row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="removeCase(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editVisible" :title="editTitle" width="720px">
      <el-form v-if="editType === 'template'" label-position="top" size="small">
        <div class="sg-row2">
          <el-form-item label="模板名称 *"><el-input v-model="tplForm.name" /></el-form-item>
          <el-form-item label="分类"><el-input v-model="tplForm.category" /></el-form-item>
        </div>
        <el-form-item label="描述"><el-input v-model="tplForm.description" /></el-form-item>
        <el-form-item label="标签（逗号分隔）"><el-input v-model="tplForm.tagsText" /></el-form-item>
        <el-form-item label="章节骨架（每行一节，格式：标题 | 写作提示）">
          <el-input v-model="tplForm.sectionsText" type="textarea" :rows="9" placeholder="项目背景与目标 | 业务现状、动因、量化目标" />
        </el-form-item>
      </el-form>
      <el-form v-else label-position="top" size="small">
        <el-form-item label="案例标题 *"><el-input v-model="caseForm.title" /></el-form-item>
        <div class="sg-row2">
          <el-form-item label="行业"><el-input v-model="caseForm.industry" /></el-form-item>
          <el-form-item label="类别"><el-input v-model="caseForm.category" /></el-form-item>
        </div>
        <div class="sg-row2">
          <el-form-item label="质量（1-5）"><el-input-number v-model="caseForm.quality" :min="1" :max="5" /></el-form-item>
          <el-form-item label="标签（逗号分隔）"><el-input v-model="caseForm.tagsText" /></el-form-item>
        </div>
        <el-form-item label="摘要"><el-input v-model="caseForm.summary" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="正文（Markdown）"><el-input v-model="caseForm.content" type="textarea" :rows="10" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MagicStick, Files, Collection, Document, FolderAdd, Delete, Plus, VideoPause,
} from '@element-plus/icons-vue'
import { hasPerm } from '@/utils/permission'
import * as api from '@/api/scheme'
import type { Brief, SchemeCase, SchemeTemplate, MatchedTemplate, MatchedCase, SchemeProject } from '@/api/scheme'

defineProps<{ code?: string; name?: string }>()

const TONES = ['专业正式', '务实简洁', '商务提案', '技术严谨', '通俗易懂']
const LENGTHS = ['精简（约 800-1200 字）', '标准（约 1500-2500 字）', '详尽（约 3000 字以上）']

const canManage = computed(() => hasPerm('app:scheme:manage'))
// 管理员（app:scheme:view_all）可在「我的 / 全部」之间切换；普通用户恒为 mine。
const canViewAll = computed(() => hasPerm('app:scheme:view_all'))
const projectScope = ref<'mine' | 'all'>(canViewAll.value ? 'all' : 'mine')

/* ----------------------------- 状态 ----------------------------- */
const brief = reactive<Brief>({ goal: '', background: '', audience: '', constraints: '', budget: '', timeline: '', extra: '' })
const tone = ref(TONES[0])
const length = ref(LENGTHS[1])

const templates = ref<SchemeTemplate[]>([])
const cases = ref<SchemeCase[]>([])
const projects = ref<SchemeProject[]>([])
const matched = reactive<{ templates: MatchedTemplate[]; cases: MatchedCase[] }>({ templates: [], cases: [] })
const templateId = ref<string | null>(null)
const caseIds = ref<string[]>([])

const content = ref('')
const generating = ref(false)
const matching = ref(false)
const saving = ref(false)
const statusText = ref('就绪')
const refInfo = ref('')
let abort: AbortController | null = null

/* ----------------------------- 加载 ----------------------------- */
async function loadTemplates() {
  try {
    const res = await api.listTemplates()
    templates.value = res.data.data || []
  } catch { /* 已提示 */ }
}
async function loadCases() {
  try {
    const res = await api.listCases()
    cases.value = res.data.data || []
  } catch { /* 已提示 */ }
}
async function loadProjects() {
  try {
    const res = await api.listProjects(30, 0, projectScope.value)
    projects.value = res.data.data?.items || []
  } catch { /* 已提示 */ }
}

/* ----------------------------- RAG 匹配 ----------------------------- */
async function runMatch() {
  if (!brief.goal.trim()) {
    ElMessage.warning('请先填写方案目标')
    return
  }
  matching.value = true
  try {
    const res = await api.search({ ...brief }, 3, 4)
    const d = res.data.data || {}
    matched.templates = d.templates || []
    matched.cases = d.cases || []
    if (!templateId.value && matched.templates.length) templateId.value = matched.templates[0].id
    caseIds.value = (matched.cases || []).map((c) => c.id)
    statusText.value = `已匹配 ${matched.templates.length} 个模板、${matched.cases.length} 个案例`
  } catch { /* 已提示 */ } finally {
    matching.value = false
  }
}

/* ----------------------------- 生成 ----------------------------- */
async function generate() {
  if (!brief.goal.trim()) {
    ElMessage.warning('请填写方案目标')
    return
  }
  content.value = ''
  generating.value = true
  statusText.value = '正在生成…'
  refInfo.value = ''
  abort = new AbortController()
  try {
    await api.streamGenerate(
      {
        brief: { ...brief },
        template_id: templateId.value,
        case_ids: caseIds.value,
        tone: tone.value,
        length: length.value,
      },
      {
        signal: abort.signal,
        onDelta: (t) => {
          content.value += t
        },
        onMeta: (tplId, ids) => {
          const t = templates.value.find((x) => x.id === tplId)
          refInfo.value = `引用模板：${t ? t.name : '通用骨架'} ｜ 复用案例 ${ids.length} 个`
        },
      },
    )
    statusText.value = content.value ? `生成完成（${content.value.length} 字）` : '生成完成（无内容）'
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      statusText.value = '已停止生成'
    } else {
      statusText.value = '生成失败'
      ElMessage.error(e?.message || '生成失败，请检查大模型接入配置')
    }
  } finally {
    generating.value = false
    abort = null
  }
}
function stop() {
  abort?.abort()
}

/* ----------------------------- 导出 / 保存 ----------------------------- */
async function exportAs(fmt: string) {
  if (!content.value) return
  try {
    const title = brief.goal.slice(0, 30) || '方案'
    const res = await api.exportScheme(content.value, fmt, title)
    const ext = fmt === 'docx' || fmt === 'word' ? 'docx' : fmt
    const ct = ((res.headers as any)?.['content-type'] as string | undefined) || 'application/octet-stream'
    const blob = new Blob([res.data], { type: ct })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${title}.${ext}`
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success('已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function save() {
  if (!content.value) return
  saving.value = true
  try {
    await api.saveProject({
      title: brief.goal.slice(0, 60) || '未命名方案',
      brief: { ...brief },
      template_id: templateId.value,
      case_ids: caseIds.value,
      content: content.value,
    })
    ElMessage.success('已存入方案库')
    await loadProjects()
  } catch { /* 已提示 */ } finally {
    saving.value = false
  }
}

async function openProject(id: string) {
  try {
    const res = await api.getProject(id)
    const p = res.data.data
    Object.assign(brief, { goal: '', background: '', audience: '', constraints: '', budget: '', timeline: '', extra: '', ...(p.brief || {}) })
    content.value = p.content || ''
    templateId.value = p.template_id || null
    caseIds.value = p.case_ids || []
    statusText.value = '已载入方案库记录'
  } catch { /* 已提示 */ }
}
async function removeProject(id: string) {
  try {
    await ElMessageBox.confirm('确认删除该方案记录？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await api.deleteProject(id)
  await loadProjects()
}

/* ----------------------------- 模板/案例 CRUD ----------------------------- */
const tplDrawer = ref(false)
const caseDrawer = ref(false)
const editVisible = ref(false)
const editType = ref<'template' | 'case'>('template')
const editSaving = ref(false)
const editId = ref<string | null>(null)

const tplForm = reactive({ name: '', category: '', description: '', tagsText: '', sectionsText: '' })
const caseForm = reactive({ title: '', industry: '', category: '', quality: 3, tagsText: '', summary: '', content: '' })

const editTitle = computed(() => {
  const kind = editType.value === 'template' ? '模板' : '案例'
  return editId.value ? `编辑${kind}` : `新建${kind}`
})

function openTplDrawer() { tplDrawer.value = true; loadTemplates() }
function openCaseDrawer() { caseDrawer.value = true; loadCases() }

function openEdit(type: 'template' | 'case', row?: any) {
  editType.value = type
  editId.value = row?.id || null
  if (type === 'template') {
    tplForm.name = row?.name || ''
    tplForm.category = row?.category || '通用'
    tplForm.description = row?.description || ''
    tplForm.tagsText = (row?.tags || []).join(', ')
    tplForm.sectionsText = (row?.sections || [])
      .map((s: any) => (typeof s === 'string' ? s : `${s.title}${s.hint ? ' | ' + s.hint : ''}`))
      .join('\n')
  } else {
    caseForm.title = row?.title || ''
    caseForm.industry = row?.industry || ''
    caseForm.category = row?.category || ''
    caseForm.quality = row?.quality || 3
    caseForm.tagsText = (row?.tags || []).join(', ')
    caseForm.summary = row?.summary || ''
    caseForm.content = row?.content || ''
  }
  editVisible.value = true
}

function parseTags(text: string): string[] {
  return text.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}
function parseSections(text: string) {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const [title, hint] = line.split('|').map((s) => s.trim())
      return { title: title || '', hint: hint || null }
    })
}

async function submitEdit() {
  if (editType.value === 'template' && !tplForm.name.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }
  if (editType.value === 'case' && !caseForm.title.trim()) {
    ElMessage.warning('请填写案例标题')
    return
  }
  editSaving.value = true
  try {
    if (editType.value === 'template') {
      const body = {
        name: tplForm.name,
        category: tplForm.category || '通用',
        description: tplForm.description,
        tags: parseTags(tplForm.tagsText),
        sections: parseSections(tplForm.sectionsText),
        status: 'active',
      }
      if (editId.value) await api.updateTemplate(editId.value, body)
      else await api.createTemplate(body)
    } else {
      const body = {
        title: caseForm.title,
        industry: caseForm.industry,
        category: caseForm.category,
        quality: caseForm.quality,
        tags: parseTags(caseForm.tagsText),
        summary: caseForm.summary,
        content: caseForm.content,
        status: 'active',
      }
      if (editId.value) await api.updateCase(editId.value, body)
      else await api.createCase(body)
    }
    ElMessage.success('已保存')
    editVisible.value = false
    await Promise.all([loadTemplates(), loadCases()])
  } catch { /* 已提示 */ } finally {
    editSaving.value = false
  }
}

async function duplicateTemplate(row: SchemeTemplate) {
  try {
    await api.createTemplate({
      name: `${row.name}（副本）`,
      category: row.category,
      description: row.description || '',
      tags: row.tags || [],
      sections: (row.sections || []).map((s: any) => (typeof s === 'string' ? { title: s, hint: null } : { title: s.title, hint: s.hint ?? null })),
      status: 'active',
    })
    ElMessage.success('已复制')
    await loadTemplates()
  } catch { /* 已提示 */ }
}

async function removeTemplate(row: SchemeTemplate) {
  try {
    await ElMessageBox.confirm(`确认删除模板「${row.name}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.deleteTemplate(row.id)
    await loadTemplates()
  } catch { /* 已提示 */ }
}
async function removeCase(row: SchemeCase) {
  try {
    await ElMessageBox.confirm(`确认删除案例「${row.title}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.deleteCase(row.id)
    await loadCases()
  } catch { /* 已提示 */ }
}

/* ----------------------------- Markdown 渲染 ----------------------------- */
function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string))
}
function inlineMd(s: string): string {
  return escapeHtml(s)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
}
function mdToHtml(md: string): string {
  const lines = (md || '').replace(/\r\n?/g, '\n').split('\n')
  const out: string[] = []
  let inCode = false
  let codeBuf: string[] = []
  let inUl = false
  let inOl = false
  const closeLists = () => {
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inOl) { out.push('</ol>'); inOl = false }
  }
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')
    if (line.trim().startsWith('```')) {
      if (inCode) { out.push('<pre><code>' + escapeHtml(codeBuf.join('\n')) + '</code></pre>'); codeBuf = []; inCode = false }
      else { closeLists(); inCode = true }
      continue
    }
    if (inCode) { codeBuf.push(line); continue }
    const st = line.trim()
    if (!st) { closeLists(); continue }
    if (/^[-*_]{3,}$/.test(st)) { closeLists(); out.push('<hr/>'); continue }
    let m = st.match(/^(#{1,6})\s+(.*)$/)
    if (m) { closeLists(); const lv = m[1].length; out.push(`<h${lv}>${inlineMd(m[2])}</h${lv}>`); continue }
    if (st.startsWith('>')) { closeLists(); out.push('<blockquote>' + inlineMd(st.replace(/^>\s?/, '')) + '</blockquote>'); continue }
    if (st.startsWith('|')) {
      if (/^\|[\s:|-]+\|$/.test(st)) continue
      const cells = st.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim())
      closeLists()
      out.push('<p class="tbl">' + cells.map(inlineMd).join(' ｜ ') + '</p>')
      continue
    }
    m = st.match(/^[-*+]\s+(.*)$/)
    if (m) { if (!inUl) { closeLists(); out.push('<ul>'); inUl = true } out.push('<li>' + inlineMd(m[1]) + '</li>'); continue }
    m = st.match(/^(\d+)[.)]\s+(.*)$/)
    if (m) { if (!inOl) { closeLists(); out.push('<ol>'); inOl = true } out.push('<li>' + inlineMd(m[2]) + '</li>'); continue }
    closeLists()
    out.push('<p>' + inlineMd(st) + '</p>')
  }
  if (inCode && codeBuf.length) out.push('<pre><code>' + escapeHtml(codeBuf.join('\n')) + '</code></pre>')
  return out.join('')
}
const rendered = computed(() => mdToHtml(content.value))

/* ----------------------------- 工具 ----------------------------- */
function pct(v: number): string {
  return `${Math.round((v || 0) * 100)}%`
}
function fmtTime(s?: string | null): string {
  if (!s) return ''
  return s.replace('T', ' ').slice(0, 16)
}

/* ----------------------------- 生命周期 ----------------------------- */
onMounted(async () => {
  await Promise.all([loadTemplates(), loadCases(), loadProjects()])
})
onUnmounted(() => abort?.abort())
</script>

<style scoped>
.sg-root { position: absolute; inset: 0; display: flex; flex-direction: column; background: var(--c-surface, #f5f7fa); color: var(--c-text-1); font-size: 13px; }
.sg-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; background: var(--c-surface-2, #fff); border-bottom: 1px solid var(--c-border, #e5e7eb); }
.sg-brand { display: flex; align-items: center; gap: 10px; }
.sg-brand .el-icon { font-size: 26px; color: var(--brand-emerald, #10b981); }
.sg-brand__t { font-weight: 700; font-size: 16px; }
.sg-brand__s { color: var(--c-text-3, #94a3b8); font-size: 12px; }
.sg-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.sg-body { flex: 1; display: grid; grid-template-columns: 380px 1fr; min-height: 0; }
.sg-left { overflow: auto; padding: 12px; border-right: 1px solid var(--c-border, #e5e7eb); display: flex; flex-direction: column; gap: 12px; }
.sg-center { overflow: auto; padding: 12px; min-width: 0; display: flex; flex-direction: column; }

.sg-card { border-radius: var(--radius-lg, 12px); }
.sg-card :deep(.el-card__header) { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; }
.sg-card__t { font-weight: 600; font-size: 13px; }
.sg-proj-head__r { display: flex; align-items: center; gap: 8px; }
.sg-form :deep(.el-form-item) { margin-bottom: 10px; }
.sg-form :deep(.el-form-item__label) { padding-bottom: 2px; font-size: 12px; color: var(--c-text-2); }
.sg-row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.sg-hint { margin-top: 8px; }
.sg-hint__t { font-size: 12px; color: var(--c-text-3); }
.sg-match { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; margin-top: 6px; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; cursor: pointer; background: var(--c-surface-3, #f8fafc); }
.sg-match:hover { border-color: var(--brand-emerald, #10b981); }
.sg-match.active { border-color: var(--brand-emerald, #10b981); background: var(--brand-grad-soft, rgba(16, 185, 129, 0.12)); font-weight: 600; }
.sg-match em { font-style: normal; color: var(--brand-emerald, #10b981); font-size: 12px; }
.sg-cases { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; width: 100%; }
.sg-case { display: flex; gap: 8px; align-items: flex-start; padding: 6px 8px; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; }
.sg-case__body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.sg-case__t { font-size: 12.5px; }
.sg-case__t em { font-style: normal; color: var(--brand-emerald, #10b981); margin-left: 4px; }
.sg-case__d { font-size: 11.5px; color: var(--c-text-3); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.sg-empty-mini { font-size: 12px; color: var(--c-text-3); padding: 8px 0; }

.sg-projects { display: flex; flex-direction: column; gap: 6px; max-height: 220px; overflow: auto; }
.sg-proj { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border: 1px solid var(--c-border, #e5e7eb); border-radius: 8px; cursor: pointer; }
.sg-proj:hover { border-color: var(--brand-emerald, #10b981); }
.sg-proj__t { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12.5px; }
.sg-proj__owner { font-size: 11px; color: var(--brand-emerald, #10b981); background: var(--brand-grad-soft, rgba(16, 185, 129, 0.12)); border-radius: 6px; padding: 1px 6px; flex-shrink: 0; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sg-proj__d { font-size: 11px; color: var(--c-text-3); }
.sg-proj__x { color: var(--c-text-3); }
.sg-proj__x:hover { color: var(--c-danger, #f43f5e); }

.sg-resultbar { display: flex; align-items: center; gap: 12px; padding: 8px 12px; margin-bottom: 10px; background: var(--c-surface-2, #fff); border: 1px solid var(--c-border, #e5e7eb); border-radius: 10px; }
.sg-status { font-weight: 600; }
.sg-refs { color: var(--c-text-3); font-size: 12px; }
.sg-actions { margin-left: auto; display: flex; gap: 8px; }

.sg-preview { flex: 1; background: #fff; border: 1px solid var(--c-border, #e5e7eb); border-radius: 10px; padding: 22px 26px; overflow: auto; line-height: 1.8; }
.sg-preview :deep(h1) { font-size: 24px; border-bottom: 2px solid var(--brand-emerald, #10b981); padding-bottom: 8px; }
.sg-preview :deep(h2) { font-size: 19px; color: #0f6e56; margin-top: 24px; }
.sg-preview :deep(h3) { font-size: 16px; margin-top: 18px; }
.sg-preview :deep(blockquote) { margin: 12px 0; padding: 8px 14px; border-left: 3px solid var(--brand-mint, #34d399); background: #f0fdf7; color: #4f7268; }
.sg-preview :deep(code) { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 12.5px; }
.sg-preview :deep(pre) { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; overflow: auto; }
.sg-preview :deep(.tbl) { font-size: 12.5px; color: #4f7268; background: #f8fafc; padding: 6px 10px; border-radius: 6px; font-family: var(--font-mono, monospace); }
.sg-preview :deep(hr) { border: none; border-top: 1px dashed #cbd5e1; margin: 20px 0; }

.sg-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; color: var(--c-text-3); background: #fff; border: 1px dashed var(--c-border, #e5e7eb); border-radius: 10px; }
.sg-placeholder .el-icon { font-size: 42px; color: var(--brand-mint, #34d399); }
.sg-placeholder__s { font-size: 12px; }

.sg-table { margin-top: 12px; }

@media (max-width: 1100px) { .sg-body { grid-template-columns: 1fr; } .sg-left { border-right: none; border-bottom: 1px solid var(--c-border); } }
</style>
