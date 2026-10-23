"""AI 蛋白分析 · 离线服务（组成 / 理化性质 / 启发式功能倾向）。

真实环境可在此接入结构预测或大模型，接口形状保持不变。
"""
from __future__ import annotations

from collections import Counter

# 标准氨基酸残基质量（近似平均，Da）
_RESIDUE_MASS = {
    "A": 71.08, "R": 156.19, "N": 114.10, "D": 115.09, "C": 103.14,
    "E": 129.12, "Q": 128.13, "G": 57.05, "H": 137.14, "I": 113.16,
    "L": 113.16, "K": 128.17, "M": 131.19, "F": 147.18, "P": 97.12,
    "S": 87.08, "T": 101.11, "W": 186.21, "Y": 163.18, "V": 99.13,
}
_HYDROPHOBIC = set("AVLIMFWCG")
_POLAR = set("STNQY")
_CHARGED_POS = set("KRH")
_CHARGED_NEG = set("DE")


def analyze(sequence: str) -> dict:
    seq = "".join(sequence.strip().upper().split())
    seq = "".join(ch for ch in seq if ch.isalpha())
    if not seq:
        return {"ok": False, "error": "序列为空"}
    invalid = sorted({ch for ch in seq if ch not in _RESIDUE_MASS})
    if invalid:
        return {"ok": False, "error": f"包含非标准氨基酸字符: {','.join(invalid)}"}

    comp = Counter(seq)
    length = len(seq)
    mass = sum(_RESIDUE_MASS[ch] for ch in seq) + 18.015  # +H2O
    hydro = sum(1 for ch in seq if ch in _HYDROPHOBIC)
    polar = sum(1 for ch in seq if ch in _POLAR)
    pos = sum(1 for ch in seq if ch in _CHARGED_POS)
    neg = sum(1 for ch in seq if ch in _CHARGED_NEG)
    charge = pos - neg
    hydro_ratio = hydro / length

    composition = [
        {"aa": aa, "count": c, "ratio": round(c / length, 3)}
        for aa, c in comp.most_common()
    ]

    notes: list[str] = []
    if hydro_ratio > 0.45:
        notes.append("疏水残基占比较高，可能形成疏水核心或跨膜区。")
    else:
        notes.append("亲水性较好，更可能分布于胞外或水溶性结构域。")
    if any(aa in comp for aa in ("W", "F", "Y")):
        notes.append("含芳香族残基，可能参与配体结合或信号转导。")
    if pos and neg and abs(charge) <= 2:
        notes.append("正负电荷较平衡，等电点附近稳定性较好。")
    elif charge > 2:
        notes.append(f"净正电荷较高（+{charge}），偏碱性。")
    elif charge < -2:
        notes.append(f"净负电荷较高（{charge}），偏酸性。")
    if length < 50:
        notes.append("序列较短，可能为肽段或活性片段。")
    elif length > 400:
        notes.append("序列较长，可能为完整结构域或多结构域蛋白。")

    return {
        "ok": True,
        "length": length,
        "molecular_weight": round(mass, 2),
        "charge": charge,
        "hydrophobic_ratio": round(hydro_ratio, 3),
        "polar_ratio": round(polar / length, 3),
        "composition": composition,
        "ai_notes": notes,
    }
