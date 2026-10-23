"""AI 方案生成 · 服务层：默认模板/案例播种、检索编排、生成与方案库。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm import chat_stream
from ...models import LlmProvider, SchemeCase, SchemeProject, SchemeTemplate, User
from .prompts import build_generation_messages, build_title
from .retrieval import retrieve

# --------------------------- 内置模板 --------------------------- #
DEFAULT_TEMPLATES: list[dict] = [
    {
        "code": "tech_solution",
        "name": "技术方案",
        "category": "技术方案",
        "description": "面向技术选型与架构设计的通用技术方案，适用于系统建设、平台搭建、技术攻关。",
        "tags": ["技术", "架构", "选型", "系统建设"],
        "sections": [
            {"title": "项目背景与目标", "hint": "业务现状、建设动因、量化目标"},
            {"title": "需求分析", "hint": "功能性/非功能性需求、边界与假设"},
            {"title": "总体技术方案", "hint": "总体思路、方案对比与选型理由"},
            {"title": "系统架构设计", "hint": "逻辑架构、部署架构、数据流"},
            {"title": "关键技术与实现", "hint": "核心难点、技术路线、接口契约"},
            {"title": "实施计划与里程碑", "hint": "阶段划分、交付物、时间点"},
            {"title": "测试与验收", "hint": "测试策略、验收标准"},
            {"title": "风险与应对", "hint": "风险登记册与缓解措施"},
            {"title": "预期收益", "hint": "业务价值与量化收益"},
        ],
    },
    {
        "code": "impl_plan",
        "name": "项目实施方案",
        "category": "实施方案",
        "description": "面向交付落地的实施方案，强调组织分工、进度与质量保障。",
        "tags": ["实施", "交付", "进度", "项目管理"],
        "sections": [
            {"title": "项目概述", "hint": "目标、范围、成功标准"},
            {"title": "实施范围与边界", "hint": "包含项与不包含项"},
            {"title": "组织与分工", "hint": "角色职责、沟通机制"},
            {"title": "实施步骤", "hint": "分阶段任务分解"},
            {"title": "进度计划与里程碑", "hint": "甘特要点、关键路径"},
            {"title": "资源与预算", "hint": "人力、设备、费用"},
            {"title": "质量保障", "hint": "评审、测试、验收"},
            {"title": "风险与应急预案", "hint": "风险与回退方案"},
        ],
    },
    {
        "code": "product_plan",
        "name": "产品方案",
        "category": "产品方案",
        "description": "面向产品规划与需求定义的产品方案，强调用户价值与商业模式。",
        "tags": ["产品", "需求", "用户", "商业化"],
        "sections": [
            {"title": "产品概述", "hint": "一句话定位与核心价值"},
            {"title": "目标用户与场景", "hint": "用户画像、典型场景"},
            {"title": "需求与痛点", "hint": "需求优先级"},
            {"title": "功能规划", "hint": "功能清单与版本节奏"},
            {"title": "产品架构", "hint": "信息架构、核心流程"},
            {"title": "运营与推广", "hint": "冷启动、增长策略"},
            {"title": "商业模式", "hint": "定价与收益模型"},
            {"title": "指标与迭代", "hint": "北极星指标、迭代机制"},
        ],
    },
    {
        "code": "training_plan",
        "name": "培训方案",
        "category": "培训方案",
        "description": "面向组织能力建设的培训方案，覆盖课程设计与效果评估。",
        "tags": ["培训", "课程", "能力建设", "评估"],
        "sections": [
            {"title": "培训背景与目标", "hint": "能力差距与培训目标"},
            {"title": "培训对象", "hint": "分层画像与人数"},
            {"title": "课程体系", "hint": "模块、课时、形式"},
            {"title": "师资与资源", "hint": "讲师、教材、平台"},
            {"title": "实施安排", "hint": "排期与场地"},
            {"title": "考核与评估", "hint": "考核方式与效果指标"},
            {"title": "预算", "hint": "费用构成"},
        ],
    },
    {
        "code": "bid_tech",
        "name": "投标技术方案",
        "category": "投标方案",
        "description": "面向招投标的技术应答方案，强调符合性、优势与承诺。",
        "tags": ["投标", "招标", "应答", "合规"],
        "sections": [
            {"title": "项目理解与需求响应", "hint": "需求对照与响应说明"},
            {"title": "技术方案总体设计", "hint": "总体架构与合规性"},
            {"title": "关键功能实现", "hint": "功能点响应"},
            {"title": "技术优势与创新", "hint": "差异化亮点"},
            {"title": "项目实施计划", "hint": "进度与组织"},
            {"title": "质量与服务承诺", "hint": "SLA 与售后"},
            {"title": "报价与商务说明", "hint": "（待确认）"},
        ],
    },
]

# --------------------------- 示例案例 --------------------------- #
DEMO_CASES: list[dict] = [
    {
        "title": "某银行智能客服升级项目（RAG 知识库）",
        "industry": "金融",
        "category": "产品方案",
        "quality": 5,
        "source": "内置示例",
        "tags": ["客服", "AI", "知识库", "RAG"],
        "summary": "为银行零售业务搭建 AI 智能客服，接入工单与产品知识库，采用 RAG 检索增强降低幻觉，坐席人工转接率下降。",
        "content": (
            "# 项目背景\n"
            "零售客户咨询量年增 35%，人工坐席成本高、夜间服务覆盖不足。\n\n"
            "# 方案要点\n"
            "- 采用大模型 + RAG：产品手册、工单历史切分为知识片段并建索引，回答时召回 Top-K 片段作为上下文。\n"
            "- 兜底策略：置信度低于阈值时转人工，并记录待补知识。\n"
            "- 渠道接入：手机银行、微信、电话 IVR 统一会话中台。\n\n"
            "# 关键指标\n"
            "| 指标 | 实施前 | 实施后 |\n| --- | --- | --- |\n"
            "| 首答响应 | 45s | 3s |\n| 人工转接率 | 62% | 28% |\n| 夜间覆盖率 | 0% | 100% |\n\n"
            "# 经验\n"
            "知识库治理是成败关键，需建立「召回质量抽检 + 每周知识补充」的运营闭环。"
        ),
    },
    {
        "title": "制造业数据中台建设与迁移",
        "industry": "制造",
        "category": "技术方案",
        "quality": 4,
        "source": "内置示例",
        "tags": ["数据中台", "迁移", "架构", "治理"],
        "summary": "为大型制造企业建设统一数据中台，整合 12 套业务系统数据，分三期完成迁移，支撑经营分析与预测性维护。",
        "content": (
            "# 总体思路\n"
            "先建标准、再迁数据、后上应用：数据标准与主数据先行，避免「垃圾进垃圾出」。\n\n"
            "# 架构要点\n"
            "- 采集层：CDC 增量同步 + 批量补录；\n"
            "- 存储层：贴源层/明细层/汇总层/应用层四层建模；\n"
            "- 服务层：统一指标平台，口径唯一。\n\n"
            "# 实施与风险\n"
            "分三期，每期 8 周；迁移采用「双跑对账」验证一致性，设置 4 小时停机窗口与回退预案。"
        ),
    },
    {
        "title": "政务云平台整体迁移实施方案",
        "industry": "政务",
        "category": "实施方案",
        "quality": 4,
        "source": "内置示例",
        "tags": ["政务云", "迁移", "实施方案", "等保"],
        "summary": "将 40+ 业务系统分批次迁移至政务云，满足等保三级要求，保障迁移期间业务连续性。",
        "content": (
            "# 迁移策略\n"
            "按「低风险先行、核心系统殿后」的批次策略，每批次含试点、推广、收尾三步。\n\n"
            "# 关键措施\n"
            "- 迁移前完成资产盘点与依赖关系测绘；\n"
            "- 采用容器化改造降低环境耦合；\n"
            "- 建立迁移演练机制，至少全流程演练一次。\n\n"
            "# 验收\n"
            "功能回归通过率 100%，性能不低于迁移前基线，安全扫描无高危项。"
        ),
    },
    {
        "title": "新员工入职培训体系搭建",
        "industry": "通用",
        "category": "培训方案",
        "quality": 3,
        "source": "内置示例",
        "tags": ["培训", "入职", "能力建设"],
        "summary": "设计 30-60-90 天入职培训体系，涵盖文化融入、业务认知与岗位技能，配套导师制与考核。",
        "content": (
            "# 培训框架\n"
            "30 天（融入）：企业文化、组织架构、基础制度；\n"
            "60 天（上手）：业务流程、工具使用、跟岗实践；\n"
            "90 天（胜任）：独立承担任务，输出转正答辩。\n\n"
            "# 机制\n"
            "一人一导师；每周一次复盘；结业考核含笔试 + 实操 + 导师评价。"
        ),
    },
]


# --------------------------- 播种 --------------------------- #
async def seed_defaults(db: AsyncSession) -> None:
    """幂等播种内置模板与示例案例（按 code / title 去重）。"""
    for tpl in DEFAULT_TEMPLATES:
        exists = (
            await db.execute(select(SchemeTemplate).where(SchemeTemplate.code == tpl["code"]))
        ).scalars().first()
        if not exists:
            db.add(SchemeTemplate(**(tpl | {"is_system": True, "status": "active"})))
    for case in DEMO_CASES:
        exists = (
            await db.execute(select(SchemeCase).where(SchemeCase.title == case["title"]))
        ).scalars().first()
        if not exists:
            db.add(SchemeCase(**(case | {"status": "active"})))
    await db.commit()


_seeded = False


async def ensure_seeded(db: AsyncSession) -> None:
    """进程内一次性播种（避免每次请求重复查询）。"""
    global _seeded
    if _seeded:
        return
    await seed_defaults(db)
    _seeded = True


# --------------------------- 序列化 --------------------------- #
def tpl_out(t: SchemeTemplate) -> dict:
    return {
        "id": str(t.id), "code": t.code, "name": t.name, "category": t.category,
        "description": t.description, "sections": t.sections or [], "tags": t.tags or [],
        "is_system": t.is_system, "usage_count": t.usage_count, "status": t.status,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def case_out(c: SchemeCase) -> dict:
    return {
        "id": str(c.id), "title": c.title, "industry": c.industry, "category": c.category,
        "summary": c.summary, "content": c.content, "tags": c.tags or [],
        "quality": c.quality, "source": c.source, "usage_count": c.usage_count,
        "status": c.status, "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def tpl_dict(t: SchemeTemplate) -> dict:
    """检索用的精简字典。"""
    return {
        "id": t.id, "code": t.code, "name": t.name, "category": t.category,
        "description": t.description, "tags": t.tags or [], "sections": t.sections or [],
    }


def case_dict(c: SchemeCase) -> dict:
    return {
        "id": c.id, "title": c.title, "industry": c.industry, "category": c.category,
        "summary": c.summary, "content": c.content, "tags": c.tags or [], "quality": c.quality,
    }


# --------------------------- 查询 / 检索 --------------------------- #
async def list_templates(db: AsyncSession) -> list[SchemeTemplate]:
    return list(
        (
            await db.execute(
                select(SchemeTemplate).order_by(
                    SchemeTemplate.is_system.desc(), SchemeTemplate.updated_at.desc()
                )
            )
        ).scalars().all()
    )


async def list_cases(db: AsyncSession) -> list[SchemeCase]:
    return list(
        (
            await db.execute(
                select(SchemeCase).order_by(SchemeCase.quality.desc(), SchemeCase.updated_at.desc())
            )
        ).scalars().all()
    )


async def search(db: AsyncSession, brief_text: str, topk_templates: int = 3, topk_cases: int = 4) -> dict:
    """RAG 检索：对模板与案例做加权 BM25 召回与排序。"""
    tpls = await list_templates(db)
    cases = await list_cases(db)
    active_t = [tpl_dict(t) for t in tpls if t.status == "active"]
    active_c = [case_dict(c) for c in cases if c.status == "active"]
    return retrieve(brief_text, active_t, active_c, topk_templates, topk_cases)


# --------------------------- 生成 --------------------------- #
async def get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


def generation_messages(
    brief: dict, template: dict | None, cases: list[dict], tone: str, length: str
) -> list[dict]:
    return build_generation_messages(brief, template, cases, tone, length)


def stream(provider: LlmProvider, messages: list[dict], model: str | None = None, temperature: float = 0.6):
    """透传大模型 SSE（OpenAI 兼容原始字节）。"""
    return chat_stream(provider, messages, model=model, temperature=temperature)


def derive_title(brief: dict, template: dict | None) -> str:
    return build_title(brief, template)


# --------------------------- 方案库 --------------------------- #
def _as_uuid(v):
    import uuid as _uuid

    if not v:
        return None
    try:
        return _uuid.UUID(str(v))
    except (ValueError, TypeError):
        return None


async def save_project(
    db: AsyncSession,
    *,
    title: str,
    brief: dict,
    template_id: str | None,
    case_ids: list[str],
    content: str,
    model: str | None,
    user_id=None,
) -> SchemeProject:
    p = SchemeProject(
        title=(title or "未命名方案")[:255],
        brief=brief or {},
        template_id=_as_uuid(template_id),
        case_ids=[str(c) for c in (case_ids or [])],
        content=content or "",
        model=model,
        created_by=_as_uuid(user_id),
    )
    db.add(p)
    # 用量累加（模板 + 案例），用于后续热度排序
    tid = _as_uuid(template_id)
    if tid:
        t = await db.get(SchemeTemplate, tid)
        if t:
            t.usage_count = (t.usage_count or 0) + 1
    for cid in case_ids or []:
        c = await db.get(SchemeCase, _as_uuid(cid))
        if c:
            c.usage_count = (c.usage_count or 0) + 1
    await db.commit()
    await db.refresh(p)
    return p


def project_out(p: SchemeProject, with_content: bool = True) -> dict:
    d = {
        "id": str(p.id),
        "title": p.title,
        "brief": p.brief or {},
        "template_id": str(p.template_id) if p.template_id else None,
        "case_ids": p.case_ids or [],
        "model": p.model,
        "status": p.status,
        "created_by": str(p.created_by) if p.created_by else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
    if with_content:
        d["content"] = p.content or ""
    return d


async def list_projects(
    db: AsyncSession,
    limit: int = 30,
    offset: int = 0,
    *,
    user_id=None,
    scope: str = "all",
    view_all: bool = False,
) -> tuple[list[SchemeProject], int]:
    """方案历史列表查询。

    - 普通用户（view_all=False）：强制只看自己创建的方案。
    - 管理员（view_all=True）：scope=all 看全部；scope=mine 仅看自己。
    """
    owner_filter = (not view_all) or (scope == "mine")
    base = select(SchemeProject)
    if owner_filter and user_id is not None:
        base = base.where(SchemeProject.created_by == _as_uuid(user_id))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(SchemeProject.created_at.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return list(rows), int(total)


async def list_owner_names(db: AsyncSession, ids: list) -> dict:
    """批量查询方案创建人展示名（id -> display_name|username），用于管理员「全部方案」视图。"""
    if not ids:
        return {}
    uuids = [_as_uuid(i) for i in ids if _as_uuid(i)]
    if not uuids:
        return {}
    rows = (
        await db.execute(select(User.id, User.display_name, User.username).where(User.id.in_(uuids)))
    ).all()
    return {str(r.id): (r.display_name or r.username) for r in rows}
