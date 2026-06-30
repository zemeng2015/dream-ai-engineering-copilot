# DREAM 对 Omni Agentic Analytics 架构的参考结论

日期：2026-06-28

状态说明：本轮已再次尝试把材料发给 ChatGPT Pro 页面复核，但 Chrome 扩展控制在 claim ChatGPT 标签时连续超时，未能取得 ChatGPT 页面生成的独立回复。以下结论基于可访问公开资料、B 站视频元数据/分段概要，以及 DREAM 当前代码实现整理。后续若浏览器控制恢复，可直接使用本文末尾 prompt 再提交给 ChatGPT。

## 1. 结论

Omni 的材料对 DREAM 有较高参考价值，但它参考的是 agent harness 工程形态，不是自动记忆提取算法本身。

对 DREAM 的核心启发是：

- 不要让 LLM 直接面对混乱 repo/doc 上下文自由发挥。
- 先建设一个受治理的 semantic substrate：approved memory claims、evidence graph、source spans、permissions、review ledger。
- 在这个 substrate 之上构建 typed tools、run trace、validators、evals 和 human review UI。
- 先做好 single coordinator + deterministic tools，不要过早上复杂 multi-agent。

所以 DREAM 下一阶段应该命名为 Agent Harness Lite：把 Requirement Case、PR Review、Memory Review 从“检索增强输出”升级为“可追踪、可验证、可回放的工程 agent workflow”。

## 2. Omni 概念到 DREAM 概念映射

| Omni 概念 | DREAM 对应概念 | 参考价值 |
| --- | --- | --- |
| Semantic model / semantic layer | Approved MemoryClaim + Evidence Graph Lite + source spans | 高。DREAM 应把 memory layer 明确定位为 engineering semantic layer。 |
| Natural language to analytics actions | Requirement / PR / memory-review workflow | 高。用户输入应进入受控 workflow，而不是直接 prompt。 |
| Blobby agent | DREAM workflow coordinator | 中。可以参考工具调度，但不要复制 analytics 领域假设。 |
| Tool registry / harness | DREAM typed tools | 高。所有 search、graph explain、context card、validator 都应工具化。 |
| Raw traces and bad-session analysis | DREAM RunTrace / EvalTrace | 高。必须落盘每一步输入、工具、证据、输出、失败原因。 |
| Dashboard Builder UI | DREAM evidence/review UI | 中高。生成结果应可检查、可编辑、可批准。 |
| Agent Skills | DREAM versioned workflow specs | 高。Requirement Case、PR Review、Memory Review 可定义为可版本化 skills。 |
| 99% code by Claude Code | DREAM 开发效率参考 | 低。不是产品架构护城河。 |

## 3. DREAM 应采纳什么

### 3.1 Agent Harness Lite

新增一个轻量 workflow runtime：

- `RunTrace`：记录 workflow id、输入、工具调用、memory claim ids、graph path ids、validator 结果、最终输出。
- `ToolCallTrace`：记录工具名、参数摘要、返回摘要、耗时、错误。
- `EvidenceUse`：记录输出中每个关键结论引用了哪些 source span / claim / graph node。
- `WorkflowSpec`：声明某 workflow 允许调用哪些 tools、需要哪些 validators、最终产物 schema。

首批 workflow：

- `requirement_case_v1`
- `pr_review_v1`
- `memory_review_v1`

### 3.2 Typed Tools

把现有能力包装为明确工具：

- `memory.search_approved_claims`
- `memory.build_context_card`
- `memory.diff_latest_scan`
- `graph.search`
- `graph.explain`
- `codebase.search_symbols`
- `codebase.find_related_tests`
- `review.validate_sources`
- `review.check_unapproved_claims`

每个工具必须返回结构化结果，禁止 workflow 直接拼接自由文本作为事实来源。

### 3.3 Validators Before Final Output

最终输出前必须过 deterministic validators：

- 结论引用的 memory claim 必须是 `approved`。
- source span 必须能在 artifact/source 中解析。
- graph path 必须存在。
- candidate/rejected/superseded claim 不得作为正式结论依据。
- 输出中如果存在未证实推断，必须标为 assumption 或 open question。

### 3.4 UI 侧 Evidence Panel

前端不应该只展示生成 markdown。应该展示：

- 最终产物。
- 证据卡片。
- memory claim 状态。
- graph path。
- tool trace。
- validator pass/fail。
- approve/reject/supersede 操作。

这对应 Omni 的 dashboard builder 思路：AI 生成，但人可以检查、编辑和接管。

## 4. DREAM 不应照搬什么

- 不要照搬 analytics agent 的 SQL/metric 假设。DREAM 的输入是 repo、runbook、incident、PR、Jira、测试文档，非结构化程度更高。
- 不要过早做多智能体。Omni 的经验反而说明 sub-agent 容易造成上下文断裂和不可预测行为。DREAM 现在应先做 single coordinator。
- 不要把“Claude 写了 99% 代码”当作项目价值主张。用户买的是可信工程记忆和可审计 workflow，不是 AI 写代码比例。
- 不要自动把生成结果反补进 durable memory。公司内改动、临时推断、未审核输出都必须留在 candidate 或 trace 层。

## 5. 推荐下一阶段开发计划

### P0：Agent Harness Lite

1. 新增 `dream/workflows/` 模块。
2. 增加 `WorkflowRun`, `RunTrace`, `ToolCallTrace`, `EvidenceUse`, `ValidationResult` models。
3. 增加 `ToolRegistry`，先注册 memory / graph / codebase / validator 工具。
4. Requirement Case workflow 改为通过 tool registry 获取 approved memory context card。
5. PR Review workflow 改为记录 related codebase memory、graph evidence、approved memory claims。
6. CLI/API 增加：
   - `dream workflow run requirement-case`
   - `dream workflow traces --team demo_team`
   - `GET /workflows/traces/{run_id}`

### P1：UI Evidence Review

1. 前端增加 workflow trace page。
2. Requirement Case / PR Review 结果页增加 Evidence Panel。
3. Memory diff 页面增加 approve/reject/supersede inline actions。
4. 显示 validator failures，并阻止“高风险失败”的结果被标记为 ready。

### P2：Eval Harness

1. 构造 golden cases：
   - 正确引用 approved memory。
   - 拒绝 candidate memory。
   - stale/superseded memory 不进入结论。
   - graph path 缺失时降级为 open question。
2. 记录每次 workflow 的 unsupported claim rate。
3. 增加 regression tests，保证 trace、source、validator 全链路存在。

## 6. 验收标准

Agent Harness Lite 完成时，至少满足：

- 每次 Requirement Case / PR Review 都生成 run id。
- 每个 run id 可回放：
  - 用户输入。
  - 调用过的 tools。
  - 使用过的 memory claim ids。
  - 使用过的 graph nodes/edges。
  - validators pass/fail。
  - 最终输出。
- 未 approved 的 memory claim 不会进入 final conclusion。
- source span 缺失会触发 validator failure。
- 测试覆盖 workflow trace、approved-only retrieval、validator block、API trace retrieval。

建议最低测试：

- `tests/test_workflow_trace.py`
- `tests/test_requirement_case_workflow_memory.py`
- `tests/test_pr_review_workflow_memory.py`
- `tests/test_workflow_validators.py`

## 7. 最高风险架构错误

1. 把 memory 当 prompt stuffing，而不是 governed semantic layer。
2. 让 LLM 自己决定哪些记忆可信。
3. 没有 run trace，导致用户无法审计为什么得出结论。
4. 自动把 AI 输出反补成 durable memory，形成污染闭环。
5. 过早引入 multi-agent，导致定位问题困难。
6. 前端只展示漂亮结论，不展示证据和风险状态。
7. eval 只看输出质量，不看 provenance、unsupported claim、stale memory。

## 8. 公开参考链接

- B 站视频：https://www.bilibili.com/video/BV1vmTA6pEXK/
- Anthropic session：https://claude.com/code-with-claude/session/ldn-ext-building-the-best-agentic-analytics-harness-powered-by-claude-built-with-claude-code
- Omni agentic analytics architecture：https://omni.co/blog/building-omnis-architecture-for-agentic-analytics
- Omni semantic model for AI：https://omni.co/blog/why-ai-needs-a-semantic-model
- Omni AI context：https://omni.co/blog/improving-ai-quality-with-context
- Omni Agent Skills：https://omni.co/blog/introducing-omnis-agent-skills
- Omni Dashboard Builder：https://omni.co/blog/introducing-omnis-dashboard-builder

## 9. 可直接提交给 ChatGPT 的复核 Prompt

```text
You are reviewing whether Omni's agentic analytics architecture is useful as evidence and guidance for the DREAM AI engineering memory system.

Context:
- User is building DREAM: an open-source engineering memory platform for teams.
- DREAM ingests repo/docs/runbooks/incidents/Jira/PR/test evidence and turns it into governed, source-backed engineering memory.
- Current DREAM implementation summary:
  - Knowledge packs from Markdown and team.yaml.
  - Codebase memory index for local repositories.
  - Evidence Graph Lite linking concepts, docs, code, tests, incidents, Jira, and PR memory.
  - Memory Distillation layer with SourceRecord, SourceSpan, MemoryClaim, MemoryEvidence, redaction, deterministic scanning, diff, review ledger, approval/rejection/supersession, eval guardrails.
  - Approved memory search and context cards via MemoryClaimRetriever.
  - Requirement Case and PR Review workflows currently use knowledge/codebase/evidence graph memory, but approved memory context cards are not yet fully integrated into every workflow.
  - Current known next phase: build an Agent Harness Lite so Requirement Case / PR Review / Memory Review become traceable, tool-driven, and eval-backed workflows.

Video / source being evaluated:
- Bilibili: https://www.bilibili.com/video/BV1vmTA6pEXK/
- Title: "99% code by Claude: How Omni built top AI Agent analytics architecture"
- Metadata summary says original Claude channel session was published 2026-05-21, Bilibili posted 2026-06-27.
- Segment outline:
  - Omni AI Analytics core: semantic layer translating natural language to databases.
  - Semantic layer and context: Cloud.md / permissions to improve agent understanding.
  - Blobby agent demo for complex analytics queries.
  - Agentic Harness: fault tolerance and budget management.
  - Trace analysis of bad sessions; tool design and sub-agent iteration.
  - Interface/parser optimization: SQL to complex task chains.
  - Raw Trace driven eval / observability.
  - 99% platform code by Claude Code.

Official/public corroborating links:
- Anthropic session: https://claude.com/code-with-claude/session/ldn-ext-building-the-best-agentic-analytics-harness-powered-by-claude-built-with-claude-code
- Omni agentic analytics architecture: https://omni.co/blog/building-omnis-architecture-for-agentic-analytics
- Omni semantic model for AI: https://omni.co/blog/why-ai-needs-a-semantic-model
- Omni AI context: https://omni.co/blog/improving-ai-quality-with-context
- Omni Agent Skills: https://omni.co/blog/introducing-omnis-agent-skills
- Omni Dashboard Builder: https://omni.co/blog/introducing-omnis-dashboard-builder

Please use Pro-level deep reasoning. Be skeptical and practical. Do not produce generic agent hype.

Deliverable requested:
1. Decide whether this Omni material is useful for DREAM, and how strong the evidence is.
2. Map Omni concepts to DREAM concepts.
3. Identify what DREAM should adopt, what it should not copy, and why.
4. Recommend the next implementation phase for DREAM, with concrete engineering backlog items.
5. Define acceptance criteria and evals for that phase.
6. State the highest-risk architectural mistakes DREAM should avoid.
7. Output in Chinese, concise but senior-engineer level. Use headings and bullet points.
```
