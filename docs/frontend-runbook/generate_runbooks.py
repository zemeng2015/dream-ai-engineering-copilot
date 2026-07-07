# ruff: noqa: E501
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "annotation-manifest.json"
USER_DOC = ROOT / "USER_RUNBOOK.zh-CN.md"
DEV_DOC = ROOT / "DEVELOPER_RUNBOOK.zh-CN.md"
USER_HTML = ROOT / "USER_RUNBOOK.zh-CN.html"
DEV_HTML = ROOT / "DEVELOPER_RUNBOOK.zh-CN.html"
INDEX_DOC = ROOT / "README.md"


COMPONENTS = {
    "mission-control": "frontend/src/app/features/dashboard/dashboard.component.ts",
    "memory-hub": "frontend/src/app/features/memory-hub/memory-hub.component.ts",
    "engineering-workbench": "frontend/src/app/features/engineering-workbench/engineering-workbench.component.ts",
    "trust-center": "frontend/src/app/features/trust-center/trust-center.component.ts",
    "knowledge-memory": "frontend/src/app/features/knowledge-base/knowledge-base.component.ts",
    "knowledge-intake": "frontend/src/app/features/knowledge-intake/knowledge-intake.component.ts",
    "memory-atlas": "frontend/src/app/features/codebase-memory/codebase-memory.component.ts",
    "retrieval-paths": "frontend/src/app/features/evidence-graph/evidence-graph.component.ts",
    "context-intelligence": "frontend/src/app/features/context-intelligence/context-intelligence.component.ts",
    "requirement-case": "frontend/src/app/features/requirement-draft/requirement-draft.component.ts",
    "pr-review": "frontend/src/app/features/pr-review/pr-review.component.ts",
    "testgen-stub": "frontend/src/app/features/testgen-stub/testgen-stub.component.ts",
    "eval-audit": "frontend/src/app/features/audit-eval/audit-eval.component.ts",
    "settings": "frontend/src/app/features/settings/settings.component.ts",
}


ROUTE_GROUPS = [
    ("主导航页", ["mission-control", "memory-hub", "engineering-workbench", "trust-center", "settings"]),
    (
        "功能子页/可直达路由",
        [
            "knowledge-memory",
            "knowledge-intake",
            "memory-atlas",
            "retrieval-paths",
            "context-intelligence",
            "requirement-case",
            "pr-review",
            "testgen-stub",
            "eval-audit",
        ],
    ),
]


def rel(path_value: str) -> str:
    return Path(path_value).relative_to(ROOT).as_posix()


def escape_table(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("|", "\\|").replace("\n", "<br>")


def page_index(manifest: dict) -> str:
    rows = [
        "| 页面 | Route | 标题 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    for page in manifest["pages"]:
        rows.append(
            f"| [{page['title']}](#{page['slug']}) | `{page['route']}` | {page['browserTitle']} | {escape_table(page['purpose'])} |"
        )
    return "\n".join(rows)


def scope_note(manifest: dict) -> str:
    return f"""# DREAM Frontend Runbook

生成时间：`{manifest['generatedAt']}`

目标环境：`{manifest['baseUrl']}`

截图方式：`{manifest.get('captureMethod', 'Browser screenshot')}`

本 runbook 覆盖 Angular router 中的全部实际页面路由；`/` 和 `/dashboard` 会重定向到 `/mission-control`，`**` 也会回到 `/mission-control`，所以不单独截图。

安全边界：
- 当前 UI 以 mock/demo 数据为主，不包含真实公司数据、真实 Jira、真实 PR、真实日志或真实 repo 写入。
- Requirement Case 和 PR Review 默认使用 `Mock local provider`；只有切到 `Real FastAPI + OpenAI-compatible provider` 时才会调用后端 `127.0.0.1:8000`。
- PR Review 的 real mode 当前发送后端固定的 synthetic diff/Jira 路径，不是把页面 textarea 里的 diff/Jira 原文直接传给后端。
- Knowledge Intake、Eval Rating、TestGen Stub 的状态是前端 in-memory/demo 行为，不等于生产落库。
- Knowledge Intake 上传使用浏览器本地 `file.text()` 做 demo parse；不要把它当成可靠 DOCX/HTML/JSON 解析器，也不要上传真实敏感资料。
- TestGen Stub 不生成单元测试，也不写 repository。
"""


def user_doc(manifest: dict) -> str:
    lines = [
        scope_note(manifest),
        "## 页面索引",
        page_index(manifest),
        "",
        "## 使用方式",
        "看每张截图上的编号，再对照下面表格。每页的 `1` 和 `2` 通常是全局左侧导航和顶部栏；后续编号是该页面自己的功能区域。",
        "",
        "左侧导航只暴露 5 个顶层入口。其他功能页通过 Mission Control quick actions、Memory Hub tabs、Workbench mode、Trust Center tabs 或直接 route 进入；所以 runbook 按 Angular router 覆盖全部页面，而不是只按 sidebar 覆盖。",
        "",
        "`/memory`、`/workbench`、`/trust` 是容器页，截图展示默认嵌入态；它们嵌入的 Intake/Atlas/Trace/Evidence、Requirement/PR、Context/Audit 也都有独立 route 截图。",
        "",
    ]
    for group_title, slugs in ROUTE_GROUPS:
        lines.append(f"## {group_title}")
        for slug in slugs:
            page = next(item for item in manifest["pages"] if item["slug"] == slug)
            lines.extend(user_page_section(page))
    return "\n".join(lines).rstrip() + "\n"


def user_page_section(page: dict) -> list[str]:
    image = rel(page["annotatedScreenshot"])
    lines = [
        f"### {page['title']} {{#{page['slug']}}}",
        "",
        f"- Route：`{page['route']}`",
        f"- 页面目的：{page['purpose']}",
        "- 标注截图：",
        "",
        f"![{page['title']} annotated screenshot]({image})",
        "",
        "| 编号 | 区域 | 功能说明 | 使用目的/注意 |",
        "| --- | --- | --- | --- |",
    ]
    for box in page["screenshotInfo"]["boxes"]:
        lines.append(
            f"| {box['id']} | {escape_table(box.get('label'))} | {escape_table(box.get('user'))} | {user_note_for_box(box)} |"
        )
    lines.append("")
    return lines


def user_note_for_box(box: dict) -> str:
    label = box.get("label", "")
    user = box.get("user", "")
    if "Real FastAPI" in user or "OpenAI" in user:
        return "只有切到 real mode 才会走后端；默认 mock 不会产生外部模型调用。"
    if "Upload" in label:
        return "本地读取上传文件并生成 demo memory cards；需要人工 approve/promote。"
    if "Rating" in label or "Human Review" in label:
        return "这是人工门禁/反馈区，用来证明输出不能自动发布。"
    if "TestGen" in label or "Stub" in label:
        return "当前是接口演示，不会生成测试或写文件。"
    if box["id"] in (1, 2):
        return "全局 shell，跨页面一致。"
    return "用于产品校验时确认该区域是否真的支持目标用户流程。"


def dev_doc(manifest: dict) -> str:
    lines = [
        scope_note(manifest),
        "## 开发者总览",
        "",
        "- 前端框架：Angular 19 standalone components + Angular Router。",
        "- 路由定义：`frontend/src/app/app.routes.ts`。",
        "- 全局 shell：`frontend/src/app/app.component.html` / `app.component.ts`。",
        "- 主要数据源：`frontend/src/app/core/mock-dream.service.ts`。",
        "- Real provider API wrapper：`frontend/src/app/core/dream-api.service.ts`，当前只被 Requirement Case 和 PR Review 的 real mode 使用。",
            "- 截图标注来源：`docs/frontend-runbook/annotation-manifest.json`。",
            "",
            "## 容易误解的产品边界",
            "",
            "- 左侧 nav 只暴露 5 个顶层页面；`/knowledge`、`/knowledge-intake`、`/codebase`、`/graph`、`/context-intelligence`、`/requirements`、`/review`、`/testgen`、`/audit` 是可直达 route，但主要从容器页或 quick actions 进入。",
            "- `/memory`、`/workbench`、`/trust` 的截图是容器默认状态；内嵌功能页另有独立截图。不要把容器默认截图理解为所有 tab/mode 的唯一状态。",
            "- 顶部 `Toggle navigation` button 当前只是视觉按钮，没有展开/收起逻辑。",
            "- “Mock Data Mode ON”和 `openai` execution option 同屏出现会造成认知冲突：默认不调外部模型，切 real mode 才会调用 `http://127.0.0.1:8000`。",
            "- PR Review real mode 当前发送固定后端 synthetic files：`examples/pr-diffs/DFP-110-output-collector-idempotency.diff` 和 `knowledge_packs/demo_team/docs/historical-jira/DFP-110-output-collection-idempotency.md`。",
            "- Knowledge Intake upload 使用浏览器 `file.text()` 做本地 demo parse，不上传服务器；这不是生产级 parser，也不要喂真实敏感资料。",
            "- Markdown/JSON 产物是 UTF-8；Windows PowerShell 默认输出可能显示乱码，读写脚本应显式使用 UTF-8。",
            "",
            "## Route / Component Map",
            "",
            "| Route | 页面 | Component | 备注 |",
        "| --- | --- | --- | --- |",
    ]
    for page in manifest["pages"]:
        component = COMPONENTS.get(page["slug"], "")
        note = route_note(page["slug"])
        lines.append(f"| `{page['route']}` | {page['title']} | `{component}` | {note} |")
    lines.extend(
        [
            "| `/` | redirect | `app.routes.ts` | redirect 到 `/mission-control`。 |",
            "| `/dashboard` | redirect | `app.routes.ts` | 旧 dashboard alias，redirect 到 `/mission-control`。 |",
            "| `**` | redirect | `app.routes.ts` | 未知路径 redirect 到 `/mission-control`。 |",
            "",
            "## 关键实现边界",
            "",
            "- 左侧 nav 只暴露 5 个顶层页面；其余功能页通过 Hub/Workbench/Trust 内嵌入口、Dashboard quick actions 或直接 route 访问。",
            "- 顶部 `Toggle navigation` button 当前只有 UI button 和 aria-label，未绑定展开/收起状态。",
            "- Mock data 不是持久化存储；刷新页面会丢失 Knowledge Intake 上传、question answers、ratings 等运行时 signal 状态。",
            "- `sourceHref()` 指向 GitHub main 分支源码路径，适合 demo drill-down，不保证当前本地 working tree 完全一致。",
            "- Real OpenAI 模式依赖后端 `http://127.0.0.1:8000`，API key 只应在后端环境变量中配置，浏览器不读取 key。",
            "- PR Review real mode 不读取 textarea 里的 diff/Jira 原文，而是发送 `DreamApiService.reviewPrWithOpenAI()` 中固定的 demo 文件路径。",
            "- 所有生成输出仍是 draft/review aid：不发 Jira、不评论/批准 PR、不执行 TestGen、不写 repo。",
            "",
            "## 页面级说明",
            "",
        ]
    )
    for page in manifest["pages"]:
        lines.extend(dev_page_section(page))
    return "\n".join(lines).rstrip() + "\n"


def route_note(slug: str) -> str:
    if slug in {"requirement-case", "pr-review"}:
        return "可切 mock/real provider；real mode 调 FastAPI。"
    if slug in {"knowledge-intake", "eval-audit", "testgen-stub"}:
        return "本地 signal/mock state，无生产 side effect。"
    if slug in {"memory-hub", "engineering-workbench", "trust-center"}:
        return "容器页，内部嵌入多个 feature component。"
    return "mock/demo 数据展示或搜索。"


def dev_page_section(page: dict) -> list[str]:
    image = rel(page["annotatedScreenshot"])
    component = COMPONENTS.get(page["slug"], "")
    lines = [
        f"### {page['title']} {{#{page['slug']}-dev}}",
        "",
        f"- Route：`{page['route']}`",
        f"- Component：`{component}`",
        f"- 目的：{page['purpose']}",
        "",
        f"![{page['title']} annotated screenshot]({image})",
        "",
        "| 编号 | 区域 | 用户功能 | 实现/状态来源 | 开发注意 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for box in page["screenshotInfo"]["boxes"]:
        lines.append(
            f"| {box['id']} | {escape_table(box.get('label'))} | {escape_table(box.get('user'))} | {escape_table(box.get('dev'))} | {dev_note_for_box(page, box)} |"
        )
    lines.append("")
    return lines


def dev_note_for_box(page: dict, box: dict) -> str:
    label = box.get("label", "")
    dev = box.get("dev", "")
    if box["id"] == 1:
        return "跨页固定 shell；改 navItems 会影响所有截图/入口。"
    if box["id"] == 2:
        return "Toggle navigation 尚未实现行为；如做响应式菜单需补状态和测试。"
    if "DreamApiService" in dev or "OpenAI" in dev or page["slug"] in {"requirement-case", "pr-review"} and "form" in dev.lower():
        return "real mode 错误处理要覆盖后端未启动、CORS、provider key 缺失。"
    if "signal" in dev:
        return "刷新会重置；生产化需接 API/持久化。"
    if "routerLink" in dev:
        return "导航无 side effect，适合 demo；真实 workflow 需补权限/状态保护。"
    if "TestGen" in label:
        return "保持 no repo writes，接 JTestGen 前需要单独权限门禁。"
    return "产品校验时确认 mock 行为和未来生产行为差异是否已说明。"


def index_doc(manifest: dict) -> str:
    return f"""# Frontend Runbook Artifacts

本目录是 DREAM Angular frontend 的逐页截图标注和使用说明。

## 文件

- `USER_RUNBOOK.zh-CN.md`：用户/产品校验版，解释每个编号区域的功能和目的。
- `DEVELOPER_RUNBOOK.zh-CN.md`：开发者版，解释 route、component、状态来源、事件和风险边界。
- `USER_RUNBOOK.zh-CN.html`：本地浏览器打开版，图片路径按 HTML 文件位置解析。
- `DEVELOPER_RUNBOOK.zh-CN.html`：开发者本地浏览器打开版。
- `annotation-manifest.json`：截图、编号、选择器、说明文字的结构化来源。
- `raw-screenshots/`：未标注截图。
- `annotated-screenshots/`：带编号框截图。
- `capture_screenshots_cdp.mjs`：用本地 Chrome CDP 重采截图。
- `annotate_screenshots.py`：根据 manifest 给截图画编号框。
- `generate_runbooks.py`：根据 manifest 生成两版 runbook。

如果本地打开 `.md` 看不到截图，直接打开同名 `.html` 文件。某些 Markdown 查看器会把相对图片路径按 workspace 根目录解析，而不是按 `.md` 文件所在目录解析。

## 覆盖范围

共覆盖 `{len(manifest['pages'])}` 个实际页面路由；`/`、`/dashboard` 和 `**` 是 redirect，不单独截图。

重新生成顺序：

```bash
node docs/frontend-runbook/capture_screenshots_cdp.mjs
python docs/frontend-runbook/annotate_screenshots.py
python docs/frontend-runbook/generate_runbooks.py
```
"""


def html_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #10233f;
      --muted: #52657f;
      --line: #dbe6f3;
      --panel: #ffffff;
      --bg: #f4f8fb;
      --accent: #007f86;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 24px 64px;
    }}
    h1, h2, h3 {{
      line-height: 1.2;
      margin: 28px 0 12px;
    }}
    h1 {{
      font-size: 34px;
    }}
    h2 {{
      border-top: 1px solid var(--line);
      padding-top: 24px;
    }}
    p, li {{
      color: var(--muted);
    }}
    code {{
      background: #eaf2fb;
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 1px 5px;
    }}
    .callout {{
      background: #e9fbfb;
      border: 1px solid #b9e4e5;
      border-left: 5px solid var(--accent);
      border-radius: 8px;
      padding: 14px 16px;
      margin: 16px 0;
    }}
    .page {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      margin: 28px 0;
      padding: 20px;
      box-shadow: 0 8px 24px rgba(16, 35, 63, 0.06);
    }}
    .screenshot {{
      width: 100%;
      max-width: 1100px;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: block;
      margin: 14px 0 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 24px;
      background: white;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #eef5fb;
    }}
    .muted {{
      color: var(--muted);
    }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def html_page_index(manifest: dict) -> str:
    rows = []
    for page in manifest["pages"]:
        rows.append(
            "<tr>"
            f"<td><a href=\"#{escape(page['slug'])}\">{escape(page['title'])}</a></td>"
            f"<td><code>{escape(page['route'])}</code></td>"
            f"<td>{escape(page['browserTitle'])}</td>"
            f"<td>{escape(page['purpose'])}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>页面</th><th>Route</th><th>标题</th><th>说明</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def html_user_doc(manifest: dict) -> str:
    parts = [
        "<h1>DREAM Frontend Runbook</h1>",
        f"<p>生成时间：<code>{escape(manifest['generatedAt'])}</code></p>",
        f"<p>目标环境：<code>{escape(manifest['baseUrl'])}</code></p>",
        "<div class=\"callout\">本 HTML 是本地浏览器打开版；图片路径按 HTML 文件所在目录解析。"
        "如果 Markdown 预览看不到图，请打开这个 HTML。</div>",
        "<h2>安全边界</h2>",
        "<ul>"
        "<li>当前 UI 以 mock/demo 数据为主，不包含真实公司数据、真实 Jira、真实 PR、真实日志或真实 repo 写入。</li>"
        "<li>Requirement Case 和 PR Review 默认使用 Mock local provider；切 real mode 才会调用后端 127.0.0.1:8000。</li>"
        "<li>PR Review real mode 当前发送后端固定 synthetic diff/Jira 路径，不直接发送页面 textarea 原文。</li>"
        "<li>Knowledge Intake、Eval Rating、TestGen Stub 是前端 in-memory/demo 行为，不等于生产落库。</li>"
        "</ul>",
        "<h2>页面索引</h2>",
        html_page_index(manifest),
    ]
    for page in manifest["pages"]:
        parts.append(html_user_page(page))
    return html_shell("DREAM Frontend Runbook - User", "\n".join(parts))


def html_user_page(page: dict) -> str:
    rows = []
    for box in page["screenshotInfo"]["boxes"]:
        rows.append(
            "<tr>"
            f"<td>{box['id']}</td>"
            f"<td>{escape(box.get('label') or '')}</td>"
            f"<td>{escape(box.get('user') or '')}</td>"
            f"<td>{escape(user_note_for_box(box))}</td>"
            "</tr>"
        )
    return f"""
<section class="page" id="{escape(page['slug'])}">
  <h2>{escape(page['title'])}</h2>
  <p>Route：<code>{escape(page['route'])}</code></p>
  <p>{escape(page['purpose'])}</p>
  <img class="screenshot" src="{escape(rel(page['annotatedScreenshot']))}" alt="{escape(page['title'])} annotated screenshot">
  <table>
    <thead><tr><th>编号</th><th>区域</th><th>功能说明</th><th>使用目的/注意</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def html_dev_doc(manifest: dict) -> str:
    route_rows = []
    for page in manifest["pages"]:
        component = COMPONENTS.get(page["slug"], "")
        route_rows.append(
            "<tr>"
            f"<td><code>{escape(page['route'])}</code></td>"
            f"<td>{escape(page['title'])}</td>"
            f"<td><code>{escape(component)}</code></td>"
            f"<td>{escape(route_note(page['slug']))}</td>"
            "</tr>"
        )
    parts = [
        "<h1>DREAM Frontend Developer Runbook</h1>",
        f"<p>生成时间：<code>{escape(manifest['generatedAt'])}</code></p>",
        "<div class=\"callout\">本 HTML 是本地浏览器打开版；图片路径按 HTML 文件所在目录解析。</div>",
        "<h2>Route / Component Map</h2>",
        "<table><thead><tr><th>Route</th><th>页面</th><th>Component</th><th>备注</th></tr></thead>"
        f"<tbody>{''.join(route_rows)}</tbody></table>",
        "<h2>关键实现边界</h2>",
        "<ul>"
        "<li>左侧 nav 只暴露 5 个顶层页面；其余功能页通过容器页、quick actions 或直接 route 访问。</li>"
        "<li>顶部 Toggle navigation button 当前只有 UI button 和 aria-label，未绑定展开/收起状态。</li>"
        "<li>Mock data 不是持久化存储；刷新页面会丢失 upload、question answers、ratings 等运行时 signal 状态。</li>"
        "<li>Real OpenAI 模式依赖后端 http://127.0.0.1:8000，API key 只应在后端环境变量中配置。</li>"
        "</ul>",
    ]
    for page in manifest["pages"]:
        parts.append(html_dev_page(page))
    return html_shell("DREAM Frontend Runbook - Developer", "\n".join(parts))


def html_dev_page(page: dict) -> str:
    rows = []
    for box in page["screenshotInfo"]["boxes"]:
        rows.append(
            "<tr>"
            f"<td>{box['id']}</td>"
            f"<td>{escape(box.get('label') or '')}</td>"
            f"<td>{escape(box.get('user') or '')}</td>"
            f"<td>{escape(box.get('dev') or '')}</td>"
            f"<td>{escape(dev_note_for_box(page, box))}</td>"
            "</tr>"
        )
    component = COMPONENTS.get(page["slug"], "")
    return f"""
<section class="page" id="{escape(page['slug'])}">
  <h2>{escape(page['title'])}</h2>
  <p>Route：<code>{escape(page['route'])}</code></p>
  <p>Component：<code>{escape(component)}</code></p>
  <p>{escape(page['purpose'])}</p>
  <img class="screenshot" src="{escape(rel(page['annotatedScreenshot']))}" alt="{escape(page['title'])} annotated screenshot">
  <table>
    <thead><tr><th>编号</th><th>区域</th><th>用户功能</th><th>实现/状态来源</th><th>开发注意</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    USER_DOC.write_text(user_doc(manifest), encoding="utf-8")
    DEV_DOC.write_text(dev_doc(manifest), encoding="utf-8")
    USER_HTML.write_text(html_user_doc(manifest), encoding="utf-8")
    DEV_HTML.write_text(html_dev_doc(manifest), encoding="utf-8")
    INDEX_DOC.write_text(index_doc(manifest), encoding="utf-8")


if __name__ == "__main__":
    main()
