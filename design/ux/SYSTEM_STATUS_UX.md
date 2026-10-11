# 系统运行 UX

任务：JTBD-13。从总览异常source进入即定位对应源最近失败run，不要求用户翻日志猜故障。页面证明实际自动运行时必须用运行数据，研究checked_at不是最后成功同步。

## 来源表[Y01/Y02]

默认仅实际启用源；“全部/计划/暂停”可切换，计划记录清楚PLANNED。表格第一组Source/业务类别/状态，第二组最后成功和最新源记录时间，第三组本次量/失败与延迟/下次计划，长指标在行展开，避免堆20列。

| 字段 | 含义及未知规则 |
|---|---|
| 状态 | 未启用/计划、正常、部分失败、失败、暂停；stale为独立时效提示。绿色正常只能来自实际成功run |
| 最后成功 | last_success_at与run ID；失败/partial不覆盖上次成功，首次未成功为“尚无” |
| 最新源记录时间 | 原source published/modified最大值及字段口径，缺日期为未知；不是系统取数时间 |
| 本次数量 | fetched/normalized/new/updated/duplicate/failed分别标，抓取数不等于新增实体；run未完成为已处理进度 |
| 失败次数 | 所选时间窗失败run和attempt分开，重试不当新业务记录 |
| 延迟 | published→首次retrieved，注明样本量/无日期排除数/范围；均值、P50/P95只有足够实际样本才显示，0样本NA |
| 下一次同步 | 调度器真实next_scheduled_at及是否暂停/退避，未部署为未计划，不由前端猜 |
| 覆盖 | 包生态、产品白名单、时间/基线完成情况、类别口径；17入口不能等于17类别 |

目前Phase 2所有配置enabled=false/last_success_at=null，首次设计/未来上线前应显示计划状态，不展示成功或实时在线。ETag/304能力研究也不证明实际run已发生。

## 同步历史与失败详情[Y03/Y04]

按source、时间、status过滤，列表显示run ID/范围、开始结束、状态/计数、尝试号与关联恢复任务。点失败子视图展示错误码和脱敏解释、request ID、检查点/已处理与失败范围、退避和下一次计划。不要显示token、连接串或原始私有资产。

“重试本次失败”仅运维retry权限、恢复同范围、由服务限额/幂等/队列校验。202返回排队及新run ID，UI显示queued；仅真实结束后显示成功；源仍离线显示退避/暂停选项说明。默认读用户不能重试；不存在任意外站URL采集按钮。

半成功任务要记录已成功范围、失败集合与后续恢复；不能把partial算全量成功或提前推进覆盖水位。重试不会重复新增相同主体；检查点/回补设计由Phase 2约束，UX只呈现真实执行结果。

## 可选健康摘要[Y05]

只显示已真实接入监测的API/Collector/Queue状态和观测时间；没有监控展示“未接入”或不显示，不造CPU/队列曲线、Kubernetes节点和99.99%在线率。正文先源和run，基础设施放展开区。

## 状态与验收

Loading保留过滤；Empty=尚无SyncRun，说明未启动/未启用；No Result=当前过滤无任务，清除条件；Partial Data/Source Offline本身是业务状态，仍读旧run；Stale Data提供最后成功和预计计划；Error重试读取并保留过滤。Conflict/Evidence Insufficient用于run处理的记录问题时提供该对象链接，不把运维页当事实审核页；Agent Timeout不适用。Permission保护运维写入和敏感日志；重试提交超时凭幂等键查询真实run而非重复发任务。

验收：总览异常→该source→失败run≤3次主动操作；历史/最新成功分开；研究probe不冒充运行；计划源不绿色；任何重试只显示实际排队/运行/完成。BACKEND REQUIRED：Y01—Y05，运行接口均待实现。

## 本页元素索引（统一依赖矩阵）

| ID | 模块/动作 | 阶段 | 数据能力状态 |
|---|---|---|---|
| Y01 | 来源表/筛选/查看最近失败 | P0 | BACKEND REQUIRED |
| Y02 | 来源时间/数量/延迟/下次计划 | P0 | BACKEND REQUIRED |
| Y03 | 任务历史/失败筛选/详情 | P0 | BACKEND REQUIRED |
| Y04 | 失败详情/脱敏错误/重试 | P0 | BACKEND REQUIRED |
| Y05 | 实际健康摘要 | P0 | BACKEND REQUIRED |

全局导航/搜索/返回/刷新/分享使用G01—G05；Evidence使用E01—E04，知识使用K01。按钮、状态响应及API提案详见[页面数据依赖](PAGE_DATA_DEPENDENCIES.md)，统一术语见[UX_TERMINOLOGY.md](UX_TERMINOLOGY.md)。
