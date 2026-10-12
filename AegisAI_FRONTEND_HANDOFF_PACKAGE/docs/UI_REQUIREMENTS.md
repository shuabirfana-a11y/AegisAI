# 七个页面的 UI 与数据需求

本文件描述前端团队应实现或完善的页面。现有七页和已有 UX/UI 继续复用；本轮未修改页面。接口真实性以 [API 状态](../api/API_STATUS.md) 为准，视觉原型中的数据不代表 HTTP 能力已开放。

## 共同规则

- 工作台采用左侧导航、页头和内容区。默认桌面左栏 216px、页头 64px、主区 28px 边距；1280px 宽度可调整为 200px/22px。沿用现有设计，不新建另一套视觉系统。
- 中文正文使用本机 Segoe UI/Microsoft YaHei UI 回退，正文约 14px；ID、版本、哈希使用等宽字体。外部字体不能成为演示依赖。
- 严重度、可信状态、任务状态分别显示带文字标签。未知值单独显示，不能以绿色或空字符串代替。状态不只靠颜色表达。
- 外部公告和博客按不可信文本渲染，不把来源正文直接作为 HTML 执行。公开 Trace 只展示步骤、工具、时长和结果，不展示隐藏推理、密钥或内部控制上下文。
- `affected=null` 是未知，不是“不受影响”；PoC 候选不是验证成功；补丁存在不代表资产已修复；`confidence` 不是测得的准确率。
- 时间显示明确时区和口径：源发布时间、采集时间、评估时间、答案生成时间各自保留。缺时间显示“未提供”，不拿当前时间补齐。
- Mock/测试回执的标签在结果和截图中可见。Mock 模式不伪装成实际后台执行；未提供数值的统计不补成零。

## 页面要求

| 页面 / 当前真实路由 | 主要内容与操作 | 现有数据来源 | 尚缺或受限 |
|---|---|---|---|
| 情报总览 `/dashboard` | 当前情报范围、资产风险摘要、重点漏洞、待复核入口、源健康 | health、assets/overview、vulnerabilities、reviews | 全局趋势/新增量没有专用统计 API；资产指标需权限 |
| 漏洞中心 `/vulnerabilities` | 搜索、来源/AI相关性筛选、分页、详情入口 | vulnerabilities | q 只匹配 canonical_id；严重度/任意版本等未提供筛选不能假称服务端支持 |
| 漏洞详情 `/vulnerabilities/{id}` | 漏洞身份、来源断言、版本范围、CVSS/CWE、候选 PoC/Patch、Claims、Evidence、冲突、时间线 | 详情聚合及六个分页子资源 | 派生证据 ID 未必可走 evidence UUID 接口；未知与冲突需显式展示 |
| 资产风险 `/assets` | 资产/组件版本、匹配状态、风险快照、依据与处置入口 | assets、overview、risks、历史快照/变更读取 | 写入/版本修改/SBOM/重算被代理拦截；专业 RiskArtifact 不在此 HTTP 返回中 |
| 证据复核 `/reviews` | 复核队列、Claim、支持/反对证据、理由和审计 | reviews 及详情；资产专用 reviews 需权限 | resolve 后端存在但被代理拦截；无 GET claims/{id} |
| 智能调查 `/assistant` | 输入范围、阶段进度、专业 Agent 链、证据、Gate、可信答案、取消/历史 | 新调查八操作可接；Mock须明确标记 | Phase 11-D 八个HTTP操作已开放；默认Mock规划失败，不能用旧 result.answer 冒充 AnswerEnvelope |
| 系统状态 `/system` | health、源状态、同步历史、失败摘要 | health、sources、sync-runs | CPU/内存/模型用量遥测、实时推送、主动重试入口未提供 |

## 漏洞中心与详情

表格优先展示身份/产品、严重度、利用与 PoC 信号、修复、Claim 核验、更新时间。实际列表未返回的富化字段不要逐行猜测；可在详情展示，或明确需要聚合接口。详情顺序：身份 → 影响范围 → 风险依据 → 修复 → Claim 与证据 → 冲突 → 时间线。

Evidence 抽屉显示证据 ID、Claim ID、来源标识、引用定位、哈希、核验结果和快照来源。来源缺内容时显示定位摘要；不要根据 ID 虚构发布者名称。优先同页打开抽屉，保留原表格筛选和滚动位置。

## 智能调查

输入至少包含问题和可选目标/资产/组件版本。提交完整 InvestigationRequest 的字段是 `planner_input.query`、`time_scope`、`user_context`、`investigation_options`，不是顶层 query/asset_scope/options。当前真实 HTTP 仅有旧 QueryRequest，两种协议必须分开。

进度区使用 `current_stage` 表示执行阶段，`overall_status` 表示总体结果。结果区分别显示 Gate 的 `integration_status` 和答案的 `answer_status`。**COMPLETED + INCOMPLETE 是合法结果**，不能改成成功。完整交付还需没有恢复待确认，并有可用且引用一致的 Gate/答案。

Agent 展示按真实 `run_id`、`task_statuses`、`tool_calls` 和 Artifact 引用构建；不按页面固定播放动画造出执行成功。Trace 中不含明确 agent_id 时不能把自定义推断当后端字段。结果区展示范围、摘要、风险、建议、已核验 Claim、争议 Claim、引用、警告、未解决事项和历史快照时间。

取消中显示 `cancel_requested=true`；只有总体或实际终态 CANCELLED 才显示已取消。`recovery_required=true` 显示“恢复待确认”，提供手动刷新及联系负责人，不自动新建调查。

## 通用状态与验收

| 状态 | 页面行为 |
|---|---|
| Loading | 保留页面范围，局部加载；不要先显示零条/安全 |
| Empty / No Result | 说明查询范围，无结果不证明漏洞不存在 |
| Error / Timeout | 保留输入与上次快照，可重试读取；提交结果不明时不得盲目换 key 重发 |
| Unauthorized / Forbidden | 显示权限说明，停止重复自动重试 |
| Partial / Stale | 显示覆盖不足、失败来源、快照时间；保留可用结果 |
| Conflict / Review Required | 对照冲突证据与作用范围，显示未解决原因和复核入口 |
| Cancel Requested / Cancelled | 区分取消请求与确认终态 |
| API_NOT_EXPOSED / PROXY_BLOCKED | 对应动作禁用或只在明确 Mock 模式演示 |
| 未知枚举 | 保留原状态文本，使用中性展示，不默认归入成功 |

验收应覆盖 1440/1280/窄屏、表格局部横滚、键盘 Tab/Enter/Esc、可见焦点、弹窗关闭后返回焦点、长证据/版本、空数组/null、401/404/409/422/503、重复提交和乱序轮询响应。旧成功回执和未完成回执都要走一遍；不能只验证截图中的 PASS。
