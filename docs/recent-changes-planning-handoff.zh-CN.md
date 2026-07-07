<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM 近期改动与规划交接

最后更新：2026-07-06。

这份文档用于产品规划和新对话交接。它记录当前分支状态、近期 UI/后端改动，以及最重要的 raw doc 到 structured memory 实现链路。

## 当前状态一句话

DREAM 已经从“多页面 mock 展示”收缩为“FastAPI 真实后端支撑的工程记忆工作台”。当前核心闭环是：

```text
Source docs + codebase index
  -> Memory Hub / Codebase Index
  -> Jira Draft 或 PR Review
  -> Eval Agent strict review
  -> Audit & Eval detail
```

当前工作分支：

```text
codex/memory-hub-density-cleanup
```

当前远端 commit：

```text
5ea19cd Simplify live workflow UI and docs
```

## 本地运行

后端：

```powershell
uvicorn dream.api.app:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
npm start --prefix frontend -- --host 127.0.0.1 --port 4300
```

入口：

```text
http://localhost:4300
```

## 当前主页面

- `/mission-control`：首页，只做总览和主要入口，不再承载详细 memory 管理。
- `/memory`：Memory Hub，管理 source intake、memory claim review 和 codebase index 三个 memory 区域。
- `/memory/:documentId`：单个 source document 的详情页，可查看 raw source、structured draft、span/hash provenance、review/promote 状态、intake audit events 和 downstream usage；downstream usage 会显示 matched paths、match reason、source hash/span/section match proof 和可推断的 Audit 跳转。
- `/workbench`：工程工作台入口。
- `/requirements`：Jira draft 工作流入口。
- `/review`：PR review 工作流入口。
- `/context/:caseId`：真实 Context Trail 详情页，调用 FastAPI context trail/context pack/prompt-preview API，展示检索步骤、selected evidence、context pack 分组、prompt preview、why selected reason，并在匹配 intake document 时回链 `/memory/:documentId`。
- `/codebase`：Repo Browser & Index JSON，查看真实 repo 文件和保存的 code index JSON。
- `/audit`：Eval Agent 总览，一页显示有限 case，支持分页。
- `/audit/:targetId`：单个 eval case 的详情页。

已废弃或合并的旧页面通过路由 redirect 到主页面：

- `/knowledge-intake` -> `/memory`
- `/knowledge` -> `/memory`
- `/graph` -> `/codebase`
- `/trust` -> `/audit`
- `/context-intelligence` -> `/audit`
- `/testgen` -> `/workbench`
- `/settings` -> `/mission-control`

## 近期主要改动

### UI 信息架构

- Mission Control 被压缩成业务总览：work queue、source memory 数量、Jira/PR/eval 待处理状态和主要启动入口。
- Memory Hub 不再和首页重复，改成 memory 管理页。
- Memory Hub 内部改为 tab：
  - Source Intake：注册、解析、审批、promote 文档。
  - Claim Review：读取 latest memory scan + memory diff/conflicts/conflict-resolutions/ledger，运行 memory scan，审查 claims（diff 只作为 added/changed 标记，不隐藏 unchanged candidates），显示 active single-value conflict pairs、intake_proofs 和 raw trace，可用 `approve_winner_reject_other` 处理冲突，并把 approve/reject/quarantine 写回 durable ledger；最新 review 会显示 reviewer signature、字段级 diff、claim snapshot 摘要，以及带 reviewer-readable explanation/evidence 的 risk/conflict signals。
  - Codebase Index：展示 repo index 数量和跳转到 Codebase Index。
- 旧的 Knowledge Intake mock 页面不再作为独立产品入口。
- Workbench 里 Jira Draft 和 PR Review 入口被简化为可执行工作流，而不是大面积解释性内容。
- Audit & Eval 做了 case-by-case detail route，生成工作流里出现 eval 结果时可以跳转到具体判定详情。

### 视觉方向

- 全局方向是更浅、更清晰的 enterprise finance 风格。
- Sidebar 和 topbar 采用两种蓝色，避免旧版过深、过重。
- 复杂解释收缩到详情、折叠区或 detail route，不在首屏全部铺开。
- 列表里优先显示文件名、状态、用途；完整路径放在 hover/detail 里。

### Codebase Index

- `/codebase` 被重构为更接近 GitHub/AWS 的 repo browser。
- 页面展示真实 repo 文件、选中文件代码预览、selected file 的 JSON index record。
- 完整 repo index JSON 不再作为主要阅读内容，只作为折叠或辅助检查对象。
- 产品语义：这里不是 review 页面，而是“真实 repo 文件 + 保存的 graph/index JSON 证据浏览器”。

### Eval Agent

- `/audit` 总览页不再把长段 rationale 全部铺开。
- `/audit/:targetId` 支持单个 eval case 的详情。
- Eval card 和 Audit Runs 都需要分页，当前前端已经有分页基础。
- Audit & Eval 的 selected-run source chips 会在匹配 intake document 时反向链接到 `/memory/:documentId`。
- Source paths 在详情里应尽量显示文件名，完整路径放 hover 或详情。

### 后端真实连接

- 前端主要工作流已改为调用 FastAPI，而不是只读 mock state。
- Requirement Draft：
  - 创建 requirement case。
  - analyze。
  - 生成 Jira draft。
  - strict eval。
  - 链接到 `/audit/:evaluationId`。
  - source rows 在匹配 intake document 时反向链接到 `/memory/:documentId`。
- PR Review：
  - 提交 diff 和 Jira context。
  - 调用 `/review/pr`。
  - strict eval。
  - 链接到 `/audit/:evaluationId`。
  - source rows 在匹配 intake document 时反向链接到 `/memory/:documentId`。
- Memory Hub：
  - 调用 `/intake/documents`。
  - 调用 `/intake/documents/upload` 做 browser multipart 文件上传。
  - 调用 draft metadata API，在 promote 前可修改 title、doc_type、app、component、concepts，并写入包含 field diff / metadata snapshot / audit run id 的 draft review event。
  - 调用 `/memory/diff`、`/memory/conflicts`、`/memory/conflicts/resolve`、`/memory/conflict-resolutions`、`/memory/ledger`、`/memory/scan`、`/memory/review` 做 governed memory claim review。
  - source document 记录 `source_hash`，parse 后每个 section 记录 `source_span` 和 `section_hash`。
  - 同 team 重复导入相同内容时不阻断，但会给 duplicate-content warning。
  - `/memory/:documentId` 调用 detail API，展示 raw source preview、structured Markdown、section span/hash、review/promote 状态、intake audit events 和 downstream usage。
  - downstream usage 已从裸 audit record 升级为结构化记录：`audit_record`、`matched_source_paths`、`match_reason`、`detail_route`、`match_proofs`。
  - `match_proofs` 会记录 retrieved source path、matched candidate path/label、document/draft id、source hash verified 状态，以及 parsed section span/hash proof。
  - 调用 parse/review/promote API。
- Codebase Index：
  - 调用 `/codebase/index`、`/codebase/files`、`/codebase/file-content`、`/codebase/search`。

## Raw Doc 到 Structured Memory

这是当前最重要的实现链路。

### 产品视角

用户在 `/memory` 的 Source Intake tab 中选择浏览器本地文件，或输入后端可访问的本地文件路径，例如：

```text
examples/intake-samples/runbook-output-reconciliation.md
```

然后依次执行：

```text
Register Source
  -> Parse
  -> Edit Metadata
  -> Approve
  -> Promote
  -> Structured Docs in Memory
```

promoted 后，该文档会成为 knowledge pack 里的 Markdown 文件，后续 requirement、PR review、eval 等 workflow 可以通过 knowledge retriever 检索到。

### 状态机

当前状态非常简单：

```text
uploaded
  -> parsed
  -> approved
  -> promoted
```

状态含义：

- `uploaded`：后端已经复制原始文件，并创建 intake document record。
- `parsed`：后端已经把 raw doc 解析成 KnowledgeDraft，包括 sections、concepts 和 normalized Markdown。
- `approved`：人工 reviewer 通过 review endpoint 批准 draft。
- `promoted`：后端把 normalized Markdown 写入 `knowledge_packs/<team>/docs/<document_type>/`，使它成为 durable knowledge pack 文档。

### 后端代码路径

核心实现文件：

- `dream/intake/models.py`
- `dream/intake/parsers.py`
- `dream/intake/repository.py`
- `dream/intake/service.py`
- `dream/api/routes.py`
- `dream/knowledge/markdown_loader.py`
- `dream/knowledge/chunker.py`
- `dream/knowledge/retriever.py`

关键服务：

```python
KnowledgeIntakeService.upload_local_file(...)
KnowledgeIntakeService.upload_file_content(...)
KnowledgeIntakeService.parse_document(...)
KnowledgeIntakeService.get_document_detail(...)
KnowledgeIntakeService.update_draft_metadata(...)
KnowledgeIntakeService.review_draft(...)
KnowledgeIntakeService.promote_draft(...)
```

### API 链路

```text
POST /intake/documents
POST /intake/documents/upload
GET  /intake/documents
GET  /intake/documents/{document_id}
GET  /intake/documents/{document_id}/detail
POST /intake/documents/{document_id}/parse
GET  /intake/drafts/{draft_id}
PATCH /intake/drafts/{draft_id}/metadata
GET /intake/drafts/{draft_id}/review-events
POST /intake/drafts/{draft_id}/review
POST /intake/drafts/{draft_id}/promote
```

前端映射：

- `DreamApiService.uploadIntakeDocument(...)`
- `DreamApiService.uploadIntakeFile(...)`
- `DreamApiService.getIntakeDocumentDetail(...)`
- `DreamApiService.getIntakeDraft(...)`
- `DreamApiService.updateIntakeDraftMetadata(...)`
- `DreamApiService.parseIntakeDocument(documentId)`
- `DreamApiService.approveIntakeDocument(documentId)`
- `DreamApiService.promoteIntakeDocument(documentId)`
- `MemoryHubComponent.runSourceAction(...)`
- `MemoryDocumentDetailComponent`

注意：当前前端 approve/promote 依赖 draft id 格式为 `draft-${documentId}`，这和当前后端实现一致。

### CLI 链路

```bash
dream intake upload \
  --team demo_team \
  --file examples/intake-samples/runbook-output-reconciliation.md \
  --type runbooks \
  --title "Output Reconciliation Intake Demo"

dream intake list
dream intake parse --document <document_id>

dream intake review \
  --draft <draft_id> \
  --status approved \
  --reviewer demo.lead \
  --reason "Synthetic runbook matches DemoCorp recovery policy."

dream intake promote --draft <draft_id>
dream kb search --team demo_team --query "output reconciliation retry"
```

### 文件落点

注册原始文件后：

```text
artifacts/intake/uploads/<document_id>.<ext>
artifacts/intake/documents/<document_id>.json
```

解析后：

```text
artifacts/intake/drafts/<draft_id>/draft.json
artifacts/intake/drafts/<draft_id>/draft.md
```

promote 后：

```text
knowledge_packs/<team_id>/docs/<document_type>/<title>-<document_id>.md
```

每个动作也会写入 audit log：

```text
knowledge_intake_upload
knowledge_intake_parse
knowledge_intake_metadata_update
knowledge_intake_review
knowledge_intake_promote
```

默认本地 SQLite：

```text
dream.sqlite
```

### Parser 当前能力

`IntakeParser` 支持：

- Markdown/text：按 Markdown heading 分 section。
- HTML/HTM：用 HTMLParser 抽取 h1/h2/h3 和正文，再转成 Markdown-like text。
- DOCX：读取 `word/document.xml` 中的段落文本，再按 Markdown-like parser 处理。

当前 concept 抽取是 deterministic：

- token 提取。
- 少量 phrase rule，例如 `execution status`、`task status`、`runbook`、`architecture`、`operator`。
- 不是 LLM semantic extraction。
- 不是向量 embedding。

### Normalized Markdown 格式

parse 后会生成带 front matter 的 Markdown：

```yaml
---
title: <document title>
app: <inferred app>
component: <inferred component>
doc_type: <document_type>
concepts: [...]
source: <original_path>
source_hash: sha256:<digest>
review_status: pending_review
---
```

正文会包含：

- 标题
- intake 提示
- 每个 section 的 heading 和正文
- `Source reference`
- `Source span`
- `Section hash`

promote 后写入 knowledge pack，后续 `MarkdownDocumentLoader` 会读取 front matter，`Chunker` 会按 H1/H2/H3 切 chunk，`SimpleRetriever` 会按 keyword 和 metadata 检索。

### 真实可验证测试

后端测试覆盖：

- `tests/test_knowledge_intake.py`
  - upload -> parse -> review -> promote
  - BOM stripping
  - audit use cases
- `tests/test_api_context_intake.py`
  - FastAPI intake endpoints
  - review gate
  - promoted_path 回填

建议回归命令：

```powershell
python scripts/verify_raw_doc_memory_flow.py
python -m pytest tests/test_knowledge_intake.py tests/test_api_context_intake.py
```

完整回归：

```powershell
python -m ruff check .
python -m pytest
cd frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

## 当前重要限制

- Source Intake 当前支持 browser multipart 文件上传，也保留“注册后端可访问本地路径”的 dev/demo 备用入口；它仍不是 Confluence/SharePoint/GitHub 等真实企业 connector。
- 当前 parser 是 deterministic parser，不会自动做深层语义 claim extraction。
- 当前 promoted Markdown 是 durable knowledge pack doc；memory scan 会把它转成 governed MemoryClaim candidates，Claim Review tab 可把 reviewer 决策写回 durable ledger，并记录 reviewer signature、字段级 governance diff、claim snapshot、raw risk/conflict signals 和 reviewer-readable signal_explanations；`/memory/conflicts` 会把 active single-value conflict 转成 claim pair report，`/memory/conflicts/resolve` 可用基础版 `approve_winner_reject_other` 写入 review ledger 和专用 conflict resolution ledger。
- `document_type` 必须和 `team.yaml` 的 `document_paths` 对齐，否则文件虽然被写入，但可能不会被 retriever 加载。
  - 当前 UI 可选的 `runbooks`、`architecture`、`domain`、`incidents`、`testing` 已和 demo `team.yaml` 对齐。
  - 后续如果允许自定义 type，仍需要做 mapping 或校验。
- 当前 claim review 已记录 status/reviewer/notes 之外的 signature、field_diffs、claim_snapshot、risk_signals、conflict_signals、signal_explanations；active conflict pair report/UI 和基础版 approve-winner/reject-other action 已有；还没有权限/审批流/ACL 策略，也还缺 supersede/merge-style conflict action。
- Metadata edit 已支持 title、doc_type、app、component、concepts，但还没有字段级 diff、冲突检测或 reviewer 签名。
- Source hash、section hash、source span、duplicate-content warning、独立 provenance/detail route、downstream usage tracking、match reason、match_proofs、claim-level match_explanation/matched_terms、Audit 跳转、Audit/Eval source chip 反链、Requirement/PR source row 反链，以及 Context Trail selected evidence 回 `/memory/:documentId` 的反链已有最小实现。
- Promote 会直接写入本地 `knowledge_packs`，企业场景应写入 private extension repo 或 governed storage。
- 已 promote 的文档是否被新 workflow 使用，取决于 workflow 每次是否重新 load knowledge pack；当前主要服务是按请求加载，适合 POC。

## 新对话交接记忆

如果开启一个新开发对话，请先给对方这段上下文：

```text
我们在 dream-ai-engineering-copilot 的 codex/memory-hub-density-cleanup 分支。
目标是把 DREAM 从 mock UI 收缩成真实 FastAPI-backed engineering memory product。
用户偏好：页面简洁、浅蓝 enterprise 风格、复杂逻辑折叠或放 detail route；不要再恢复旧 mock 页面。

当前主要页面：
/mission-control 总览入口
/memory 管 source intake 和 codebase memory
/memory/:documentId source detail，查看 raw source、structured draft、span/hash、review/promote、intake audit events、downstream usage、matched paths、match reason、match proof、Audit 跳转
/workbench 工程工作台
/requirements Jira draft
/review PR review
/context/:caseId context trail/detail，查看 retrieval steps、selected evidence、context pack、prompt preview、why selected reason，并回链 matched source detail；memory claim references 会保留 intake_proofs，approved claim 进入 context 时仍可追溯 raw intake doc、section hash、match_explanation 和 intake audit run
/codebase repo browser + saved code index JSON
/audit eval 总览
/audit/:targetId eval detail

raw doc -> structured memory 已有最小闭环：
POST /intake/documents 注册后端可访问本地文件
POST /intake/documents/upload 上传浏览器本地文件
GET /intake/documents/{id}/detail 查看 raw/doc/draft/provenance/intake audit/downstream usage 详情；返回 downstream_events 兼容字段和 downstream_usages 结构化字段；downstream_usages 带 match_proofs
POST /intake/documents/{id}/parse 解析成 draft.json + draft.md
PATCH /intake/drafts/{draft_id}/metadata 人审前修改 title/doc_type/app/component/concepts
POST /intake/drafts/{draft_id}/review 人审 approve
POST /intake/drafts/{draft_id}/promote 写入 knowledge_packs/<team>/docs/<type>/
POST /memory/scan 把 promoted docs 转成 governed MemoryClaim candidates；由 intake 文档生成的 claim 会在 evidence.intake_proofs 中带回 document_id、draft_id、promoted/raw path、source hash verification、intake audit run ids、section span/hash proof、match_explanation 和 matched_terms。
promoted docs 才算可被 workflow 使用的 structured memory。
当前 intake document 有 source_hash；draft section 有 source_span 和 section_hash；重复内容会给 warning。

重点实现文件：
dream/intake/service.py
dream/intake/repository.py
dream/intake/parsers.py
dream/intake/models.py
dream/api/routes.py
dream/memory/models.py
dream/memory/distiller.py
dream/memory/claim_retriever.py
frontend/src/app/features/memory-hub/*
frontend/src/app/features/memory-document-detail/*
frontend/src/app/core/dream-api.service.ts

当前最大产品缺口：
supersede/merge conflict action、
真实企业 connector 前的权限/脱敏/审计设计。
```

## 下一步规划建议

优先级从高到低：

1. 继续推进 conflict resolution workflow：现在 active single-value conflict pairs 已能由 `/memory/conflicts` 返回、Claim Review UI 成对展示，并可用 `approve_winner_reject_other` 写入普通 review ledger + 专用 resolution ledger；下一步是加入 supersede/merge-style 动作和字段级 resolution rationale。
2. 把 context/retrieval reason、reviewed claim、intake_proofs、match_explanation 和 raw doc detail 串成一屏；当前后端 claim evidence 已能落到 intake document、audit run id、hash、section span/hash 和 deterministic matched terms，Claim Review UI 已能显示带 signature/diff/snapshot/signals/raw trace 的结构化 proof。
3. 继续规范 source type：`runbooks`、`architecture`、`domain`、`incidents`、`testing` 等必须和 `team.yaml` 对齐。
4. 继续收紧 promoted docs 与 memory claim ledger 的边界：doc 可以被检索，semantic claim 仍需独立 review 后才能作为 approved claim 进入正式上下文。
5. Eval Agent 详情页继续收缩：总览只放分数/failed dimension/missing count，长 rationale 进 detail。
6. Codebase Index 增加 path breadcrumb 跳转和 folder-level impact map。
7. 在真实企业 connector 前补权限、脱敏、ACL、数据驻留和 private extension repo 写入策略。
8. 将 duplicate-content warning 升级为可配置 review gate 或 quarantine 策略。
