# Frontend Runbook Artifacts

本目录是 DREAM Angular frontend 的逐页截图标注和使用说明。

> Current status: these artifacts were generated before the latest live FastAPI
> UI simplification. They are useful as historical reference, but must be
> regenerated before being used for product acceptance. The current primary
> routes are `/mission-control`, `/memory`, `/workbench`, `/requirements`,
> `/review`, `/codebase`, `/audit`, and `/audit/:targetId`.

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

旧版产物覆盖 `14` 个历史页面路由；`/`、`/dashboard` 和 `**` 是 redirect，不单独截图。
当前 UI 已合并/移除多个 mock 页面，重新生成时应以 `docs/frontend-angular.md`
记录的当前路由为准。

重新生成顺序：

```bash
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
npm start --prefix frontend -- --host 127.0.0.1 --port 4300
node docs/frontend-runbook/capture_screenshots_cdp.mjs
python docs/frontend-runbook/annotate_screenshots.py
python docs/frontend-runbook/generate_runbooks.py
```
