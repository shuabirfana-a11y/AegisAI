# 增量同步与恢复设计

| 源 | Initial Sync | Incremental Sync | Checkpoint / 补漏 |
|---|---|---|---|
| CVE_LIST | 一次官方Git基线，固定SHA；首期处理当前声明年份/AI白名单，完整raw按取用范围留存；历史年份单列回补 | fetch目标commit，确认前后祖先关系；diff变更/删除JSON路径；记录CNA/Program/ADP原文和REJECTED状态 | 目标SHA与已完成路径；只有raw/标准记录持久化成功才推进整体SHA。历史重写/非祖先则比较已用路径hash并重建基线，不能静默跳过 |
| OSV | 一次PyPI生态dump（或有限种子明确披露范围），记录generation/ETag/hash及基线完成时间；withdrawn与EMPTY范围有恢复说明 | 官方modified_id.csv反向时间排序；流式取新于watermark减24h的ID，完整一行解析；同时间ID全部处理，再GET /v1/vulns/{id} | (modified timestamp,已处理ID集合)；不能仅单ID tie-break丢同秒记录。watermark不晚于所有成功记录；失败ID独立待补，成功时间不冒进。停机超预算或索引机制变化则做生态checkpoint对账；EMPTY/withdrawn纳入周期身份核对 |
| KEV | 一次完整JSON；count=条目数，CVE ID唯一，schema/hash校验；保留catalogVersion/dateReleased | If-None-Match；304只加成功观察，无新raw；200内容hash改变后按cveID+条目hash比较新增/修订/撤销 | ETag/hash/catalogVersion；不存在官方逐条delta API。修改时获取完整约1.8MB快照是该源必要方式，不是每轮全量刷新 |
| 厂商/GitHub | 三个批准repo的公开advisory分页快照；精确reference路径才扩代码端点 | ETag + Link；仅端点支持才用updated/since过滤；小advisory列表按hash对比以发现撤销和更正 | per-repo、per-endpoint、查询范围+分页位置、整体窗口；不把Issue since套到security-advisories；commit文件分页/截断需标完整性 |
| EPSS | 少量关注CVE取某日分数；全量需要时每日官方CSV一次 | 新date/model_version是新观察，即使概率未变；同日更正按hash修订；不用CVE modified当分数更新 | 日期+model+hash；无分数=unknown，历史补查日与今日不混 |
| CISA Vulnrichment | 首先读CVE原文CISA ADP，不新增网络任务；独立repo若启用则固定SHA基线 | Git diff按CVE更改；与CVE ADP以provider+记录修订/hash检测同份转载 | commit/记录hash；SSVC timestamp与model_version保留；旧Exploitation=none不覆盖后来的KEV正证据 |
| arXiv | 固定主题查询、start/max_results，按lastUpdatedDate取近期元数据；无CVE也保存paper ID | 周期按lastUpdatedDate降序分页到watermark−7天；每entry ID+vN/hash去重 | 查询版本/分页/updated及ID；返回结果集可能变化，不保证CDC完整性。周期复查已用paper新版本，升级全域回补时另用官方OAI-PMH方案 |
| RSS/Atom | 一次feed窗口，记录真实覆盖最早/最晚条目 | 条件GET + guid/id/link/entry hash；sameID内容变保留修订 | ETag/Last-Modified + seen-ID；丢出feed不是删除，超窗口停机允许按批准归档补查或报告缺口 |
| SAMR/NIST/CAC | 固定官方标准清单/目录与已批准文档；metadata/title/日期/版本/links | 6h观察目录/清单详情；有条件headers则用，没有则比较响应/正文hash；新增链接经域/类型批准后获取 | 栏目分页与seen URL/hash；源没有modified时留null，观察变化时间独立保存；区分语种/计划/草案/现行标准；修订状态只用正式依据 |
| ATLAS/OWASP | 固定commit/edition/schema版本 | 每周Git更新diff、schema核对；版本不覆盖 | commit+edition；兼容性变更暂停标准化并保存raw |

所有“24h重叠、7d重叠、6h/1h/每日/每周”等为团队起始配置，随观察修订，不是上游SLA或已测时效。首次完成时以原发布时间−first_retrieved_at测新增前瞻延迟；历史回补单列，发布日期缺失保留unknown。

运行状态概念：PLANNED→RUNNING→SUCCEEDED / PARTIAL / FAILED / RATE_LIMITED / NEED_REVIEW。网络成功不等于标准化成功；单条schema失败raw留存隔离，不把旧checkpoint推进越过缺口。覆盖范围/known gaps必须能查看。

通用预算：单source并发1、连接10s/读取30s起始值；最多3次重试，指数backoff 2/4/8s加jitter，整体任务预算10min。429遵守Retry-After，GitHub403先看rate-limit reset/secondary策略；401/授权403不重试绕过。5xx/timeout有限重试后排队，下轮回补。此配置须在实现阶段测量，不是当前已跑调度器。

Checkpoint分“已获取原文”和“已完成下游处理”两种；源观察高水位与失败队列同一可恢复提交，事务实现留数据库阶段。分页途中失败续同冻结窗口/游标，若游标失效则重扫带重叠窗口并幂等。解析器版本升级从raw replay，不重新访问全站。原文存储/数据库失败不写成功标记。源故障互相隔离，陈旧源不返回无条件最新结论。

条件请求只能在内容缓存还存在时发出；本轮已见ETag/Last-Modified头，未对所有服务实测304，标为实现前需验证的协商能力，不宣称全部服务已支持。
