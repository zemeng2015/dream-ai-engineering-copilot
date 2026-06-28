<!-- SPDX-License-Identifier: Apache-2.0 -->

# DREAM 记忆系统技术说明

## 1. 项目定位

DREAM 是一个 source-backed memory platform。它不是通用聊天机器人，也不是简单 RAG demo。核心目标是把团队里的代码、文档、runbook、事故记录、历史 Jira/PR、测试计划、评审规则等信息，整理成可检索、可引用、可审计、可人工验收的工程记忆系统。

当前第一个落地场景是软件工程协作：从粗糙业务需求出发，生成有证据支撑的需求草案、影响分析、澄清问题、工程 brief、Jira 草稿、PR review 摘要和质量评估报告。

## 2. 设计原则

DREAM 的记忆系统遵循几个原则：

- 证据优先：任何可持久化的记忆都必须能回溯到 source、span、hash 或具体文件路径。
- 少提取、强引用：系统不追求一次性抽取所有知识，而是优先提取低风险、可验证、可审查的 claim。
- 结构化记忆优先于 prompt 拼接：团队知识不是临时塞进 prompt，而是沉淀为可复用的索引、图谱、claim 和审计记录。
- 语义 claim 默认需要人工验收：代码结构类事实可以自动批准；从文档中推断出来的语义记忆默认保持 candidate 状态。
- 记忆不能污染自己：生成物不能直接变成权威记忆，除非它能指向原始 source 并通过 review/eval。

## 3. 高层架构

```text
Knowledge Packs / Repo / Runbooks / Incidents / PR-Jira History
  -> Source Registry
  -> Source Spans
  -> Codebase Index
  -> Evidence Graph
  -> Candidate Memory Claims
  -> Validation Gates
  -> Memory Diff Review
  -> Durable Memory Ledger
  -> Retrieval for Requirement / PR Review / Eval Workflows
```

当前实现已经覆盖到：

- Knowledge Pack 加载
- Codebase Index
- Evidence Graph Lite
- Memory Claim 蒸馏
- Memory Diff
- Memory Eval
- CLI/API 入口

尚未完成的是：

- UI approval workflow
- approved memory claim 直接接入 Requirement/PR/TestGen 等业务 workflow
- 增量扫描和跨版本 diff

## 4. 记忆系统的四层实现

### 4.1 Knowledge Pack 层

Knowledge Pack 是团队知识的源头。它由 Markdown 和 YAML 组成，包含：

- domain docs
- architecture docs
- runbooks
- incidents
- testing docs
- pr-review rules
- historical Jira
- historical PR
- concept memory

技术实现：

- `KnowledgePackLoader` 读取 `team.yaml`
- `MarkdownDocumentLoader` 读取 Markdown
- `Chunker` 切分文档
- `SimpleRetriever` 做确定性关键词和 metadata 检索

这层的特点是简单、透明、可本地运行，不依赖 vector database。

### 4.2 Codebase Memory 层

Codebase Memory 把本地 repo 变成结构化代码记忆。

它记录：

- files
- language
- file role
- symbols
- endpoint-like methods
- dependencies
- concepts
- source-to-test mappings
- summaries
- warnings

技术实现：

- `CodebaseScanner` 扫描文件
- `detect_language` 判断语言
- `extract_symbols_and_dependencies` 提取 Java/Python/TypeScript 符号和依赖
- `CodebaseIndexer` 生成 `RepoIndex`
- `CodebaseIndexRepository` 写入 JSON artifact

artifact 路径：

```text
artifacts/codebase-indexes/{team_id}/{repo_name}.json
```

这层目前是 deterministic index，不依赖 LLM。

### 4.3 Evidence Graph 层

Evidence Graph Lite 把文档、代码、测试、事故、历史 Jira/PR 连接起来。

典型节点：

- concept
- knowledge doc
- code file
- symbol
- test file
- incident
- historical Jira
- historical PR

典型边：

- `MENTIONED_IN`
- `IMPLEMENTED_BY`
- `DEFINED_IN`
- `TESTED_BY`
- `AFFECTS`
- `REGRESSED_BY`
- `REQUIRED_BY`
- `CHANGED_BY`

技术实现：

- `EvidenceGraphBuilder` 从 Knowledge Pack 和 Codebase Index 构建图
- `EvidenceGraphRepository` 持久化图
- `EvidenceGraphRetriever` 做图搜索和 explain

artifact 路径：

```text
artifacts/evidence-graphs/{team_id}/{repo_name}.json
```

Requirement Case 和 PR Review 会使用 Evidence Graph，让输出能展示 evidence paths，而不是只给无来源结论。

### 4.4 Governed Memory Distillation 层

这是当前新增的记忆蒸馏层。它把 repo 和知识文档转成可审查的 `MemoryClaim`。

核心模型：

- `SourceRecord`：一个原始来源，如代码文件、测试文件、文档。
- `SourceSpan`：来源中的具体行号区间、hash 和 preview。
- `MemoryEntity`：被描述的实体，如 code file、symbol、endpoint、concept、incident、runbook。
- `MemoryRelation`：实体之间的关系，如 `defined_in`、`tested_by`、`documented_by`、`risk_for`、`mitigates`。
- `MemoryEvidence`：claim 依赖的 source id 和 span。
- `ExtractionInfo`：提取方法、版本、置信度。
- `GovernanceInfo`：candidate/approved/quarantined、风险等级、reviewer。
- `SecurityInfo`：安全分类和是否 redacted。
- `MemoryScanResult`：一次 scan 的完整结果，包含 schema version 和 repo provenance。
- `MemoryEvalResult`：一次 eval 的验收结果。

实现入口：

- `MemoryDistillationService.scan`
- `MemoryDistillationService.diff_markdown`
- `MemoryDistillationEvaluator.evaluate`
- `MemoryDistillationRepository`

artifact 路径：

```text
artifacts/memory-scans/{team_id}/{scan_id}.json
artifacts/memory-scans/{team_id}/latest.json
artifacts/memory-evals/{team_id}/{evaluation_id}.json
```

每次 scan 会记录：

- schema version
- scanned repo path
- containing Git root
- current commit SHA
- dirty state
- dirty path list
- scanner version

`SourceRecord.commit_sha` 会从 scan provenance 填充。hash 仍基于原始内容计算，但 `SourceSpan.preview` 在落盘前会先做 redaction，避免 secret-like assignment、AWS access key、JWT-like token、private key header 直接进入 artifact preview。

## 5. Claim 类型和晋升规则

当前系统区分 deterministic structural claims 和 heuristic semantic claims。

结构类 claim 可以自动 approved：

- file has language
- symbol defined in file
- endpoint-like symbol implements endpoint-like method

测试映射类 claim 通常保持 candidate，除非后续有更强证据：

- source file tested by test file

语义类 claim 默认 candidate：

- concept documented by Markdown
- runbook mitigates risk
- incident risk_for component
- ticket documented_by requirement
- architecture decision documented_by document

敏感或疑似 secret 的来源会 quarantined，不进入正常 durable memory。

## 6. 验收和 Guardrails

`dream memory eval` 当前检查：

- citation validity
- unsupported claim rate
- secret leakage count
- structural claim count
- semantic candidate claim count
- auto-promoted semantic claim count

当前 pass 条件：

```text
citation_validity == 1.0
unsupported_claim_rate <= 0.03
secret_leakage_count == 0
auto_promoted_semantic_claims == 0
```

这些指标的意义：

- citation validity：claim 是否真的引用了本次 scan 中存在的 source span。
- unsupported claim rate：没有证据或证据失效的 claim 比例。
- secret leakage count：敏感来源是否被错误进入非隔离状态。
- auto-promoted semantic claim count：语义推断是否被错误自动批准。

## 7. CLI 和 API

CLI：

```bash
dream memory scan --team demo_team --repo examples/java-demo-repo --name java-demo-repo
dream memory diff --team demo_team
dream memory eval --team demo_team
```

API：

```text
POST /memory/scan
GET  /memory/scans/latest
GET  /memory/diff
POST /memory/eval
```

示例：

```bash
curl -X POST http://localhost:8000/memory/scan \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","repo_path":"examples/java-demo-repo","repo_name":"java-demo-repo"}'

curl "http://localhost:8000/memory/diff?team_id=demo_team"

curl -X POST http://localhost:8000/memory/eval \
  -H "Content-Type: application/json" \
  -d '{"team_id":"demo_team","scan_id":"latest"}'
```

## 8. 技术栈

后端：

- Python 3.11+
- FastAPI
- Pydantic v2
- Typer CLI
- PyYAML
- Uvicorn
- SQLite audit/eval storage
- JSON artifact repository

开发和测试：

- pytest
- ruff
- httpx

前端：

- Angular 19
- TypeScript 5.7
- RxJS
- SCSS design tokens
- Karma/Jasmine

当前 memory/index/graph 层没有强依赖外部数据库、向量数据库或云服务。OpenAI-compatible provider 是可选能力，用于生成类 workflow；本地测试和 demo 默认使用 deterministic/mock provider。

## 9. 当前实现的强项

- 本地可运行，部署和演示成本低。
- 证据链清楚：source、span、hash、artifact 都能落盘。
- 结构化程度高：不是把文档直接塞给 LLM，而是形成 codebase index、evidence graph、memory claim。
- Governance 意识正确：semantic claim 默认 candidate，避免自动把推断当事实。
- API/CLI 都已经可用，适合继续接 UI review queue。
- 测试覆盖当前核心路径，当前全量 pytest 为 52 passed。

## 10. 主要优化空间

### 已完成：记录 commit 和 dirty 状态

`SourceRecord.commit_sha` 字段已经从 scan provenance 填充。当前已记录：

- repo commit SHA
- dirty state
- scanned root
- extractor version
- artifact schema version

后续仍可继续增强为 per-source provenance，例如分别记录外部 repo、knowledge pack repo 和生成 artifact repo 的来源版本。

### P0：实现 durable approval ledger

当前 `memory diff` 是 review queue，不是真正的批准账本。需要新增：

- approve/reject/quarantine 操作
- reviewer
- review reason
- reviewed_at
- previous_claim_id
- superseded_by
- durable ledger artifact 或 SQLite table

### 已完成基础版：增强 secret redaction

当前 secret 检测是基础 regex。后续需要：

- 在写入 `SourceSpan.preview` 前先 redaction
- 增加 AWS key、PEM、JWT、高熵 token、`.env` 检测
- 对 blocked source 默认不落 preview

当前实现已经在 preview 落盘前 redaction secret-like assignments、AWS access key、JWT-like token 和 private key header。后续可继续加入高熵 token 和 `.env` 语义检测。

### 已完成基础版：durable approval ledger

当前实现已经新增 review ledger：

- approve/reject/quarantine/candidate 状态流转
- reviewer
- review reason
- reviewed_at
- scan_id
- previous_status/new_status

ledger 存储在：

```text
artifacts/memory-ledgers/{team_id}.json
```

### 已完成基础版：做真正的 scan diff

当前 diff 是单个 scan 的 claim 列表。后续应支持：

- added claims
- removed claims
- changed evidence
- changed confidence
- changed status
- stale evidence

当前实现已经支持 added/removed/changed/unchanged 统计；后续可继续增强 stale evidence 和 status-only diff。

### 已完成基础版：把 MemoryClaim 接入 retrieval

当前 Requirement Case/PR Review 主要用 Knowledge Pack、Codebase Index 和 Evidence Graph。下一步应新增：

- `MemoryClaimRetriever`
- 只检索 approved claims
- candidate claims 只进入 review UI
- 输出中显示 claim id 和 evidence span

当前实现已经提供 approved-claim search 和 `memory context` context card。后续需要把 context card 直接接入 Requirement Case、PR Review、TestGen 等 workflow。

### P1：引入 schema-based LLM extraction

当前 semantic claim 来自 front matter 和 doc_type heuristic。可引入 LLM，但必须约束：

- JSON schema 输出
- strict source-span citation
- semantic claim 默认 candidate
- eval 不通过不能进入 durable memory

### P2：增量扫描

当前每次 scan 全量跑。后续应按 content hash 做增量：

- unchanged source 跳过
- changed source 重新抽取
- deleted source 标记相关 claim stale

## 11. 建议下一步开发顺序

推荐顺序：

1. 提交当前 memory distillation MVP。
2. 将 approved memory context card 接入 Requirement Case 和 PR Review。
3. 增强 stale evidence / status-only diff。
4. 增加 UI approval workflow。
5. 继续增强 secret scanning。
6. 最后再加 LLM semantic extraction。

原因是：provenance 和 redaction 已经具备基础版；补齐 ledger、true diff 和 approved-claim retrieval 后，系统才更接近“可进入公司项目长期演进的工程记忆系统”。
