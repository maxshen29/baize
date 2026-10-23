"""社会推演 · 服务层。

负责与大模型交互：构建世界、运行多智能体推演循环、生成预测报告、与数字世界对话。
全部基于本平台已接入的 OpenAI 兼容大模型；不依赖 OASIS / Zep 等外部组件。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, AsyncGenerator, Iterable

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm import OPENAI_CHAT_PATH, _headers, _normalize_base_url, chat_stream
from ...models import LlmProvider, SocialSimulation, User
from .prompts import (
    PROMPT_BUILD_WORLD,
    PROMPT_CHAT_SYSTEM,
    PROMPT_EXTRACT_GRAPH,
    PROMPT_REPORT,
    PROMPT_ROUND,
    SYSTEM_BUILD_WORLD,
    SYSTEM_CHAT,
    SYSTEM_EXTRACT_GRAPH,
    SYSTEM_REPORT,
    SYSTEM_ROUND,
)

VALID_STANCES = ("supportive", "opposing", "neutral", "observer")
STANCE_CN = {
    "supportive": "支持",
    "opposing": "反对",
    "neutral": "中立",
    "observer": "旁观",
}


# --------------------------------------------------------------------------- #
# 通用 LLM 调用
# --------------------------------------------------------------------------- #
async def get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


async def _chat_complete(
    provider: LlmProvider,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.4,
    response_format: dict | None = None,
) -> str:
    """非流式调用，返回完整文本（用于需要 JSON 的结构化生成）。"""
    url = f"{_normalize_base_url(provider.base_url)}{OPENAI_CHAT_PATH}"
    payload: dict[str, Any] = {
        "model": model or provider.model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if response_format:
        payload["response_format"] = response_format
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=20.0)) as client:
        resp = await client.post(url, headers=_headers(provider), json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""


async def _stream_text(
    provider: LlmProvider,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """流式调用，逐块产出文本增量（解析上游 SSE）。"""
    async for raw in chat_stream(provider, messages, model=model, temperature=temperature):
        text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            try:
                j = json.loads(payload)
                delta = j.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


# --------------------------------------------------------------------------- #
# 1) 构建世界
# --------------------------------------------------------------------------- #
def _normalize_stance(v: Any) -> str:
    if isinstance(v, str) and v.lower() in VALID_STANCES:
        return v.lower()
    return "neutral"


async def build_world(
    provider: LlmProvider,
    seed_text: str,
    question: str,
    num_agents: int,
    model: str | None = None,
) -> dict:
    prompt = PROMPT_BUILD_WORLD.format(
        seed_text=seed_text.strip() or "（未提供种子材料，请基于预测需求自行设定一个合理的世界背景）",
        question=question.strip() or "（未提供预测需求，请构建一个可推演的社会演化场景）",
        num_agents=max(2, min(20, int(num_agents))),
    )
    messages = [
        {"role": "system", "content": SYSTEM_BUILD_WORLD},
        {"role": "user", "content": prompt},
    ]
    raw = await _chat_complete(provider, messages, model=model, temperature=0.7,
                              response_format={"type": "json_object"})
    data = _safe_json(raw) or {}
    world = (data.get("world") or "").strip()
    setting = (data.get("setting") or "").strip()
    personas = data.get("personas") or []
    norm: list[dict] = []
    for i, p in enumerate(personas[:20]):
        if not isinstance(p, dict):
            continue
        norm.append({
            "id": i,
            "name": str(p.get("name") or f"居民{i + 1}"),
            "role": str(p.get("role") or "居民"),
            "traits": str(p.get("traits") or ""),
            "stance": _normalize_stance(p.get("stance")),
            "background": str(p.get("background") or ""),
            "voice": str(p.get("voice") or ""),
        })
    return {"world": world, "setting": setting, "personas": norm}


# --------------------------------------------------------------------------- #
# 1b) GraphRAG：从种子材料抽取实体关系图谱
# --------------------------------------------------------------------------- #
VALID_ENTITY_TYPES = (
    "Organization", "Person", "MediaOutlet", "University", "Student", "Professor",
    "GovernmentAgency", "LegalAuthority", "Alumni", "OpinionLeader", "Event",
    "Concept", "Location", "Other",
)

ENTITY_COLORS = {
    "Organization": "#5470c6",
    "Person": "#91cc75",
    "MediaOutlet": "#fac858",
    "University": "#ee6666",
    "Student": "#73c0de",
    "Professor": "#3ba272",
    "GovernmentAgency": "#fc8452",
    "LegalAuthority": "#9a60b4",
    "Alumni": "#ea7ccc",
    "OpinionLeader": "#ff9f7f",
    "Event": "#ffdb5c",
    "Concept": "#67e0e3",
    "Location": "#37a2da",
    "Other": "#999",
}


def _normalize_graph(raw: dict) -> dict:
    """清洗 LLM 返回的图谱，确保 id 唯一、source/target 存在。"""
    nodes = []
    seen_ids = set()
    if isinstance(raw.get("nodes"), list):
        for n in raw["nodes"]:
            if not isinstance(n, dict):
                continue
            node_id = str(n.get("id") or "").strip()
            if not node_id or node_id in seen_ids:
                continue
            node_type = str(n.get("type") or "Other")
            if node_type not in VALID_ENTITY_TYPES:
                node_type = "Other"
            seen_ids.add(node_id)
            nodes.append({
                "id": node_id,
                "name": str(n.get("name") or node_id),
                "type": node_type,
                "description": str(n.get("description") or "").strip(),
                "color": ENTITY_COLORS.get(node_type, "#999"),
            })
    valid_ids = {n["id"] for n in nodes}
    edges = []
    seen_edges = set()
    if isinstance(raw.get("edges"), list):
        for e in raw["edges"]:
            if not isinstance(e, dict):
                continue
            src = str(e.get("source") or "").strip()
            tgt = str(e.get("target") or "").strip()
            if src not in valid_ids or tgt not in valid_ids or src == tgt:
                continue
            key = (src, tgt, str(e.get("relation") or ""))
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append({
                "source": src,
                "target": tgt,
                "relation": str(e.get("relation") or "关联"),
                "description": str(e.get("description") or "").strip(),
            })
    return {"nodes": nodes, "edges": edges}


async def extract_graph(
    provider: LlmProvider,
    seed_text: str,
    question: str,
    model: str | None = None,
) -> dict:
    prompt = PROMPT_EXTRACT_GRAPH.format(
        seed_text=seed_text.strip() or "（未提供种子材料，请基于预测需求自行构建一个合理的关系图谱）",
        question=question.strip() or "（未提供预测需求）",
    )
    messages = [
        {"role": "system", "content": SYSTEM_EXTRACT_GRAPH},
        {"role": "user", "content": prompt},
    ]
    raw = await _chat_complete(provider, messages, model=model, temperature=0.3,
                              response_format={"type": "json_object"})
    data = _safe_json(raw) or {}
    return _normalize_graph(data)


# --------------------------------------------------------------------------- #
# 2) 多智能体推演循环（异步生成器，逐轮产出事件）
# --------------------------------------------------------------------------- #
def _select_actors(personas: list[dict], round_no: int, k: int) -> list[dict]:
    n = len(personas)
    if n == 0:
        return []
    k = max(1, min(k, n))
    # 轮转起始点，使不同轮次由不同居民主导，同时保证覆盖
    start = (round_no * 2) % n
    order = personas[start:] + personas[:start]
    return order[:k]


def _actors_block(actors: list[dict]) -> str:
    lines = []
    for a in actors:
        lines.append(
            f"- {a['name']}（{a['role']}｜立场：{STANCE_CN.get(a['stance'], '中立')}｜风格：{a.get('voice','')}）"
            f"：{a.get('traits','')} {a.get('background','')}"
        )
    return "\n".join(lines)


def _history_block(transcript: list[dict], limit: int = 40) -> str:
    if not transcript:
        return "（尚无发言，这是推演的起点。）"
    lines = []
    for ev in transcript[-limit:]:
        lines.append(f"[第{ev['round']}轮] {ev['name']}（{ev['role']}）：{ev['content']}")
    return "\n".join(lines)


async def simulate(
    provider: LlmProvider,
    world: str,
    setting: str,
    personas: list[dict],
    question: str,
    rounds: int,
    god_events: dict[int, str],
    model: str | None = None,
) -> AsyncGenerator[dict, None]:
    rounds = max(1, min(20, int(rounds)))
    transcript: list[dict] = []
    actors_per_round = max(2, min(len(personas), max(3, round(len(personas) * 0.6))))

    for r in range(1, rounds + 1):
        yield {"type": "round_start", "round": r, "total": rounds}
        actors = _select_actors(personas, r, actors_per_round)
        god = god_events.get(r)
        god_block = (
            f"\n## 上帝视角 · 本轮新增变量（外部冲击，居民会对此作出反应）\n{god}\n"
            if god else ""
        )
        prompt = PROMPT_ROUND.format(
            round=r,
            total_rounds=rounds,
            world=world,
            setting=setting,
            question=question,
            actors_block=_actors_block(actors),
            history_block=_history_block(transcript),
            god_block=god_block,
        )
        messages = [
            {"role": "system", "content": SYSTEM_ROUND},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = await _chat_complete(provider, messages, model=model, temperature=0.85,
                                      response_format={"type": "json_object"})
            data = _safe_json(raw) or {}
            msgs = data.get("messages") or []
        except Exception as e:  # 单轮失败不中断整体，给出提示后继续
            yield {"type": "action", "round": r, "name": "系统", "role": "系统",
                   "stance": "observer", "content": f"（第 {r} 轮生成失败：{e}，已跳过）"}
            yield {"type": "round_end", "round": r}
            continue

        # 建立 name -> persona 映射
        by_name = {a["name"]: a for a in personas}
        emitted = 0
        for m in msgs:
            if not isinstance(m, dict):
                continue
            name = str(m.get("name") or "").strip()
            content = str(m.get("content") or "").strip()
            if not content:
                continue
            persona = by_name.get(name) or {}
            role = persona.get("role", "居民")
            stance = persona.get("stance", "neutral")
            transcript.append({
                "round": r, "name": name or "匿名居民",
                "role": role, "stance": stance, "content": content,
            })
            yield {"type": "action", "round": r, "name": name or "匿名居民",
                   "role": role, "stance": stance, "content": content}
            emitted += 1
        if emitted == 0:
            yield {"type": "action", "round": r, "name": "系统", "role": "系统",
                   "stance": "observer", "content": "（本轮没有生成有效发言）"}
        yield {"type": "round_end", "round": r}

    yield {"type": "done", "transcript": transcript}


# --------------------------------------------------------------------------- #
# 3) 预测报告
# --------------------------------------------------------------------------- #
def _personas_block(personas: list[dict]) -> str:
    lines = []
    for a in personas:
        lines.append(f"- {a['name']}（{a['role']}｜立场：{STANCE_CN.get(a['stance'], '中立')}）：{a.get('background','')}")
    return "\n".join(lines) if lines else "（无）"


def _transcript_block(transcript: list[dict]) -> str:
    if not transcript:
        return "（无推演记录）"
    lines = []
    for ev in transcript:
        lines.append(f"[第{ev['round']}轮] {ev['name']}（{ev['role']}）：{ev['content']}")
    return "\n".join(lines)


async def report(
    provider: LlmProvider,
    world: str,
    setting: str,
    personas: list[dict],
    question: str,
    transcript: list[dict],
    model: str | None = None,
    rounds: int = 6,
    agent_count: int = 0,
) -> AsyncGenerator[str, None]:
    prompt = PROMPT_REPORT.format(
        world=world,
        question=question,
        personas_block=_personas_block(personas),
        transcript_block=_transcript_block(transcript),
        rounds=rounds,
        agent_count=agent_count or len(personas or []),
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    messages = [
        {"role": "system", "content": SYSTEM_REPORT},
        {"role": "user", "content": prompt},
    ]
    async for delta in _stream_text(provider, messages, model=model, temperature=0.5):
        yield delta


# --------------------------------------------------------------------------- #
# 4) 与数字世界对话
# --------------------------------------------------------------------------- #
async def chat(
    provider: LlmProvider,
    world: str,
    setting: str,
    personas: list[dict],
    question: str,
    transcript: list[dict],
    report_text: str,
    messages: list[dict],
    focus: str = "",
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    focus_line = (
        f"\n## 本次对话聚焦\n用户希望重点从虚拟居民「{focus}」的视角出发作答（若其未在档案中出现，则按全体视角作答）。"
        if focus else ""
    )
    sys_content = PROMPT_CHAT_SYSTEM.format(
        world=world,
        setting=setting,
        question=question,
        personas_block=_personas_block(personas),
        transcript_block=_transcript_block(transcript),
        report_block=report_text or "（尚未生成预测报告）",
    ) + focus_line
    full = [{"role": "system", "content": sys_content}] + (messages or [])
    async for delta in _stream_text(provider, full, model=model, temperature=0.6):
        yield delta


# --------------------------------------------------------------------------- #
# 历史存档（按创建人隔离，沿用 scheme 模式）
# --------------------------------------------------------------------------- #
def _as_uuid(v: Any):
    import uuid
    if v is None:
        return None
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except (ValueError, AttributeError):
        return None


async def list_simulations(
    db: AsyncSession,
    limit: int = 30,
    offset: int = 0,
    *,
    user_id=None,
) -> tuple[list[SocialSimulation], int]:
    base = select(SocialSimulation)
    if user_id is not None:
        base = base.where(SocialSimulation.created_by == _as_uuid(user_id))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(SocialSimulation.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total)


async def list_owner_names(db: AsyncSession, ids: list) -> dict:
    uuids = [_as_uuid(i) for i in ids if _as_uuid(i)]
    if not uuids:
        return {}
    rows = (
        await db.execute(select(User.id, User.display_name, User.username).where(User.id.in_(uuids)))
    ).all()
    return {str(r.id): (r.display_name or r.username) for r in rows}


def sim_out(s: SocialSimulation, with_detail: bool = False) -> dict:
    d = {
        "id": str(s.id),
        "title": s.title,
        "question": s.question,
        "world": s.world,
        "setting": s.setting,
        "persona_count": len(s.personas or []),
        "action_count": len(s.transcript or []),
        "params": s.params or {},
        "model": s.model,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
    if with_detail:
        d["seed_text"] = s.seed_text
        d["personas"] = s.personas or []
        d["transcript"] = s.transcript or []
        d["report"] = s.report or ""
        d["graph"] = s.graph_json or {"nodes": [], "edges": []}
    return d


async def save_simulation(
    db: AsyncSession,
    *,
    title: str,
    seed_text: str,
    question: str,
    world: str,
    setting: str,
    personas: list,
    transcript: list,
    report: str,
    graph_json: dict | None,
    params: dict,
    model: str | None,
    user_id=None,
) -> SocialSimulation:
    s = SocialSimulation(
        title=title or "未命名推演",
        seed_text=seed_text or "",
        question=question or "",
        world=world or "",
        setting=setting or "",
        personas=personas or [],
        transcript=transcript or [],
        report=report or "",
        graph_json=graph_json or {"nodes": [], "edges": []},
        params=params or {},
        model=model,
        created_by=_as_uuid(user_id),
    )
    db.add(s)
    await db.flush()
    await db.commit()
    await db.refresh(s)
    return s


async def update_simulation(
    db: AsyncSession,
    sid: Any,
    *,
    title: str | None = None,
    seed_text: str | None = None,
    question: str | None = None,
    world: str | None = None,
    setting: str | None = None,
    personas: list | None = None,
    transcript: list | None = None,
    report: str | None = None,
    graph_json: dict | None = None,
    params: dict | None = None,
    model: str | None = None,
) -> SocialSimulation | None:
    """更新已存在的推演存档（用于自动存档 / 增量保存，避免重复建行）。"""
    uid = _as_uuid(sid)
    if not uid:
        return None
    s = await db.get(SocialSimulation, uid)
    if not s:
        return None
    if title is not None:
        s.title = title or "未命名推演"
    if seed_text is not None:
        s.seed_text = seed_text or ""
    if question is not None:
        s.question = question or ""
    if world is not None:
        s.world = world or ""
    if setting is not None:
        s.setting = setting or ""
    if personas is not None:
        s.personas = personas or []
    if transcript is not None:
        s.transcript = transcript or []
    if report is not None:
        s.report = report or ""
    if graph_json is not None:
        s.graph_json = graph_json or {"nodes": [], "edges": []}
    if params is not None:
        s.params = params or {}
    if model is not None:
        s.model = model
    await db.commit()
    await db.refresh(s)
    return s


# --------------------------------------------------------------------------- #
# JSON 解析容错
# --------------------------------------------------------------------------- #
def _safe_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    # 去掉可能的 ```json 围栏
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 退而求其次：截取首个 {...} 块
    import re
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None
