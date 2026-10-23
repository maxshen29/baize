"""AI 数据分析 · 离线服务（内置示例数据集 + 启发式洞察）。

真实环境可在此接入数仓/OLAP 与 LLM，接口形状保持不变。
"""
from __future__ import annotations

DATASETS: dict[str, dict] = {
    "sales": {
        "id": "sales",
        "name": "区域季度销售额",
        "desc": "2024 四大区销售额",
        "unit": "万元",
        "series": [
            {"label": "华东", "value": 1280},
            {"label": "华北", "value": 960},
            {"label": "华南", "value": 1120},
            {"label": "西部", "value": 640},
        ],
    },
    "traffic": {
        "id": "traffic",
        "name": "站点日活趋势",
        "desc": "近 7 天日活跃用户",
        "unit": "万",
        "series": [
            {"label": "周一", "value": 32},
            {"label": "周二", "value": 35},
            {"label": "周三", "value": 33},
            {"label": "周四", "value": 41},
            {"label": "周五", "value": 47},
            {"label": "周六", "value": 52},
            {"label": "周日", "value": 49},
        ],
    },
    "risk": {
        "id": "risk",
        "name": "风险事件分布",
        "desc": "各渠道风险事件数",
        "unit": "件",
        "series": [
            {"label": "登录异常", "value": 18},
            {"label": "接口超时", "value": 27},
            {"label": "数据越权", "value": 6},
            {"label": "爬虫攻击", "value": 41},
            {"label": "注入尝试", "value": 12},
        ],
    },
}


def list_datasets() -> list[dict]:
    return [
        {"id": d["id"], "name": d["name"], "desc": d["desc"], "unit": d["unit"]}
        for d in DATASETS.values()
    ]


def get_dataset(ds_id: str) -> dict | None:
    d = DATASETS.get(ds_id)
    if not d:
        return None
    return {
        "id": d["id"],
        "name": d["name"],
        "desc": d["desc"],
        "unit": d["unit"],
        "series": d["series"],
    }


def insights(ds_id: str) -> dict:
    d = DATASETS.get(ds_id)
    if not d:
        return {"summary": "未找到数据集", "points": []}
    s = d["series"]
    vals = [p["value"] for p in s]
    total = sum(vals)
    mx = max(s, key=lambda p: p["value"])
    mn = min(s, key=lambda p: p["value"])
    avg = total / len(vals)
    trend_up = s[-1]["value"] >= s[0]["value"]
    delta = s[-1]["value"] - s[0]["value"]
    points = [
        f"共 {len(s)} 项指标，合计 {total} {d['unit']}，平均 {avg:.1f} {d['unit']}。",
        f"峰值出现在「{mx['label']}」（{mx['value']} {d['unit']}），谷值出现在「{mn['label']}」（{mn['value']} {d['unit']}）。",
        f"头部 1 项占比约 {mx['value'] / total * 100:.0f}%，分布{'较为均衡' if mx['value'] / total < 0.4 else '存在明显集中'}。",
        f"整体呈{'上升' if trend_up else '下降'}趋势（末项较首项 {('+' if trend_up else '')}{delta} {d['unit']}）。",
    ]
    summary = f"{d['name']}：合计 {total}{d['unit']}，峰值 {mx['label']}，{'上行' if trend_up else '下行'}。"
    return {"summary": summary, "points": points, "top": mx["label"], "top_value": mx["value"]}
