# 数据库部署说明（远程 PostgreSQL）

数据库**不在本机**，本目录的 `schema.sql` 是建库建表的唯一来源（应用侧不自动建表）。
请在目标服务器的 PostgreSQL（建议 16+）上执行本文件完成初始化。

## 1. 前置条件
- 服务器已安装 PostgreSQL 16+。
- 已安装 **pgvector** 扩展（提供 `vector` 类型与 `<=>` 余弦算子）。
  - Debian/Ubuntu：`apt install postgresql-16-pgvector`
  - 或源码编译；扩展名 `vector`。
- 已创建业务库与账号，例如：
  ```sql
  CREATE DATABASE baize;
  CREATE USER baize WITH ENCRYPTED PASSWORD 'StrongPwd123!';
  GRANT ALL PRIVILEGES ON DATABASE baize TO baize;
  ```

## 2. 执行建表
```bash
# 在能连通服务器的机器上执行
psql "postgresql://baize:StrongPwd123!@<服务器IP>:5432/baize" -f schema.sql
```
- `CREATE EXTENSION IF NOT EXISTS vector;` 需要超级权限；若无，请 DBA 预先执行。
- 表/索引均带 `IF NOT EXISTS`，可重复执行。
- 种子模板（3 个示例结构）通过 `ON CONFLICT DO NOTHING` 幂等写入。

## 3. 向量召回调优（可选）
ivfflat 为近似最近邻索引，召回质量受 `probes` 影响：
```sql
-- 应用连接建立后执行（可在 api 连接池初始化里加）
SET ivfflat.probes = 10;
```
数据量增大后可考虑改用 `hnsw` 索引（pgvector 0.7+）：
```sql
DROP INDEX IF EXISTS ix_chunks_embedding;
CREATE INDEX ix_chunks_embedding
  ON chunks USING hnsw (embedding vector_cosine_ops);
```

## 4. 应用侧连接配置
在 `05_代码/.env`（或 `api/.env`）中设置：
```
DATABASE_URL=postgresql+psycopg2://baize:StrongPwd123!@<服务器IP>:5432/baize
```
确保服务器防火墙/安全组放行来自应用所在主机的 5432 端口。

## 5. 表结构速览
| 表 | 用途 |
| --- | --- |
| `templates` / `template_sections` | 能力① 可复用参考结构模板 |
| `documents` | 能力② 参考文档元信息（含去重 checksum） |
| `chunks` | 能力③ 知识切片（含 `embedding` 向量 + 全文索引） |
| `writing_tasks` / `writing_sections` | 能力④ 撰写任务与章节正文（含 citations 引用） |

## 6. 中文全文检索说明
当前 FTS 使用 `to_tsvector('simple', ...)`，`simple` 配置对中文不做分词，仅做整串/字符级匹配，
因此**中文关键词召回较弱**。知识服务采用「向量语义召回为主 + FTS 保底」的混合策略，
中文场景主要由 bge-m3 向量检索承担。若需更强中文关键词召回，可后续安装 `pg_jieba` / `zhparser`
并改用对应 tsconfig（属增强项，不影响当前部署）。
