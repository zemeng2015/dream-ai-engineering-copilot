<!-- SPDX-License-Identifier: Apache-2.0 -->

# ChatGPT 对 DREAM 记忆系统方向的结论整理

日期：2026-06-23

ChatGPT 会话：
https://chatgpt.com/c/6a3a8739-a5a0-83ea-8d0c-390d79865097

输入证据：

- `docs/research-ai-engineering-memory-systems.md`
- `docs/dream-frontier-methodology.md`
- `docs/chatgpt-dream-memory-strategy-brief.md`
- 当前 DREAM 代码中 memory / knowledge / codebase / evidence graph / eval 的实现摘要

## 一句话结论

ChatGPT 的判断是：

> DREAM 值得做这个方向，但必须收窄为“受治理的工程记忆系统 MVP”。不要做“任意 repo / 文档 / runbook / Jira / Slack 自动摄入并自动写长期记忆”的大系统。

推荐定位：

> DREAM turns engineering evidence into governed memory, not just searchable context.

中文可以表述为：

> DREAM 不是把工程资料变成可搜索上下文，而是把工程证据转化为可治理、可审计、可评审、可演进的团队记忆。

## 是否应该做

结论：应该做，但必须是窄 MVP。

应该做的原因：

- repo-to-wiki、GraphRAG、agent memory、enterprise context graph 都已经证明市场需求真实存在。
- DREAM 现有代码已经有正确基础：knowledge pack、codebase index、Evidence Graph Lite、Requirement Case、PR Review、audit、eval。
- 真正差异点不是“能检索文档”，而是“能把工程证据转成候选记忆，并经过验证和人工评审后再成为 durable memory”。

不应该做的方向：

- 不要做 generic RAG chatbot。
- 不要做一次性 repo wiki 生成器。
- 不要做自动把所有 LLM 摘要写进长期记忆的系统。
- 不要第一阶段就接 GitHub/Jira/Confluence/Slack 全量 live connector。

## 差异化定位

### 相对 generic RAG

Generic RAG 是：

```text
retrieve chunks -> answer with citations
```

DREAM 应该是：

```text
extract typed engineering claims
-> validate against exact sources and current code
-> show memory diffs
-> promote only approved claims into durable memory
```

关键差异是 memory governance，不是 retrieval。

### 相对 DeepWiki / CodeWiki / Google Code Wiki

这些系统强在 repo 理解、wiki、架构图、onboarding。

DREAM 不应该和它们比“谁的 wiki 更漂亮”。DREAM 的壁垒应该是：

- code + runbook + incident + historical PR/Jira + tests + review rule 的跨源工程记忆
- 候选记忆 diff
- 人工评审和 durable promotion
- stale / conflict / security gate
- PR review、requirement impact、runbook risk 这些工程工作流输出

Wiki 只是 view，不是 source of truth。

### 相对 GraphRAG / Graphiti / Cognee / mem0

GraphRAG 和 memory framework 是基础设施。

DREAM 应该是工程应用层：

```text
repo + docs + runbooks + incidents + PR/ticket history
-> candidate claims
-> validation
-> review
-> durable memory
-> requirement / PR / test / onboarding outputs
```

也就是说，DREAM 不卖“通用记忆框架”，而卖“工程记忆治理工作流”。

## MVP 应该包含什么

MVP 名称建议：

```text
DREAM Memory Distillation MVP
```

第一阶段只摄入这些来源：

| Source | MVP 是否包含 | 原因 |
| --- | --- | --- |
| Local Git repo snapshot | 是 | 当前 branch、commit SHA、file path、line span |
| Local Git diff | 是 | 支持 PR review 和增量更新 |
| README / Markdown docs | 是 | 现有 knowledge pack 已支持 |
| ADR / design docs | 是 | 高价值语义记忆，但需要 review |
| Runbooks | 是 | 高价值但高风险，必须 review |
| Incidents / postmortems | 是 | 很适合抽取 known failure mode |
| Historical PR/Jira-like Markdown/JSON fixtures | 是 | 先用本地/export 文件，不急着 live API |
| Tests | 是 | 可确定性关联代码实体 |
| CI/workflow YAML | 窄范围支持 | 只抽 jobs / commands / env references |
| Live GitHub/Jira/Confluence/Slack | 暂不做 | connector、权限、安全复杂度太高 |
| PDFs/arbitrary docs | 暂不做 | 先证明 claim pipeline |
| DREAM 生成的 wiki | 永不作为直接来源 | 只能作为 view，不能反哺成事实源 |

## 核心数据模型

ChatGPT 建议 durable memory 不应是大段 summary，而应该是 atomic claim。

建议的 `MemoryClaimV0` 结构：

```yaml
MemoryClaimV0:
  claim_id: string
  team_id: string
  repo_id: string | null
  scan_id: string
  entity:
    entity_id: string
    entity_type: service | module | code_file | symbol | endpoint | job | test | runbook | incident | decision | requirement | pr | ticket | owner | concept
    canonical_name: string
    aliases: string[]
  relation:
    type: implements | depends_on | calls | tested_by | documented_by | runbook_for | mitigates | caused_by | changed_by | supersedes | conflicts_with | owned_by | review_rule_for | risk_for | deploys_with
    object_entity_id: string | null
    value: string | null
    condition: string | null
  evidence:
    source_ids: string[]
    spans:
      - source_id: string
        source_type: code | doc | runbook | incident | pr | ticket | test | workflow
        path: string
        commit_sha: string | null
        start_line: int | null
        end_line: int | null
        excerpt_hash: string
  extraction:
    method: deterministic | llm_semantic | human_curated
    extractor_version: string
    model_name: string | null
    confidence: float
  governance:
    status: candidate | approved | rejected | stale | conflicted | superseded | quarantined
    risk_level: low | medium | high | blocked
    reviewer: string | null
    reviewed_at: datetime | null
    rejection_reason: string | null
  temporal:
    valid_from: string | null
    valid_until: string | null
    superseded_by: string | null
  security:
    classification: public_demo | internal | sensitive | blocked
    redaction_applied: boolean
```

第一版只做五类 claim：

1. Code structure claims
2. Behavior claims from docs/runbooks/incidents
3. Historical risk claims from incidents/PRs/tickets
4. Decision claims from ADRs/design docs
5. Review-rule claims

不要先做宽泛的 architecture summary memory。

## 推荐架构

ChatGPT 的架构结论是：

```text
RepoGraph      = deterministic structure
EvidenceGraph  = source spans, entities, evidence paths
MemoryLedger   = candidate/approved/stale/conflicted atomic claims
```

不要把所有东西混成一个松散大图。

推荐 pipeline：

```text
Source registry
  -> source snapshot + span registry
  -> deterministic RepoGraph extraction
  -> semantic claim extraction
  -> validation gates
  -> candidate memory diff
  -> human review / auto-promotion policy
  -> durable memory ledger
  -> retrieval + generated views
  -> eval + audit
  -> incremental refresh
```

MVP 存储建议：

- SQLite 或 Postgres 优先
- 表：source_records、source_spans、repo_nodes、repo_edges、memory_claims、memory_claim_evidence、memory_reviews、memory_conflicts、scan_runs、eval_runs
- Neo4j、Graphiti、GraphML export 以后作为 optional adapter

## 验证和人工介入边界

必须经过 validation gates：

| Gate | 规则 |
| --- | --- |
| Source gate | 必须引用系统生成的 source_id 和 exact span |
| Schema gate | entity type / relation type 必须符合 `MemoryClaimV0` |
| Evidence-span gate | claim 必须被 cited span 支撑，否则输出 `INSUFFICIENT_EVIDENCE` |
| Deterministic-code gate | code structure 必须来自 parser/indexer，不由 LLM 推断 |
| Entity-resolution gate | canonical entity 不明确就进入 review |
| Freshness gate | span 在当前 scan 中不存在就 stale |
| Conflict gate | 冲突 claim 保留为 conflicted，不强行合并 |
| Security gate | secret、PII、sensitive ops data 必须 block/quarantine |
| Dedupe gate | 近重复 claim 合并为一个 candidate |
| Risk gate | production/security/owner/escalation/customer-impacting claim 必须人工 review |

可以自动 approve 的：

- 文件存在
- 文件语言/角色
- class/function/method symbol
- import/dependency edge
- endpoint annotation
- 高置信 source-to-test mapping
- 低风险 markdown front-matter concept link

必须人工 review 的：

- architecture decisions
- runbook steps
- incident lessons
- production commands
- security/compliance facts
- owner/escalation/permission facts
- customer-impacting behavior
- conflicting evidence
- low-confidence extraction
- entity merge/split
- schema changes
- generated-summary promotion

永不应成为 durable active memory 的：

- secrets/tokens/passwords/private keys
- PII/customer data
- unsupported LLM inference
- speculation/TODO/debug notes
- transient chat/task state
- DREAM generated wiki without original evidence
- fake/unresolvable citations
- broad narrative summaries

## Evaluation 标准

最重要的三个门槛：

```text
citation validity = 100%
secret leakage = 0
semantic auto-promotion = 0 in MVP
```

建议指标：

| Metric | MVP threshold |
| --- | --- |
| Citation validity | 100% |
| Unsupported claim rate | <= 3% |
| Semantic extraction precision | >= 85% |
| Structural extraction precision | >= 95% |
| Entity resolution precision | >= 95% |
| Conflict detection recall | >= 80% |
| Stale detection recall | >= 80% initially |
| Secret leakage | 0 |
| Duplicate claim rate | <= 5% |
| Grounded answer correctness | >= 85% |
| Abstention quality | >= 90% |
| Review burden | p50 < 30 sec / claim, p90 < 90 sec / claim |

需要构建 `memory_v0` golden suite，覆盖：

- stale runbook
- renamed class / moved file
- README 与 code 冲突
- incident lesson 应该/不应该成为 memory
- duplicate service names
- old PR decision superseded by newer ADR/code
- fake citation
- prompt injection in Markdown
- secret/token
- generated wiki 被误放回 docs
- ambiguous owner/escalation claim
- insufficient evidence

## 2/6/12 周路线图

### 2 周：证明 candidate memory，不做自动化幻想

目标：从本地 repo/docs 抽取 source-backed candidate claims，并展示 reviewable memory diff。

交付：

- `MemoryClaimV0` 和 `SourceSpan` 模型
- source registry：content hash、path、commit SHA、line span
- `artifacts/memory-candidates/{team_id}/{scan_id}.json`
- deterministic structural claims
- LLM semantic extraction from Markdown only
- source/schema/citation/security/dedupe gates
- CLI：

```bash
dream memory scan --team demo_team --repo java-demo-repo
dream memory diff --team demo_team --scan latest
dream memory eval --suite memory_v0
```

退出标准：

- citation validity = 100%
- secret leakage = 0
- structural precision >= 95%
- semantic candidate precision 被测量
- no semantic auto-promotion

### 6 周：接入 DREAM workflow

目标：approved/candidate memory 接入 Requirement Case 和 PR Review，并做 review queue。

交付：

- memory review UI：approve/reject/edit/mark stale/mark conflict/assign reviewer
- durable memory ledger in SQLite/Postgres
- EvidenceGraph 升级：SourceSpan、CandidateClaim、DurableClaim、Entity
- entity resolver v0
- conflict detection
- stale detection
- Requirement Case 和 PR Review 接入
- Eval dashboard

退出标准：

- semantic candidate precision >= 85%
- unsupported claim rate <= 3%
- entity resolution precision >= 95%
- conflict detection recall >= 80%
- stale detection recall >= 80%
- review p50 < 30 sec / claim

### 12 周：成为可信的 open-source governed engineering memory platform

目标：做成可对外展示的增量工程记忆平台。

交付：

- Git diff-triggered incremental update
- temporal memory：valid_from、valid_until、superseded_by
- risk-based promotion policy
- optional vector/reranker layer
- local Git history ingestion
- public benchmark/demo
- future connector adapter interface
- 文档：not generic RAG、generated artifacts are views、promotion policy、eval thresholds、security model limitations

退出标准：

- citation validity = 100%
- secret leakage = 0
- semantic precision >= 90%
- unsupported claim rate <= 1% before any semantic auto-promotion experiment
- stale detection recall >= 90%
- incremental update recall >= 90%
- no generated artifact feedback-loop failures

## 对 DREAM 当前项目的直接建议

下一步最值得做的不是更多 UI，也不是先接外部 connector，而是补齐 memory distillation 的最小闭环：

1. 新增 source registry 和 source span registry。
2. 定义 `MemoryClaimV0`。
3. 新增 `dream memory scan/diff/eval` CLI。
4. 从现有 knowledge pack、codebase index、evidence graph 生成 candidate claims。
5. 增加 validation gates。
6. 增加 memory diff review artifact 或 UI。
7. 将 approved memory 接入 Requirement Case 和 PR Review。

这会让 DREAM 从“source-backed context tool”升级为“governed engineering memory platform”。

## 最终判断

ChatGPT 的最终 recommendation：

> Build it, but with a hard scope boundary.

不要做：

```text
arbitrary docs -> embeddings -> chatbot -> auto memory
```

要做：

```text
repo + docs + runbooks + incidents + PR/ticket history
  -> source spans
  -> deterministic RepoGraph
  -> candidate semantic claims
  -> validation gates
  -> reviewable memory diff
  -> durable memory ledger
  -> evidence graph retrieval
  -> requirement / PR / runbook / wiki outputs
  -> eval and audit
```

这条路线值得立项，而且比 generic RAG、repo wiki、GraphRAG framework 更有差异化。
