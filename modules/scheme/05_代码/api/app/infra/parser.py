"""参考文档解析（doc/docx/pdf/md -> Markdown）。

对标 OpenBidKit 的 doc2markdown/convert.mjs：统一输出保留 # 标题层级的 Markdown，
作为切片与知识库构建的输入（见 11_本地知识库建设方案 §3）。
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def parse_file(path: str, source_type: str | None = None) -> str:
    suffix = (source_type or Path(path).suffix.lstrip(".")).lower()
    if suffix in ("md", "markdown", "txt"):
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    if suffix in ("docx",):
        return _parse_docx(path)
    if suffix in ("pdf",):
        return _parse_pdf(path)
    # 默认按纯文本
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def _parse_docx(path: str) -> str:
    doc = DocxDocument(path)
    lines: list[str] = []

    def _emit(text: str, level: int | None = None):
        text = text.strip()
        if not text:
            return
        if level:
            lines.append("#" * min(level, 6) + " " + text)
        else:
            lines.append(text)

    for para in doc.paragraphs:
        style = (para.style.name if para.style else "") or ""
        m = re.match(r"Heading\s+(\d+)", style, re.IGNORECASE)
        if m:
            _emit(para.text, int(m.group(1)))
        elif style.lower() == "title":
            _emit(para.text, 1)
        else:
            _emit(para.text)

    # 表格：转为 Markdown 表格
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")  # 表后空行

    return "\n\n".join(lines).strip()


def _parse_pdf(path: str) -> str:
    reader = PdfReader(path)
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def checksum_text(text: str) -> str:
    """简单去重校验和（sha256 前缀）。"""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
