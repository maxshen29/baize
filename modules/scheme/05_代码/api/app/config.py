"""全局配置（从环境变量 / .env 读取）。

借鉴 OpenBidKit 的 configStore 思路：所有可调参数集中在 settings 单例，
远程数据库、Ollama 嵌入与 LLM 网关地址均通过环境变量注入，便于部署到服务器。
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # ---- 应用 ----
    app_name: str = "Baize 方案撰写平台"
    api_prefix: str = "/api"
    cors_origins: str = "*"  # 逗号分隔，部署时改为前端域名

    # ---- 数据库（远程服务器，不在本机）----
    # 例：postgresql+psycopg2://baize:StrongPwd@10.0.0.5:5432/baize
    database_url: str = "postgresql+psycopg2://baize:baize@localhost:5432/baize"

    # ---- 嵌入（本地 Ollama，参考 11_本地知识库建设方案）----
    ollama_base_url: str = "http://localhost:11434"
    embed_model: str = "bge-m3"        # 1024 维，中英多语
    embedding_dim: int = 1024

    # ---- 生成 LLM（OpenAI-like 兼容，默认指向本地 Ollama）----
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5:14b"
    llm_api_key: str = "ollama"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # ---- 文件存储 ----
    upload_dir: str = "./uploads"

    # ---- 知识库/检索 ----
    chunk_overlap: int = 150          # 切片重叠字数
    chunk_min_chars: int = 300
    chunk_max_chars: int = 800
    hybrid_top_k: int = 12            # 每路召回数
    rrf_k: int = 60                   # RRF 融合常数

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins in ("*", ""):
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
