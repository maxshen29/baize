# Baize 方案撰写平台 · 代码与部署

> 能力④ 落地实现：Vue3 前端 + FastAPI 后端 + PostgreSQL(pgvector) 远程数据库。
> 借鉴 [OpenBidKit_Yibiao](https://github.com/FB208/OpenBidKit_Yibiao) 的 `templateStore` / `knowledgeBaseStore` / `doc2markdown` / `contentGenerationTask` / `aiService` 等模块。

## 1. 目录结构

```
05_代码/
├── api/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py      # 入口、CORS、路由挂载、/api/health
│   │   ├── config.py    # 配置（DB / Ollama / LLM / 检索参数）
│   │   ├── db.py        # 引擎与会话
│   │   ├── models.py    # SQLAlchemy 模型（6 张表）
│   │   ├── schemas.py   # Pydantic 契约
│   │   ├── infra/       # parser(文档解析) / embeddings(本地嵌入) / llm(生成网关)
│   │   ├── services/    # template / document / knowledge(混合检索) / writing
│   │   └── routers/     # templates / documents / kb / writing / export
│   ├── requirements.txt
│   └── Dockerfile
├── web/                 # Vue3 + Vite + TS + Pinia + Element Plus
│   └── src/{api,views,router}
├── db/
│   ├── schema.sql       # ★ 在远程服务器执行的建库建表 + 种子模板
│   └── README.md        # 数据库部署说明
├── docker-compose.yml       # 生产：api + web（DB 远程）
├── docker-compose.dev.yml   # 本地：+ postgres+pgvector
├── .env.example             # 配置样例
└── README.md
```

## 2. 部署步骤（数据库在远程服务器）

1. **建库建表**：在远程 PostgreSQL 执行 `db/schema.sql`（需 pgvector 扩展）。详见 `db/README.md`。
2. **配置**：复制 `.env.example` 为 `.env`，填写 `DATABASE_URL`（指向远程库）、`OLLAMA_BASE_URL`、`LLM_*`。
3. **构建并启动**（应用服务器）：
   ```bash
   cd 05_代码
   docker compose up -d --build     # 启动 api(8000) 与 web(8080)
   # 打开 http://<应用服务器IP>:8080
   ```
4. **本地嵌入/生成（可选）**：在能访问的机器上安装 Ollama 并拉取模型：
   ```bash
   ollama pull bge-m3 && ollama pull qwen2.5:14b
   ```
   通过 `.env` 的 `OLLAMA_BASE_URL` / `LLM_BASE_URL` 指向该地址。

## 3. 本地联调（含 PG）

```bash
docker compose -f docker-compose.dev.yml up -d --build
# 前端 http://localhost:8080 ，后端 http://localhost:8000/docs
```

## 4. 四能力与代码映射

| 能力 | 路由 | 服务 | 关键文件 |
| --- | --- | --- | --- |
| ① 模板 | `POST/GET /api/templates` | `template_service` | `routers/template.py` |
| ② 文档 | `POST /api/documents/upload` | `document_service` | `infra/parser.py` |
| ③ 知识库 | `POST /api/kb/search` | `knowledge_service`(切片+混合检索) | `services/knowledge_service.py` |
| ④ 撰写 | `POST /api/writing/tasks` + `/sections/{id}/generate` + `/export` | `writing_service` | `services/writing_service.py` |

## 5. 环境变量速查（`.env`）

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 远程 PostgreSQL 连接串（必填） |
| `OLLAMA_BASE_URL` | 嵌入服务地址（默认本地 Ollama 11434） |
| `EMBED_MODEL` / `EMBEDDING_DIM` | 嵌入模型与维度（bge-m3 = 1024） |
| `LLM_BASE_URL` / `LLM_MODEL` | 生成网关（OpenAI-like） |
| `CORS_ORIGINS` | 允许的跨域来源 |
