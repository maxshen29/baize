-- ============================================================================
-- Baize 方案撰写平台 · 数据库 Schema（PostgreSQL 16 + pgvector）
-- 用途：在【远程服务器】的 PostgreSQL 上执行本文件完成建库建表与初始化。
-- 执行示例：
--   psql "postgresql://baize:密码@<服务器IP>:5432/baize" -f schema.sql
-- 前置：服务器已安装 pgvector 扩展（或超级用户执行 CREATE EXTENSION 有权限）。
-- ============================================================================

-- 1) 向量扩展（pgvector 提供 vector 类型与 <=> 余弦距离算子）
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) 能力①：可复用参考结构模板
CREATE TABLE IF NOT EXISTS templates (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    scenario    TEXT,
    version     INTEGER NOT NULL DEFAULT 1,
    author      TEXT,
    tags        JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS template_sections (
    id               TEXT PRIMARY KEY,
    template_id      TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    parent_id        TEXT REFERENCES template_sections(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    level            INTEGER NOT NULL DEFAULT 1,
    required         BOOLEAN NOT NULL DEFAULT TRUE,
    "order"          INTEGER NOT NULL DEFAULT 0,
    guidance         TEXT NOT NULL DEFAULT '',
    placeholders     JSONB NOT NULL DEFAULT '[]',
    source_tags      JSONB NOT NULL DEFAULT '[]'
);

-- 3) 能力② + ③：参考文档与知识切片（同库，见 11_本地知识库建设方案）
CREATE TABLE IF NOT EXISTS documents (
    id             TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    source_type    TEXT NOT NULL,
    original_path  TEXT,
    parsed_path    TEXT,
    status         TEXT NOT NULL DEFAULT 'imported',
    checksum       TEXT,
    tags           JSONB NOT NULL DEFAULT '[]',
    classification TEXT,
    version        INTEGER NOT NULL DEFAULT 1,
    chunk_count    INTEGER NOT NULL DEFAULT 0,
    imported_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    heading_path  TEXT,
    content       TEXT NOT NULL,
    chunk_index   INTEGER NOT NULL DEFAULT 0,
    keywords      JSONB NOT NULL DEFAULT '[]',
    facets        JSONB NOT NULL DEFAULT '{}',
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    status        TEXT NOT NULL DEFAULT 'active',
    embedding     VECTOR(1024)     -- 与 Ollama bge-m3 维度一致（1024）
);

-- 4) 能力④：基于知识库按需撰写
CREATE TABLE IF NOT EXISTS writing_tasks (
    id            TEXT PRIMARY KEY,
    template_id   TEXT REFERENCES templates(id) ON DELETE SET NULL,
    title         TEXT NOT NULL,
    kb_scope      JSONB NOT NULL DEFAULT '[]',
    global_facts  JSONB NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'draft',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS writing_sections (
    id                   TEXT PRIMARY KEY,
    task_id              TEXT NOT NULL REFERENCES writing_tasks(id) ON DELETE CASCADE,
    template_section_id  TEXT,
    title                TEXT NOT NULL,
    level                INTEGER NOT NULL DEFAULT 1,
    "order"              INTEGER NOT NULL DEFAULT 0,
    guidance             TEXT NOT NULL DEFAULT '',
    content              TEXT NOT NULL DEFAULT '',
    status               TEXT NOT NULL DEFAULT 'draft',
    citations            JSONB NOT NULL DEFAULT '[]',
    version              INTEGER NOT NULL DEFAULT 1,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5) 索引（分面 / 去重 / 向量 ANN / 全文检索）
CREATE INDEX IF NOT EXISTS ix_templates_type        ON templates(type);
CREATE INDEX IF NOT EXISTS ix_tpl_sec_template      ON template_sections(template_id);
CREATE INDEX IF NOT EXISTS ix_tpl_sec_parent        ON template_sections(parent_id);
CREATE INDEX IF NOT EXISTS ix_docs_checksum         ON documents(checksum);
CREATE INDEX IF NOT EXISTS ix_docs_source_type      ON documents(source_type);
CREATE INDEX IF NOT EXISTS ix_chunks_document       ON chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_chunks_status         ON chunks(status);
-- 语义召回：余弦距离 ANN（ivfflat）
CREATE INDEX IF NOT EXISTS ix_chunks_embedding
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- 关键词召回：表达式 GIN 全文索引（与知识服务查询一致）
CREATE INDEX IF NOT EXISTS ix_chunks_fts
    ON chunks USING GIN (to_tsvector('simple', content));
CREATE INDEX IF NOT EXISTS ix_wt_template           ON writing_tasks(template_id);
CREATE INDEX IF NOT EXISTS ix_ws_task               ON writing_sections(task_id);
CREATE INDEX IF NOT EXISTS ix_ws_template_section   ON writing_sections(template_section_id);

-- 使用 ivfflat 时建议设置探测数（召回质量/速度权衡）
-- SET ivfflat.probes = 10;  -- 会话级，可在应用连接池初始化时执行

-- ============================================================================
-- 6) 初始化种子模板（对应 02_模板 下三个示例标准结构）
-- ============================================================================
INSERT INTO templates (id, type, name, scenario, version, author, tags)
VALUES
  ('tpl-bid',  '投标', '通用投标方案',   '招投标响应', 1, '系统', '["投标"]'),
  ('tpl-tech', '技术', '通用技术方案',   '技术建议书', 1, '系统', '["技术"]'),
  ('tpl-impl', '实施', '通用项目实施方案', '项目落地交付', 1, '系统', '["实施","交付"]')
ON CONFLICT (id) DO NOTHING;

-- 投标方案章节
INSERT INTO template_sections (id, template_id, parent_id, title, level, required, "order", guidance, source_tags) VALUES
  ('sec-bid-1',  'tpl-bid', NULL, '招标须知响应',        1, TRUE, 1, '逐条响应招标须知，标注偏离', '["招标要求"]'),
  ('sec-bid-2',  'tpl-bid', NULL, '项目理解与需求分析',  1, TRUE, 2, '阐述对项目背景与核心需求的理解', '["需求","背景"]'),
  ('sec-bid-3',  'tpl-bid', NULL, '总体技术方案',        1, TRUE, 3, '给出总体架构与技术路线', '["技术架构"]'),
  ('sec-bid-4',  'tpl-bid', NULL, '实施方案与进度',      1, TRUE, 4, '交付里程碑与资源安排', '["实施","进度"]'),
  ('sec-bid-5',  'tpl-bid', NULL, '质量保障与售后服务',  1, TRUE, 5, '质保体系与运维承诺', '["质量","售后"]'),
  ('sec-bid-6',  'tpl-bid', NULL, '报价与商务',          1, TRUE, 6, '报价构成与商务条款', '["报价","商务"]')
ON CONFLICT (id) DO NOTHING;

-- 技术方案章节
INSERT INTO template_sections (id, template_id, parent_id, title, level, required, "order", guidance, source_tags) VALUES
  ('sec-tech-1', 'tpl-tech', NULL, '项目背景与目标',    1, TRUE, 1, '建设目标与范围', '["背景","目标"]'),
  ('sec-tech-2', 'tpl-tech', NULL, '总体架构设计',      1, TRUE, 2, '系统总体架构与分层', '["架构"]'),
  ('sec-tech-3', 'tpl-tech', NULL, '关键技术选型',      1, TRUE, 3, '技术栈与选型理由', '["技术选型"]'),
  ('sec-tech-4', 'tpl-tech', NULL, '功能模块设计',      1, TRUE, 4, '各模块功能说明', '["功能"]'),
  ('sec-tech-5', 'tpl-tech', NULL, '安全与合规',        1, TRUE, 5, '安全设计与合规要求', '["安全","合规"]'),
  ('sec-tech-6', 'tpl-tech', NULL, '性能与容量规划',    1, TRUE, 6, '性能指标与扩展规划', '["性能","容量"]')
ON CONFLICT (id) DO NOTHING;

-- 实施方案章节
INSERT INTO template_sections (id, template_id, parent_id, title, level, required, "order", guidance, source_tags) VALUES
  ('sec-impl-1', 'tpl-impl', NULL, '项目组织与团队',    1, TRUE, 1, '组织结构与关键人员', '["项目组织","人员"]'),
  ('sec-impl-2', 'tpl-impl', NULL, '实施进度计划',      1, TRUE, 2, '阶段划分与里程碑', '["进度"]'),
  ('sec-impl-3', 'tpl-impl', NULL, '部署与迁移方案',    1, TRUE, 3, '上线部署与数据迁移', '["部署","迁移"]'),
  ('sec-impl-4', 'tpl-impl', NULL, '培训与知识转移',    1, TRUE, 4, '用户培训与文档交付', '["培训"]'),
  ('sec-impl-5', 'tpl-impl', NULL, '风险与应对措施',    1, TRUE, 5, '风险识别与预案', '["风险"]')
ON CONFLICT (id) DO NOTHING;
