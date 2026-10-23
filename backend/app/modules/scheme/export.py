"""方案生成 · 导出内核（纯函数，无框架依赖，可独立测试）。

支持三种导出：
- Markdown（.md）：原样返回，附带 YAML 元信息头
- HTML（.html）：轻量 Markdown→HTML，内联样式便于直接分发/打印
- Word（.docx）：手工构建 OOXML 包（zipfile + XML），**不引入 python-docx 等新依赖**

docx 结构： [Content_Types].xml / _rels/.rels / word/document.xml /
            word/_rels/document.xml.rels / word/styles.xml / docProps/{core,app}.xml
"""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime, timezone
from html import escape as h_escape
from xml.sax.saxutils import escape as x_escape

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{ns}">
<w:docDefaults>
<w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Microsoft YaHei"/>
<w:sz w:val="21"/><w:szCs w:val="21"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="140" w:line="320" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>
<w:pPr><w:jc w:val="center"/><w:spacing w:after="280"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="44"/><w:color w:val="143A32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:before="320" w:after="140"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="0F6E56"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="26"/><w:color w:val="10796A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="23"/></w:rPr></w:style>
</w:styles>""".replace("{ns}", W_NS)

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>Baize AI Scheme Generator</Application>
</Properties>"""


def _core_xml(title: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{x_escape(title)}</dc:title>"
        "<dc:creator>白泽 AI 方案生成</dc:creator>"
        '<cp:lastModifiedBy>白泽 AI 方案生成</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


# --------------------------- 行内样式解析 --------------------------- #
_INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def _runs(text: str) -> list[tuple[str, bool, bool, bool]]:
    """把行内 Markdown 拆成 (text, bold, italic, code) 片段。"""
    out: list[tuple[str, bool, bool, bool]] = []
    for part in _INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            out.append((part[2:-2], True, False, False))
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            out.append((part[1:-1], False, False, True))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            out.append((part[1:-1], False, True, False))
        else:
            out.append((part, False, False, False))
    return out


def _xruns(text: str) -> str:
    xml = ""
    for t, b, i, code in _runs(text):
        rpr = ""
        if b or i or code:
            rpr = "<w:rPr>"
            if b:
                rpr += "<w:b/>"
            if i:
                rpr += "<w:i/>"
            if code:
                rpr += '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:shd w:val="clear" w:fill="F1F5F9"/>'
            rpr += "</w:rPr>"
        xml += f'<w:r>{rpr}<w:t xml:space="preserve">{x_escape(t)}</w:t></w:r>'
    return xml or '<w:r><w:t xml:space="preserve"></w:t></w:r>'


def _para(text: str, style: str | None = None, indent: int = 0, bold_all: bool = False) -> str:
    ppr = "<w:pPr>"
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if indent:
        ppr += f'<w:ind w:left="{indent}"/>'
    ppr += "</w:pPr>"
    if bold_all:
        body = "".join(
            f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{x_escape(t)}</w:t></w:r>'
            for t, _b, _i, _c in _runs(text)
        ) or '<w:r><w:t xml:space="preserve"></w:t></w:r>'
    else:
        body = _xruns(text)
    return f"<w:p>{ppr}{body}</w:p>"


def markdown_to_document_xml(md: str, title: str = "") -> str:
    """把 Markdown 转成 WordprocessingML 文档体。"""
    paras: list[str] = []
    if title:
        paras.append(_para(title, style="Title"))

    lines = (md or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_code = False
    code_buf: list[str] = []

    def flush_code() -> None:
        nonlocal code_buf
        if code_buf:
            for cl in code_buf:
                paras.append(_para(cl if cl else " ", indent=360, bold_all=False))
            code_buf = []

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            paras.append("<w:p/>")
            continue
        # 分隔线
        if re.fullmatch(r"[-*_]{3,}", stripped):
            continue
        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            style = "Heading1" if level == 1 else "Heading2" if level == 2 else "Heading3"
            paras.append(_para(m.group(2), style=style))
            continue
        # 引用
        if stripped.startswith(">"):
            paras.append(_para(stripped.lstrip("> ").strip(), indent=360))
            continue
        # 表格：分隔行跳过，其余按单元格拼接
        if stripped.startswith("|"):
            if re.fullmatch(r"\|[\s:|-]+\|", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            paras.append(_para(" ｜ ".join(cells), indent=240))
            continue
        # 无序列表
        m = re.match(r"^([-*+])\s+(.*)$", stripped)
        if m:
            paras.append(_para("• " + m.group(2), indent=360))
            continue
        # 有序列表
        m = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if m:
            paras.append(_para(f"{m.group(1)}. {m.group(2)}", indent=360))
            continue
        # 普通段落
        paras.append(_para(stripped))

    flush_code()
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>'
        + "".join(paras)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>"
    )


def markdown_to_docx(md: str, title: str = "") -> bytes:
    """生成合法的 .docx 字节流。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT_XML)
        z.writestr("_rels/.rels", RELS_XML)
        z.writestr("word/document.xml", markdown_to_document_xml(md, title))
        z.writestr("word/_rels/document.xml.rels", DOC_RELS_XML)
        z.writestr("word/styles.xml", STYLES_XML)
        z.writestr("docProps/core.xml", _core_xml(title or "方案"))
        z.writestr("docProps/app.xml", APP_XML)
    return buf.getvalue()


# ------------------------------- HTML ------------------------------- #
def markdown_to_html(md: str, title: str = "") -> str:
    """轻量 Markdown→HTML（标题/列表/引用/代码/粗斜体/表格分隔），带内联样式。"""
    body: list[str] = []
    lines = (md or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_code = False
    code_buf: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            body.append("</ul>")
            in_ul = False
        if in_ol:
            body.append("</ol>")
            in_ol = False

    def inline(s: str) -> str:
        s = h_escape(s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        return s

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                body.append("<pre><code>" + h_escape("\n".join(code_buf)) + "</code></pre>")
                code_buf = []
                in_code = False
            else:
                close_lists()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue
        st = line.strip()
        if not st:
            close_lists()
            continue
        if re.fullmatch(r"[-*_]{3,}", st):
            close_lists()
            body.append("<hr/>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            close_lists()
            lv = len(m.group(1))
            body.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            continue
        if st.startswith(">"):
            close_lists()
            body.append("<blockquote>" + inline(st.lstrip("> ").strip()) + "</blockquote>")
            continue
        if st.startswith("|"):
            if re.fullmatch(r"\|[\s:|-]+\|", st):
                continue
            cells = [c.strip() for c in st.strip("|").split("|")]
            close_lists()
            body.append("<p class='tbl'>" + " ｜ ".join(inline(c) for c in cells) + "</p>")
            continue
        m = re.match(r"^[-*+]\s+(.*)$", st)
        if m:
            if not in_ul:
                close_lists()
                body.append("<ul>")
                in_ul = True
            body.append("<li>" + inline(m.group(1)) + "</li>")
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)$", st)
        if m:
            if not in_ol:
                close_lists()
                body.append("<ol>")
                in_ol = True
            body.append("<li>" + inline(m.group(2)) + "</li>")
            continue
        close_lists()
        body.append("<p>" + inline(st) + "</p>")

    if in_code and code_buf:
        body.append("<pre><code>" + h_escape("\n".join(code_buf)) + "</code></pre>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>{h_escape(title or '方案')}</title>
<style>
body{{max-width:820px;margin:40px auto;padding:0 24px;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
color:#143a32;line-height:1.8;font-size:15px}}
h1{{font-size:26px;border-bottom:2px solid #10b981;padding-bottom:8px}}
h2{{font-size:20px;color:#0f6e56;margin-top:28px}}
h3{{font-size:17px}}
blockquote{{margin:12px 0;padding:8px 14px;border-left:3px solid #34d399;background:#f0fdf7;color:#4f7268}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:13px}}
pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;overflow:auto}}
hr{{border:none;border-top:1px dashed #cbd5e1;margin:22px 0}}
.tbl{{font-size:13px;color:#4f7268;background:#f8fafc;padding:6px 10px;border-radius:6px}}
li{{margin:4px 0}}
</style></head><body>
{''.join(body)}
</body></html>"""


# ------------------------------ 统一入口 ------------------------------ #
FMT_META = {
    "md": ("md", "text/markdown; charset=utf-8"),
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "html": ("html", "text/html; charset=utf-8"),
    "docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "word": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
}


def build_export(content_md: str, fmt: str, title: str = "") -> tuple[str, str, bytes]:
    """返回 (扩展名, media_type, 字节内容)。fmt 支持 md/markdown/html/docx/word。"""
    f = (fmt or "md").lower()
    ext, media = FMT_META.get(f, FMT_META["md"])
    if ext == "docx":
        return ext, media, markdown_to_docx(content_md, title)
    if ext == "html":
        return ext, media, markdown_to_html(content_md, title).encode("utf-8")
    header = ""
    if title:
        header = f"<!-- {title} · 由白泽 AI 方案生成导出 · {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n\n"
    return ext, media, (header + (content_md or "")).encode("utf-8")
