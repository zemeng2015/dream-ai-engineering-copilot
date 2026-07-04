# DREAM Frontend Runbook

> 历史版本：本 runbook 生成于当前 live FastAPI UI 简化之前，保留作参考。
> 新一轮产品验收前必须重新截图并生成。当前路由和运行方式见
> `docs/frontend-angular.md` 与 `docs/current-development-handoff.md`。

生成时间：`2026-07-01T12:49:58.521Z`

目标环境：`http://127.0.0.1:4300`

截图方式：`Chrome DevTools Protocol viewport-height screenshot`

本 runbook 覆盖 Angular router 中的全部实际页面路由；`/` 和 `/dashboard` 会重定向到 `/mission-control`，`**` 也会回到 `/mission-control`，所以不单独截图。

安全边界：
- 当前 UI 以 mock/demo 数据为主，不包含真实公司数据、真实 Jira、真实 PR、真实日志或真实 repo 写入。
- Requirement Case 和 PR Review 默认使用 `Mock local provider`；只有切到 `Real FastAPI + OpenAI-compatible provider` 时才会调用后端 `127.0.0.1:8000`。
- PR Review 的 real mode 当前发送后端固定的 synthetic diff/Jira 路径，不是把页面 textarea 里的 diff/Jira 原文直接传给后端。
- Knowledge Intake、Eval Rating、TestGen Stub 的状态是前端 in-memory/demo 行为，不等于生产落库。
- Knowledge Intake 上传使用浏览器本地 `file.text()` 做 demo parse；不要把它当成可靠 DOCX/HTML/JSON 解析器，也不要上传真实敏感资料。
- TestGen Stub 不生成单元测试，也不写 repository。

## 页面索引
| 页面 | Route | 标题 | 说明 |
| --- | --- | --- | --- |
| [Mission Control](#mission-control) | `/mission-control` | DREAM Mission Control | 全局驾驶舱，用一屏汇总记忆源、审计、pipeline、需要人工 review 的事项。 |
| [Memory Hub](#memory-hub) | `/memory` | DREAM Memory Hub | Memory Hub 总览页，管理 source evidence 到 approved workflow context 的闭环。 |
| [Engineering Workbench](#engineering-workbench) | `/workbench` | DREAM Engineering Workbench | 需求分析和 PR Review 的工作台容器，旁边固定显示 context trust sidebar。 |
| [Trust Center](#trust-center) | `/trust` | DREAM Trust Center | 检索可信度、prompt preview、eval/audit 和 human rating 的治理入口。 |
| [Knowledge Memory](#knowledge-memory) | `/knowledge` | Knowledge Base | 知识源搜索和 chunk 预览页面，用于查 domain docs/runbooks/incidents/Jira/PR/test docs。 |
| [Knowledge Intake](#knowledge-intake) | `/knowledge-intake` | Knowledge Intake | 把上传/导入的 source parse 成候选 memory cards，并经过 approve/promote 流程。 |
| [Memory Atlas](#memory-atlas) | `/codebase` | Code Index | 代码库 capability memory atlas，把业务能力、代码文件、测试、风险和 prompt 用途连接起来。 |
| [Retrieval Paths](#retrieval-paths) | `/graph` | Retrieval Paths | 按业务概念查 docs -> code -> tests 的 evidence graph path。 |
| [Context Intelligence](#context-intelligence) | `/context-intelligence` | Context Intelligence | 展示 intent 到 source-backed context pack、prompt preview、logic chain 的完整组装过程。 |
| [Requirement Case](#requirement-case) | `/requirements` | Requirement Case | 把粗糙业务需求转为 evidence、impact map、澄清问题、scorecard 和 Jira draft。 |
| [PR Review](#pr-review) | `/review` | PR Review | 用 synthetic diff/Jira context 生成 evidence-backed PR review aid。 |
| [TestGen Stub](#testgen-stub) | `/testgen` | TestGen Stub | 展示未来 TestGen provider 接口，但当前不生成测试、不写 repo。 |
| [Eval & Audit](#eval-audit) | `/audit` | Audit & Eval | 查看 deterministic scorecards、run history、human ratings 和 evidence coverage。 |
| [Settings](#settings) | `/settings` | Settings | 运行模式和 guardrails 的只读配置预览。 |

## 使用方式
看每张截图上的编号，再对照下面表格。每页的 `1` 和 `2` 通常是全局左侧导航和顶部栏；后续编号是该页面自己的功能区域。

左侧导航只暴露 5 个顶层入口。其他功能页通过 Mission Control quick actions、Memory Hub tabs、Workbench mode、Trust Center tabs 或直接 route 进入；所以 runbook 按 Angular router 覆盖全部页面，而不是只按 sidebar 覆盖。

`/memory`、`/workbench`、`/trust` 是容器页，截图展示默认嵌入态；它们嵌入的 Intake/Atlas/Trace/Evidence、Requirement/PR、Context/Audit 也都有独立 route 截图。

## 主导航页
### Mission Control {#mission-control}

- Route：`/mission-control`
- 页面目的：全局驾驶舱，用一屏汇总记忆源、审计、pipeline、需要人工 review 的事项。
- 标注截图：

![Mission Control annotated screenshot](annotated-screenshots/mission-control-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面主叙事与入口 | 告诉用户 DREAM 的定位，并提供进入 Workbench 和 Trust Trail 的两个主入口。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | 主工作流按钮 | Open Workbench 进入需求/PR 工作流；Inspect Trust Trail 查看可审计证据链。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | 本地演示护栏 | 展示当前 demo 是否允许外部修改、默认 provider、是否需要人工审批。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | 关键指标条 | 快速看当前 mock memory、case、scorecard、rating、待 review 数量。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Memory-to-review pipeline | 展示从知识包、代码索引、检索路径到 review/audit 的端到端链路。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Recent Audit Runs | 最近生成/审计 run 的状态表，用于判断哪些输出失败、通过或待审。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 9 | Retrieval Path Preview | 预览业务概念如何映射到 evidence path。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 10 | Knowledge Pack Health | 查看知识包覆盖率和健康状态，定位缺失/危险知识源。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 11 | Active Requirement Case | 当前最重要需求 case 的摘要、置信度和 evidence/impact 数量。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 12 | Human Review Required | 列出需要人工确认的 run，提醒不能自动发布。 | 这是人工门禁/反馈区，用来证明输出不能自动发布。 |
| 13 | Quick Actions | 快捷进入需求、代码索引、PR review、Memory、Trust、Context Trail。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Memory Hub {#memory-hub}

- Route：`/memory`
- 页面目的：Memory Hub 总览页，管理 source evidence 到 approved workflow context 的闭环。
- 标注截图：

![Memory Hub annotated screenshot](annotated-screenshots/memory-hub-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Memory Hub 标题与动作 | Add Source 切到 Intake；Trace Request 切到检索轨迹。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Hub 内部 Tabs | 切换 Loop Overview、Intake、Atlas、Trace、Evidence 五个内嵌视图。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Active Request 卡片 | 当前示例请求和 Show Trace/Open Atlas/Review Sources 快捷入口。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Memory Loop Stages | 显示 raw source 到 eval/audit 的每一步数量和状态。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Overview Focus Grid | 当前关注 capability、atlas 高亮、待处理事项。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Retrieval Trace Preview | 预览 request -> concepts -> memory -> code -> prompt -> eval 的链路。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Engineering Workbench {#engineering-workbench}

- Route：`/workbench`
- 页面目的：需求分析和 PR Review 的工作台容器，旁边固定显示 context trust sidebar。
- 标注截图：

![Engineering Workbench annotated screenshot](annotated-screenshots/engineering-workbench-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Workbench 标题与 Trust 入口 | 说明工作台目的，右侧 Trust Center 链接用于打开检索审计。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Workflow Mode Switch | 在 Requirement Case 与 PR Review 两种工作模式间切换。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | 嵌入工作流区域 | 当前模式的实际表单和结果输出区。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Context Sidebar | 持续显示检测到的概念、检索 trail、context eval 和 active case。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Trust Center {#trust-center}

- Route：`/trust`
- 页面目的：检索可信度、prompt preview、eval/audit 和 human rating 的治理入口。
- 标注截图：

![Trust Center annotated screenshot](annotated-screenshots/trust-center-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Trust Center 标题 | 解释这是 review/governance 面板。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | 汇总数字 | 快速看 trail steps、scorecards、audit runs 数量。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Trust Tabs | 切换 Retrieval Trust 和 Eval & Audit。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | 嵌入治理视图 | 当前 tab 的实际 trust/audit 内容。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Settings {#settings}

- Route：`/settings`
- 页面目的：运行模式和 guardrails 的只读配置预览。
- 标注截图：

![Settings annotated screenshot](annotated-screenshots/settings-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Settings 页面说明 | 查看 frontend mock-only 状态和健康标识。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Runtime Mode | 查看 provider、API base URL、frontend mode、status。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Guardrails | 当前 demo 的安全边界：无付费外部 API、无真实公司数据、输出仅草稿、TestGen excluded。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

## 功能子页/可直达路由
### Knowledge Memory {#knowledge-memory}

- Route：`/knowledge`
- 页面目的：知识源搜索和 chunk 预览页面，用于查 domain docs/runbooks/incidents/Jira/PR/test docs。
- 标注截图：

![Knowledge Memory annotated screenshot](annotated-screenshots/knowledge-memory-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面说明与索引状态 | 说明当前搜索 demo_team synthetic knowledge pack。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | 搜索与筛选面板 | 输入 query、app、doc type、component、Top K 后搜索来源。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | 展开后的搜索表单 | 高级过滤条件，搜索后会自动折叠并更新结果。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Knowledge Source Tree | 按 source type 分组展示命中的 chunk，点击任意 chunk 查看右侧详情。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Chunk Preview | 查看选中 chunk 的摘要、概念标签、metadata 和 GitHub source link。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Knowledge Intake {#knowledge-intake}

- Route：`/knowledge-intake`
- 页面目的：把上传/导入的 source parse 成候选 memory cards，并经过 approve/promote 流程。
- 标注截图：

![Knowledge Intake annotated screenshot](annotated-screenshots/knowledge-intake-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Intake 标题 | 进入 source intake/review 工作台。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Sources Queue | 展示待处理 source、解析状态、reviewer、memory card 数量和目标 pack。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Upload Source | 上传 md/txt/docx/html/json；本地读取并解析成 proposed memory cards。 | 本地读取上传文件并生成 demo memory cards；需要人工 approve/promote。 |
| 6 | Review & Approve Console | 对选中 source 进行 re-parse、approve、promote，并记录 review comment。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Proposed Memory Cards | 展示解析出来的候选 memory cards、摘要、source span 和 retrieval tags。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Retrieval Tags | 解析出的概念标签，用于后续检索匹配。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 9 | Checks & Reviewer Notes | 系统检查和人工 review note 的审计说明。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Memory Atlas {#memory-atlas}

- Route：`/codebase`
- 页面目的：代码库 capability memory atlas，把业务能力、代码文件、测试、风险和 prompt 用途连接起来。
- 标注截图：

![Memory Atlas annotated screenshot](annotated-screenshots/memory-atlas-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Atlas 标题与 Repo 状态 | 说明当前索引的 repo 和 provider snapshot。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | 左侧 Atlas Rail | 查看 indexed repo、attention queue、trust states 和高级搜索。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Advanced Search | 按 query/topK 搜索代码 evidence，并选中第一个 match。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Selected Memory Hero | 当前选中 capability 的摘要、状态、trust 和 evidence 数量。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Capability Network | 点击 capability node 切换上下文，查看能力之间的关联。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Impact Map | 把能力拆成 source code、tests、docs，可点击具体文件/路径。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 9 | Prompt Assembly Trace | 说明 request 到 prompt slots 的组装步骤。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 10 | Evidence Library | 按 frontend/API/service/domain/tests 分组列出当前 capability 的 evidence。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 11 | Decision Inspector | 右侧查看为什么信任、风险缺口、概念、选中 evidence 和搜索 matches。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Retrieval Paths {#retrieval-paths}

- Route：`/graph`
- 页面目的：按业务概念查 docs -> code -> tests 的 evidence graph path。
- 标注截图：

![Retrieval Paths annotated screenshot](annotated-screenshots/retrieval-paths-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面标题与图谱状态 | 显示当前 demo repo 的 graph path ready 状态。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Find Retrieval Path 表单 | 输入 business concept/risk 和 topK 后 trace sources。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Graph Path Results | 点击结果选择某条 evidence path。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Why These Sources | 解释选中 path 中每个节点为什么进入 prompt context。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Prompt Boundary | 提醒哪些 docs/incidents/code/tests 会进入 context pack，并提供快捷 query。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Context Intelligence {#context-intelligence}

- Route：`/context-intelligence`
- 页面目的：展示 intent 到 source-backed context pack、prompt preview、logic chain 的完整组装过程。
- 标注截图：

![Context Intelligence annotated screenshot](annotated-screenshots/context-intelligence-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Context 页面说明 | 说明当前 caseId 和 context pack ready 状态。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Active Request Summary | 当前请求、trail/pack/evidence 的摘要计数。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Retrieval Eval Metrics | 衡量 coverage、freshness、source mix 等检索质量。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Retrieval Trail Timeline | 逐步展示 query、匹配 source 数和状态。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Context Pack Sections | 点击 section 查看该 section 的 guardrail 和 linked evidence。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Evidence Cards | 显示当前 section 绑定的 source excerpt、relevance 和 why selected。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 9 | Prompt Preview | 查看最终将送给模型的 system/developer/user/evidence instructions 预览。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 10 | Standardized Logic Chain | 标准化记录 input/output/evidence，方便审计和复盘。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### Requirement Case {#requirement-case}

- Route：`/requirements`
- 页面目的：把粗糙业务需求转为 evidence、impact map、澄清问题、scorecard 和 Jira draft。
- 标注截图：

![Requirement Case annotated screenshot](annotated-screenshots/requirement-case-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面目标与人工门禁 | 说明输出必须人工 review 后才能进 Jira。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Case Intake 表单 | 选择 execution mode、team/app/component/role/topK，输入 rough request 并分析。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Sources Used | 生成后展示检索到的来源和 source path。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Impact Map | 显示需求可能影响的系统区域、描述和置信度。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Evaluation Scorecard | 用分数和建议判断是否 Jira-ready 或仍需答案。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 8 | Role-specific Questions | 不同角色需要回答的问题，可保存答案回填到 case。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 9 | Jira-ready Draft | 查看/重新生成带人工答案的 Jira markdown 草稿。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### PR Review {#pr-review}

- Route：`/review`
- 页面目的：用 synthetic diff/Jira context 生成 evidence-backed PR review aid。
- 标注截图：

![PR Review annotated screenshot](annotated-screenshots/pr-review-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面目标与安全边界 | 明确不发 PR comment、不 approve/reject，只生成 review aid。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Review Input 表单 | 选择 mode/team/app/component/topK，输入 synthetic diff 和 Jira context。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Review Memory | 查看风险等级、eval grade、changed files、related code 和 sources。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Markdown Output | 生成可复制给 reviewer 的 markdown 摘要。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |

### TestGen Stub {#testgen-stub}

- Route：`/testgen`
- 页面目的：展示未来 TestGen provider 接口，但当前不生成测试、不写 repo。
- 标注截图：

![TestGen Stub annotated screenshot](annotated-screenshots/testgen-stub-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | 页面目标与 Stub 边界 | 说明这是 provider interface only，mock provider，无 repo 写入。 | 当前是接口演示，不会生成测试或写文件。 |
| 4 | 范围警告 | 提醒 unit-test generation 不在当前 UI phase。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Provider Stub Input | 输入 team、语言、repo path，保持 dry run only。 | 当前是接口演示，不会生成测试或写文件。 |
| 6 | Plan / Result | Plan Stub 预览要做的动作。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 7 | Safe Stub Report | Run Safe Stub 生成安全报告，证明不会写文件。 | 当前是接口演示，不会生成测试或写文件。 |

### Eval & Audit {#eval-audit}

- Route：`/audit`
- 页面目的：查看 deterministic scorecards、run history、human ratings 和 evidence coverage。
- 标注截图：

![Eval & Audit annotated screenshot](annotated-screenshots/eval-audit-annotated.png)

| 编号 | 区域 | 功能说明 | 使用目的/注意 |
| --- | --- | --- | --- |
| 1 | 全局左侧导航 | 主导航：DREAM brand、五个顶层页面、mock/demo 环境状态。 | 全局 shell，跨页面一致。 |
| 2 | 全局顶部栏 | 移动菜单按钮、当前产品标识、mock memory chip、Memory 快捷入口、demo 用户头像。 | 全局 shell，跨页面一致。 |
| 3 | Audit 页面说明 | 说明输出在 review-ready 前需要 eval 和人工评分。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 4 | Evaluation Scorecards | 分数、grade、recommendation 和 pass/warning/fail 状态。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 5 | Audit Runs Table | 点击 run 查看详情和评分。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
| 6 | Run Detail & Rating | 查看 provider、sources、warnings，并填写 usefulness/correctness/comment。 | 这是人工门禁/反馈区，用来证明输出不能自动发布。 |
| 7 | Ratings List | 展示当前 run 已保存的人类评分。 | 这是人工门禁/反馈区，用来证明输出不能自动发布。 |
| 8 | Evidence Coverage | 展示知识/代码/测试/历史等来源覆盖情况。 | 用于产品校验时确认该区域是否真的支持目标用户流程。 |
