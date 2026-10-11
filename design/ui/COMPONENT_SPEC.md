# 核心组件规范

以下是后续组件实现契约。静态原型复用CSS/helper与原生控件，不是生产组件库。已展示基本按钮/表格/抽屉/表单/状态/引用等；Multi Select、任意日期弹层、完整Tooltip/Popover与全部键盘roving属于规范覆盖，当前不声称均有完整实现。

| 组件 | Props / 数据 | 交互与变体 |
|---|---|---|
| Button | label/variant/disabled/action | primary/secondary/ghost/small，hover/focus/disabled；读操作不确认 |
| Input | value/label/error/required | 标准label与就地校验；不只依赖placeholder |
| Search | term/scope/result IDs | 全局Ctrl/Cmd K与本页搜索分开；Enter选结果，Esc返回 |
| Select | options/value/unknown bucket | native原型；固定口径、多状态与未知独立 |
| Multi Select | selected IDs/options | 规范已定义；生产用chip+弹层，不使用自由任意SQL |
| Date Range | field/start/end/timezone/as_of | 明确published/modified/observed，日级不伪装秒级 |
| Filter | predicates/coverage/cursor | 基础条件可见，高级折叠；条件chip可清除 |
| Badge | text/tone | 仅表达简短状态，必须有文案 |
| Status Badge | field Claim/status/scope | 四态，只针对Claim，不表示全条无条件可信 |
| Risk Badge | CVSS version/source/severity | 严重/高危/中危/低危与核验独立 |
| Tag | type/ecosystem/edition | 中性背景，不冒充风险状态 |
| Tabs | type/active/available counts | 漏洞/事件/论文/标准/政策；不新增一级导航 |
| Card | title/body/action | 仅必要聚合容器，详情用连续文章，不每段一张卡 |
| Metric Card | distinct count/window/filter | 最多4—6；可进入同条件结果，不含benchmark占位数字 |
| Table | stable IDs/columns/rows/revision | 六组信息；unknown/N/A/源日期不被截断 |
| Pagination | cursor/count/as_of | 返回保留条件/位置；换条件回首段 |
| Tooltip | short clarification | 键盘focus可读；不可承载唯一Evidence |
| Popover | local filter/selection | 用于选择，不嵌套多个调查详情 |
| Drawer | origin/Claim/revision | Evidence/SyncRun就近展开；Focus trap、Esc、返回原字段 |
| Modal | draft/preview/permission/revision | 写操作预览或人工登记；关键决定不能点击背景误提交 |
| Toast | actual result/request ID | 轻反馈；不得把queued写成成功 |
| Empty State | initial scope/capabilities/action | 未登记/未启用与查询无匹配区别 |
| Error State | failed request/retry/partial facts | 就地重试；写操作先查幂等结果 |
| Skeleton | loading area/existing snapshot | 无0/无假动画进度；原条件保留 |
| Timeline | event type/source/date/Claim | 事实变化、证据链接，未知源日期另标 |
| Evidence Card | publisher/type/excerpt/times/URL/status | Claim上下文明确；定位/hash折叠；许可受限不保证全文 |
| Source Badge | source name/provider/lineage | 用户见发布者名称，内部SourceID在技术展开 |
| Conflict Alert | same-scope candidates/review ID | 局部不夸张，先比较scope/CVSS版本/时间 |
| Review Panel | candidate A/B/reason/actor/revision/audit | 确认A/B、缺证、暂缓；审计原值/新值/原因 |
| Asset Match Badge | asset/package/version/impact/reason | 三态：受影响/不受该漏洞影响/无法判断 |
| POC Status | association/usability/scope/evidence | 关联与可用性两轴；未发现不等于不存在 |
| Patch Status | association/SHA/branch/Evidence | 候选/已关联/未发现或未获取；不表示环境修复成功 |
| Agent Tool Step | tool/range/count/source/status | 实际工具事件摘要，无私有思维链/SQL/凭证 |
| Citation | EvidenceID/ClaimID/revision | 紧邻结论可点，保持query和来源scope |

数据取自COMPONENT_DATA_MAPPING（57项UX元素与24个API提案）。原型未实现的控件须在真实前端阶段基于相同token和交互规范实现，不能用一个无响应按钮冒充完成。

## 组件组合

Table内ID/标题链接与Evidence按钮独立；status和severity同一行并列而不混成一个色标。Evidence Drawer包含Claim header→来源分组→Evidence Card→locator展开→Review跳转。Review Panel包含对照、理由、预览确认、审计回链。Agent Result包含范围chips、结构化Findings、Citation、Tool Steps及partial缺口；没有第二个全局聊天窗。

Modal/Drawer有aria-modal、可读标题、Focus trap，关闭回原触发元素；原型内存模拟提交保留上游观察，人工记录值/actor/理由独立。生产写入需后端权限和并发契约，不得从按钮状态推断授权。资产模糊版本就地说明，不自动补成版本。
