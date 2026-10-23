"""AI 方案生成 · 内核冒烟测试（RAG 检索 / 导出），无需 fastapi 与数据库。

用法：
    python backend/scripts/smoke_scheme.py
"""
import importlib.util
import io
import os
import xml.etree.ElementTree as ET
import zipfile

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "app", "modules", "scheme")

passed = failed = 0


def ok(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print("  ✓", name)
    else:
        failed += 1
        print("  ✗", name, extra)


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BASE, fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


retrieval = load("scheme_retrieval", "retrieval.py")
export = load("scheme_export", "export.py")
prompts = load("scheme_prompts", "prompts.py")

print("== 分词 / 检索 ==")
toks = retrieval.tokenize("为中小企业搭建 AI 客服助手")
ok("分词含 ASCII 词 ai", "ai" in toks)
ok("分词含中文词 客服", "客服" in toks)
ok("分词含 bigram 助手", "助手" in toks)

templates = [
    {"id": "t1", "name": "AI 客服助手产品方案", "category": "产品方案",
     "description": "面向企业的智能客服搭建方案", "tags": ["客服", "AI", "对话"],
     "sections": [{"title": "需求分析", "hint": "客服现状与痛点"}, {"title": "技术架构"}]},
    {"id": "t2", "name": "数据中心迁移实施方案", "category": "实施方案",
     "description": "机房搬迁与数据迁移", "tags": ["迁移"], "sections": [{"title": "迁移步骤"}]},
    {"id": "t3", "name": "员工培训方案", "category": "培训方案",
     "description": "新员工入职培训", "tags": ["培训"], "sections": [{"title": "课程安排"}]},
]
cases = [
    {"id": "c1", "title": "某银行智能客服升级案例", "industry": "金融", "category": "产品方案",
     "summary": "为银行搭建 AI 客服，接入知识库，提升响应效率", "content": "响应时间下降 40%", "quality": 5},
    {"id": "c2", "title": "制造业数据中台迁移", "industry": "制造", "category": "实施方案",
     "summary": "数据中台整体迁移", "content": "停机窗口 4 小时", "quality": 4},
]
res = retrieval.retrieve("为中小企业搭建 AI 客服助手，提升响应效率", templates, cases, 3, 2)
ok("命中模板 Top1 为客服方案", res["templates"][0]["id"] == "t1")
ok("模板得分已归一化=1.0", res["templates"][0]["score"] == 1.0)
ok("模板带章节标题", "需求分析" in (res["templates"][0]["sections"] or []))
ok("命中案例 Top1 为客服案例", res["cases"][0]["id"] == "c1")
ok("案例带摘要片段", len(res["cases"][0]["excerpt"]) > 0)
ok("无关案例未进 Top1", res["cases"][0]["id"] != "c2")

print("== 提示词构建 ==")
msgs = prompts.build_generation_messages(
    {"goal": "搭建 AI 客服", "audience": "中小企业"}, templates[0],
    [{"title": "某银行客服升级", "industry": "金融", "excerpt": "转接率 62%→28%"}], "专业正式", "标准")
ok("生成 system+user 两条", len(msgs) == 2 and msgs[0]["role"] == "system")
u = msgs[1]["content"]
ok("提示词含模板章节", "需求分析（客服现状与痛点）" in u)
ok("提示词含案例参考", "某银行客服升级" in u)
ok("提示词含素材", "搭建 AI 客服" in u)
ok("提示词含输出约束", "待确认" in u)
ok("无模板时兜底骨架", "通用商务方案骨架" in prompts.build_generation_messages({}, None, [], "x", "y")[1]["content"])

print("== 导出：docx ==")
md = ("# 项目背景\n\n这是**加粗**与`代码`行内样式。\n\n- 要点一\n- 要点二\n\n> 引用说明\n\n"
      "1. 第一步\n2. 第二步\n\n| 列A | 列B |\n| --- | --- |\n| 1 | 2 |\n")
data = export.markdown_to_docx(md, "测试方案")
ok("docx 非空字节", isinstance(data, (bytes, bytearray)) and len(data) > 800, str(len(data)))
z = zipfile.ZipFile(io.BytesIO(data))
need = {"[Content_Types].xml", "_rels/.rels", "word/document.xml",
        "word/_rels/document.xml.rels", "word/styles.xml", "docProps/core.xml", "docProps/app.xml"}
ok("docx 含全部必需部件", need.issubset(set(z.namelist())))
allok = True
for part in need:
    try:
        ET.fromstring(z.read(part))
    except Exception as e:  # noqa: BLE001
        allok = False
        ok(f"{part} XML 合法", False, str(e))
ok("全部部件 XML 合法", allok)
doc = z.read("word/document.xml").decode("utf-8")
ok("docx 含标题文字", "项目背景" in doc)
ok("docx 含加粗标记", "<w:b/>" in doc)
ok("docx 用 Heading1 样式", 'w:val="Heading1"' in doc)

print("== 导出：html / md / word ==")
html = export.markdown_to_html(md, "测试方案")
ok("html 含 <h1>", "<h1>项目背景</h1>" in html)
ok("html 含 <strong>", "<strong>加粗</strong>" in html)
ok("html 含 blockquote", "<blockquote>" in html)
for fmt, ext, media_part in [("md", "md", "text/markdown"), ("word", "docx", "wordprocessingml"), ("html", "html", "text/html")]:
    e, m, d = export.build_export(md, fmt, "测试方案")
    ok(f"build_export({fmt}) 正确", e == ext and media_part in m and len(d) > 0)

print(f"\n结果：{passed} 通过 / {failed} 失败")
raise SystemExit(1 if failed else 0)
