# UI元素—组件—数据—交互—后端映射

沿用Phase 3全部57个ID，API为24项未实现提案。原型内Mock不代替正式服务。表中Source是输入出处，不是宣称官方源提供人工审计或聚合数字。组件名为前端建议，不创建生产工程。

| UI Element / 页面 | Component | Data Required | Interaction | Backend Dependency / 分期 |
|---|---|---|---|---|
| G01 / GLOBAL 导航及可用动作 | AppShell / GlobalSearch / ContextLink / Feedback | 实际开放能力、read/write权限、登录会话 | 读取；导航及可用动作 | 能力与最小权限；A01；P0；BACKEND REQUIRED |
| G02 / GLOBAL 全局搜索/结果跳转 | AppShell / GlobalSearch / ContextLink / Feedback | 实体ID/类型、搜索范围、可访问产品/资产 | 读取；全局搜索/结果跳转 | 实体搜索与授权过滤；A02；P0；BACKEND REQUIRED |
| G03 / GLOBAL 返回/面包屑/锚点 | AppShell / GlobalSearch / ContextLink / Feedback | origin、filters、cursor、scroll、revision、as_of | 读取；返回/面包屑/锚点 | 本地路由上下文；仅本地上下文；P0；LOCAL ONLY |
| G04 / GLOBAL 请求重试/范围刷新 | AppShell / GlobalSearch / ContextLink / Feedback | 请求ID、最新revision/coverage、旧快照 | 读取；请求重试/范围刷新 | 统一错误与快照协议；A01；P0；BACKEND REQUIRED |
| G05 / GLOBAL 复制分享链接 | AppShell / GlobalSearch / ContextLink / Feedback | 公共entity/revision/anchor；私有资产只在授权会话上下文 | 读取；复制分享链接 | 本地URL构造及访问权限复核；A01；P0；BACKEND REQUIRED |
| D01 / DASH 时间窗与范围/刷新 | MetricCard / IntelList / TrendChart / SourceSummary | window、as_of、覆盖产品/来源及快照 | 读取；时间窗与范围/刷新 | 一致快照与范围摘要；A03；P0；BACKEND REQUIRED |
| D02 / DASH 新增/更新/知识计数及进入列表 | MetricCard / IntelList / TrendChart / SourceSummary | 首次发现distinct entity、新修订entity、knowledge type计数及过滤器 | 读取；新增/更新/知识计数及进入列表 | 去重后变化聚合；A03, A04；P0；BACKEND REQUIRED |
| D03 / DASH 值得关注/风险信号及进入详情 | MetricCard / IntelList / TrendChart / SourceSummary | CVSS版本、PoC关联状态、KEV目录、EPSS日期、变化依据 | 读取；值得关注/风险信号及进入详情 | 可解释风险信号聚合；A03, A05；P0；BACKEND REQUIRED |
| D04 / DASH 近期情报列表/时间线及类型跳转 | MetricCard / IntelList / TrendChart / SourceSummary | ID/类型、变化摘要、源日期和观测日期 | 读取；近期情报列表/时间线及类型跳转 | 类型化事件与知识聚合；A03, A04, A07, A10；P0；BACKEND REQUIRED |
| D05 / DASH 来源摘要及异常跳转 | MetricCard / IntelList / TrendChart / SourceSummary | 实际启用数、类别、stale/failed、last_success_at | 读取；来源摘要及异常跳转 | 运行状态聚合；A03, A20, A21；P0；BACKEND REQUIRED |
| D06 / DASH 资产影响入口 | MetricCard / IntelList / TrendChart / SourceSummary | 受影响登记组件/漏洞distinct数，库存revision | 读取；资产影响入口 | 授权Asset Matching；A03, A13；P1；BACKEND REQUIRED |
| D07 / DASH 待复核入口 | MetricCard / IntelList / TrendChart / SourceSummary | 开放任务distinct数、风险及触发原因 | 读取；待复核入口 | Review队列聚合；A03, A14；P1；BACKEND REQUIRED |
| C01 / CENTER 类型切换/搜索/清空 | TypeTabs / Filter / Table / Pagination | record_type、外部ID/关键词、各类型结果计数 | 读取；类型切换/搜索/清空 | 统一类型检索；A04；P0；BACKEND REQUIRED |
| C02 / CENTER 基础及高级筛选/排序/分页 | TypeTabs / Filter / Table / Pagination | 产品生态、AI类别及依据、CVSS version、KEV/PoC/fixed/date/Claim状态、cursor | 读取；基础及高级筛选/排序/分页 | 确定性筛选、未知桶及排序；A04；P0；BACKEND REQUIRED |
| C03 / CENTER 漏洞行及详情跳转 | TypeTabs / Filter / Table / Pagination | 身份、产品、评分出处、PoC关联、修复、KEV、字段核验、updated | 读取；漏洞行及详情跳转 | 精简漏洞投影；A04, A05；P0；BACKEND REQUIRED |
| C04 / CENTER 论文/标准/政策/事件行及详情跳转 | TypeTabs / Filter / Table / Pagination | 作者/发布机关、ID/版次/状态、时间、related entities、证据 | 读取；论文/标准/政策/事件行及详情跳转 | 知识类型投影与详情；A04, A10；P0；BACKEND REQUIRED |
| C05 / CENTER 资产命中筛选 | TypeTabs / Filter / Table / Pagination | 授权资产ID、affected/not_affected/unknown | 读取；资产命中筛选 | 授权资产匹配筛选；A04, A13；P1；BACKEND REQUIRED |
| C06 / CENTER 结果范围/未知说明 | TypeTabs / Filter / Table / Pagination | 本次已查范围/未接入范围、撤销记录、部分源失败 | 读取；结果范围/未知说明 | Coverage与查询执行摘要；A04；P0；BACKEND REQUIRED |
| V01 / DETAIL 身份/描述/状态 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | CVE/GHSA别名、title、record_status、源语言/日期 | 读取；身份/描述/状态 | 实体详情与状态修订；A05；P0；BACKEND REQUIRED |
| V02 / DETAIL 影响产品/包/版本/修复及查看证据 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | package/ecosystem/PURL、原range/events/explicit versions、explicit fixed、scope/ClaimID | 读取；影响产品/包/版本/修复及查看证据 | 版本契约与字段provenance；A05, A08；P0；BACKEND REQUIRED |
| V03 / DETAIL CVSS/EPSS/KEV/利用状态及查看证据 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | cvss版本vector/base/provider；epss/date/model；KEV完整目录时间；SSVC scope | 读取；CVSS/EPSS/KEV/利用状态及查看证据 | 风险字段独立保留与溯源；A05, A08；P0；BACKEND REQUIRED |
| V04 / DETAIL PoC关联/可用性及展开证据 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | candidate/related、公开链接；独立核验记录/授权适用环境或unknown | 读取；PoC关联/可用性及展开证据 | PoC关系与可用性独立记录；A06, A08；P0；BACKEND REQUIRED |
| V05 / DETAIL 处置建议/厂商链接/修复版本 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | explicit fixed、厂商建议及适用包分支、未提供原因 | 读取；处置建议/厂商链接/修复版本 | 修复事实/建议出处；A05, A06, A08；P0；BACKEND REQUIRED |
| V06 / DETAIL Patch/Fix Commit | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | 候选commit完整SHA/PR/branch、关联状态、Evidence | 读取；Patch/Fix Commit | Patch关联（未实现时隐藏）；A06, A08；P1；BACKEND REQUIRED |
| V07 / DETAIL 论文/分析及知识关联跳转 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | 文献元数据、relation scope、关系候选依据 | 读取；论文/分析及知识关联跳转 | 关系检索与知识详情；A06, A10, A08；P0；BACKEND REQUIRED |
| V08 / DETAIL 证据/Claim状态/差异 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | Claim scope/revision、EvidenceID、support/refute/context、lineage | 读取；证据/Claim状态/差异 | Evidence Store与字段核验；A08, A09；P0；BACKEND REQUIRED |
| V09 / DETAIL 同范围冲突/进入复核 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | 真实冲突ID、两候选、范围及review ID | 读取；同范围冲突/进入复核 | 冲突检测与Review；A05, A14, A15；P1；BACKEND REQUIRED |
| V10 / DETAIL 时间线及事件证据 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | 源发布/修改、系统首次发现、PoC关系/KEV/fix变化，事件证据 | 读取；时间线及事件证据 | 证据化事件时间线；A07, A09；P0；BACKEND REQUIRED |
| V11 / DETAIL 继续询问这个漏洞 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | entityID/revision、当前Claim及问题、授权上下文 | 读取；继续询问这个漏洞 | 受控问答任务；A17, A18；P0；BACKEND REQUIRED |
| V12 / DETAIL 当前资产影响摘要/查看清单 | DetailSection / RiskBadge / PocStatus / PatchStatus / EvidenceTrigger | 授权inventory revision、三态匹配和依据 | 读取；当前资产影响摘要/查看清单 | Asset Matching；A13；P1；BACKEND REQUIRED |
| E01 / EVIDENCE 来源/原文摘要/时间/URL | EvidenceDrawer / EvidenceCard / Citation | publisher/sourceID、excerpt、published/retrieved、original URL | 读取；来源/原文摘要/时间/URL | 证据内容与许可/权限控制；A09；P0；BACKEND REQUIRED |
| E02 / EVIDENCE 范围/多来源/lineage比较 | EvidenceDrawer / EvidenceCard / Citation | Claim/raw revision、scope、支持反驳关系、原始发布者与转录链 | 读取；范围/多来源/lineage比较 | Claim与来源链检索；A08, A09；P0；BACKEND REQUIRED |
| E03 / EVIDENCE 原始定位/历史证据/分享 | EvidenceDrawer / EvidenceCard / Citation | raw hash、JSON Pointer/页码/span、已取raw受限读取、permalink | 读取；原始定位/历史证据/分享 | 不可变证据版本定位；A09；P0；BACKEND REQUIRED |
| E04 / EVIDENCE 进入对应复核/返回原字段 | EvidenceDrawer / EvidenceCard / Citation | reviewID/读写权限，返回Claim anchor/revision | 读取；进入对应复核/返回原字段 | Review及导航上下文；A15, A01；P1；BACKEND REQUIRED |
| K01 / KNOWLEDGE 知识详情/原文/版本/关联/询问 | KnowledgeDetail / SourceBadge / Citation | type、ID、版次/status、publisher/author、dates、links/ClaimID | 读取；知识详情/原文/版本/关联/询问 | 共享知识详情及引用问答；A10, A08, A17；P0；BACKEND REQUIRED |
| R01 / REVIEW 问题队列/筛选/进入任务 | ReviewPanel / ConflictAlert / Modal / AuditTimeline | 对象、问题类型、风险理由、候选、证据数及创建日期 | 读取；问题队列/筛选/进入任务 | Review过滤及权限；A14, A15；P1；BACKEND REQUIRED |
| R02 / REVIEW 对照范围/候选A/B/证据 | ReviewPanel / ConflictAlert / Modal / AuditTimeline | 原结论、候选、生态/版本/分支/date/CVSS version、lineage | 读取；对照范围/候选A/B/证据 | 同scope事实对照；A15, A08, A09；P1；BACKEND REQUIRED |
| R03 / REVIEW 确认A/B/证据不足/暂不判断/备注 | ReviewPanel / ConflictAlert / Modal / AuditTimeline | 选择值、理由、review revision、actor和幂等请求键 | 人工写入；确认A/B/证据不足/暂不判断/备注 | 权限、并发校验及决策审计；A16；P1；BACKEND REQUIRED |
| R04 / REVIEW 审计历史/回详情 | ReviewPanel / ConflictAlert / Modal / AuditTimeline | 原/后结论、actor/time/reason、证据版本、entity/anchor | 读取；审计历史/回详情 | 不可覆盖审计与详情回链；A15, A05；P1；BACKEND REQUIRED |
| R05 / REVIEW 刷新后比较/恢复草稿 | ReviewPanel / ConflictAlert / Modal / AuditTimeline | 409当前revision、草稿、差异及重新提交范围 | 读取；刷新后比较/恢复草稿 | 并发差异返回；A15, A16；P1；BACKEND REQUIRED |
| S01 / ASSET 组件清单/查找/选择 | AssetList / AssetMatchBadge / Form / Table | 授权名称、ecosystem/package、原始精确version与校验状态 | 读取；组件清单/查找/选择 | 最小资产清单权限；A11；P1；BACKEND REQUIRED |
| S02 / ASSET 人工添加/确认登记 | AssetList / AssetMatchBadge / Form / Table | name/ecosystem/package/exact version、歧义原因、错误定位 | 人工写入；人工添加/确认登记 | 资产登记校验与审计；A12；P1；BACKEND REQUIRED |
| S03 / ASSET 影响三态/未知原因 | AssetList / AssetMatchBadge / Form / Table | inventory revision、matched entity、range scope、reason/evidence | 读取；影响三态/未知原因 | 生态版本匹配；A13, A08；P1；BACKEND REQUIRED |
| S04 / ASSET 优先处置列表/排序解释/详情 | AssetList / AssetMatchBadge / Form / Table | 匹配证据、KEV收录/目录时间、PoC状态、CVSS版本、明确fixed及用户业务关键性 | 读取；优先处置列表/排序解释/详情 | 可解释规则排序；A13, A05, A06；P1；BACKEND REQUIRED |
| S05 / ASSET 分析为什么影响我 | AssetList / AssetMatchBadge / Form / Table | 资产ID和inventory revision、漏洞/ClaimID；问题 | 读取；分析为什么影响我 | 授权资产上下文问答；A17, A18；P1；BACKEND REQUIRED |
| Q01 / QA 问题输入/推荐问题/提交 | QuestionScope / AgentToolStep / Findings / Citation | question、会话、entity/Claim上下文、as_of/time zone/coverage | 读取；问题输入/推荐问题/提交 | 问答任务接入与范围澄清；A17；P0；BACKEND REQUIRED |
| Q02 / QA 任务过程/取消/重试 | QuestionScope / AgentToolStep / Findings / Citation | 工具名、参数范围/状态/结果数、过滤原因、query_id；取消结果 | 读取；任务过程/取消/重试 | 真实任务公开事件与生命周期；A18, A19, A17；P0；BACKEND REQUIRED |
| Q03 / QA 回答/未知部分/引用 | QuestionScope / AgentToolStep / Findings / Citation | 有Claim引用的结论、适用范围、partial reason、snapshot revision | 读取；回答/未知部分/引用 | 可核验证据回答；A18, A08, A09；P0；BACKEND REQUIRED |
| Q04 / QA 相关漏洞列表/回详情 | QuestionScope / AgentToolStep / Findings / Citation | entityID/revision、相关产品与来源、匹配过滤条件 | 读取；相关漏洞列表/回详情 | 受控结果投影及详情回链；A18, A05；P0；BACKEND REQUIRED |
| Q05 / QA 相关知识/来源/跨文档引用 | QuestionScope / AgentToolStep / Findings / Citation | knowledgeID/type/edition、EvidenceID、source/provider | 读取；相关知识/来源/跨文档引用 | 文档检索与关系工具；A18, A10, A09；P0；BACKEND REQUIRED |
| Q06 / QA 相关资产/为什么优先 | QuestionScope / AgentToolStep / Findings / Citation | 授权assetID/inventory revision、影响三态、解释因子 | 读取；相关资产/为什么优先 | 授权资产工具；A18, A13；P1；BACKEND REQUIRED |
| Q07 / QA 澄清/续问/原查询恢复 | QuestionScope / AgentToolStep / Findings / Citation | 缺失参数、先前query_id与scope、明确新时间窗 | 读取；澄清/续问/原查询恢复 | 会话上下文及实际范围；A17, A18；P0；BACKEND REQUIRED |
| Y01 / SYSTEM 来源表/筛选/查看最近失败 | SourceTable / StatusBadge / SyncRunDrawer | 注册SourceID、enabled、运行状态、类别及coverage | 读取；来源表/筛选/查看最近失败 | 来源注册与真实运行聚合；A20, A21；P0；BACKEND REQUIRED |
| Y02 / SYSTEM 来源时间/数量/延迟/下次计划 | SourceTable / StatusBadge / SyncRunDrawer | last_success/newest source date、fetched/normalized/new/updated/failed、retry/latency samples/next_scheduled | 读取；来源时间/数量/延迟/下次计划 | SyncRun统计与调度时间；A20, A21；P0；BACKEND REQUIRED |
| Y03 / SYSTEM 任务历史/失败筛选/详情 | SourceTable / StatusBadge / SyncRunDrawer | runID、source/time/status、范围、尝试、恢复关系 | 读取；任务历史/失败筛选/详情 | SyncRun历史查询；A21, A22；P0；BACKEND REQUIRED |
| Y04 / SYSTEM 失败详情/脱敏错误/重试 | SourceTable / StatusBadge / SyncRunDrawer | 错误码/request ID、checkpoint、重试权限/queued/new runID | 运维写入；失败详情/脱敏错误/重试 | 失败隔离与受控重试；A22, A23；P0；BACKEND REQUIRED |
| Y05 / SYSTEM 实际健康摘要 | SourceTable / StatusBadge / SyncRunDrawer | 已监测API/Collector/Queue及observed_at或NA | 读取；实际健康摘要 | 已有监控摘要；A24；P0；BACKEND REQUIRED |
## Normalized字段与UI View Model

external_ids→身份链接；record_type→类型Tab/知识模板；package.ecosystem/name/PURL→产品/包；affected_versions原expression/events→原范围+解释；fixed_versions仅explicit fixed→修复事实；cvss数组→分版本/来源Badge，不平均；epss.date/model→预测日期；exploitation/KEV目录→已收录/未在该次目录/未知；field_provenance/Claim/Evidence/raw version→可点击依据。

PoC association与usability是独立状态；Review人工决策另层，不能覆盖原Observation；资产匹配三态及reason、inventory revision；Source/SyncRun聚合来源是内部运行数据，研究checked_at不能冒充last_success。null表示未知，[]仅真实空集合；reason not_provided/unsupported/ambiguous/not_fetched/withdrawn用户文案保留。

原型使用简化flat View Model，替换为服务数据时需适配上述契约并校验。没有源→显示未知而非默认绿色；没有后台能力→不启用按钮/指标；没有授权→不返回私有对象。API响应需coverage/revision/as_of/partial/error/request_id；审核需expected_revision/actor/time/before/after/reason/Evidence和幂等key。仅本地G03无网络依赖，其余BACKEND REQUIRED。

完整来源字段优先级沿用research/data_sources/SOURCE_FIELD_MAPPING，不改变首批CVE_LIST/OSV/CISA_KEV或有限第二批。论文/标准/政策和实际Agent问答M1/P0；资产/冲突写复核/Patch增强P1。
