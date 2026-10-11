# 页面—数据—能力—API依赖矩阵

**所有业务数据、运行状态和动作均为 BACKEND REQUIRED，尚未实现。** Phase 2原样本、设计JSON和HTTP probe不是产品后端。纯本地返回/布局标LOCAL ONLY，不产生事实。元素ID贯穿页面说明与线框，表中包括筛选、跳转、查询和写动作，不能只实现卡片数值。

Source ID沿用research/data_sources/source_catalog.json；列表来源指证据/输入，不等于Source原生提供人工结论/统计。[]表示本地用户输入或内部运行数据，不是“官方源未知”。下列API路径全为 **API PROPOSAL 未实现**，将来后端架构阶段可调整，本轮不创建端点/数据库。

## GLOBAL

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| G01 导航及可用动作 | 实际开放能力、read/write权限、登录会话 | 用户输入/本地上下文或内部运行数据 | 能力与最小权限 | A01 | P0/读取/BACKEND REQUIRED |

| G02 全局搜索/结果跳转 | 实体ID/类型、搜索范围、可访问产品/资产 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 实体搜索与授权过滤 | A02 | P0/读取/BACKEND REQUIRED |

| G03 返回/面包屑/锚点 | origin、filters、cursor、scroll、revision、as_of | 用户输入/本地上下文或内部运行数据 | 本地路由上下文 | 无网络API，仅本地上下文 | P0/读取/LOCAL ONLY |

| G04 请求重试/范围刷新 | 请求ID、最新revision/coverage、旧快照 | 用户输入/本地上下文或内部运行数据 | 统一错误与快照协议 | A01 | P0/读取/BACKEND REQUIRED |

| G05 复制分享链接 | 公共entity/revision/anchor；私有资产只在授权会话上下文 | 用户输入/本地上下文或内部运行数据 | 本地URL构造及访问权限复核 | A01 | P0/读取/BACKEND REQUIRED |

## DASH

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| D01 时间窗与范围/刷新 | window、as_of、覆盖产品/来源及快照 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 一致快照与范围摘要 | A03 | P0/读取/BACKEND REQUIRED |

| D02 新增/更新/知识计数及进入列表 | 首次发现distinct entity、新修订entity、knowledge type计数及过滤器 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 去重后变化聚合 | A03, A04 | P0/读取/BACKEND REQUIRED |

| D03 值得关注/风险信号及进入详情 | CVSS版本、PoC关联状态、KEV目录、EPSS日期、变化依据 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, CISA_KEV, EPSS, VULNRICHMENT, GITHUB_CODE | 可解释风险信号聚合 | A03, A05 | P0/读取/BACKEND REQUIRED |

| D04 近期情报列表/时间线及类型跳转 | ID/类型、变化摘要、源日期和观测日期 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 类型化事件与知识聚合 | A03, A04, A07, A10 | P0/读取/BACKEND REQUIRED |

| D05 来源摘要及异常跳转 | 实际启用数、类别、stale/failed、last_success_at | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 运行状态聚合 | A03, A20, A21 | P0/读取/BACKEND REQUIRED |

| D06 资产影响入口 | 受影响登记组件/漏洞distinct数，库存revision | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 授权Asset Matching | A03, A13 | P1/读取/BACKEND REQUIRED |

| D07 待复核入口 | 开放任务distinct数、风险及触发原因 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Review队列聚合 | A03, A14 | P1/读取/BACKEND REQUIRED |

## CENTER

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| C01 类型切换/搜索/清空 | record_type、外部ID/关键词、各类型结果计数 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 统一类型检索 | A04 | P0/读取/BACKEND REQUIRED |

| C02 基础及高级筛选/排序/分页 | 产品生态、AI类别及依据、CVSS version、KEV/PoC/fixed/date/Claim状态、cursor | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 确定性筛选、未知桶及排序 | A04 | P0/读取/BACKEND REQUIRED |

| C03 漏洞行及详情跳转 | 身份、产品、评分出处、PoC关联、修复、KEV、字段核验、updated | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, CISA_KEV, EPSS, VULNRICHMENT, GITHUB_CODE | 精简漏洞投影 | A04, A05 | P0/读取/BACKEND REQUIRED |

| C04 论文/标准/政策/事件行及详情跳转 | 作者/发布机关、ID/版次/状态、时间、related entities、证据 | ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 知识类型投影与详情 | A04, A10 | P0/读取/BACKEND REQUIRED |

| C05 资产命中筛选 | 授权资产ID、affected/not_affected/unknown | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 授权资产匹配筛选 | A04, A13 | P1/读取/BACKEND REQUIRED |

| C06 结果范围/未知说明 | 本次已查范围/未接入范围、撤销记录、部分源失败 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Coverage与查询执行摘要 | A04 | P0/读取/BACKEND REQUIRED |

## DETAIL

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| V01 身份/描述/状态 | CVE/GHSA别名、title、record_status、源语言/日期 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 实体详情与状态修订 | A05 | P0/读取/BACKEND REQUIRED |

| V02 影响产品/包/版本/修复及查看证据 | package/ecosystem/PURL、原range/events/explicit versions、explicit fixed、scope/ClaimID | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 版本契约与字段provenance | A05, A08 | P0/读取/BACKEND REQUIRED |

| V03 CVSS/EPSS/KEV/利用状态及查看证据 | cvss版本vector/base/provider；epss/date/model；KEV完整目录时间；SSVC scope | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, CISA_KEV, EPSS, VULNRICHMENT | 风险字段独立保留与溯源 | A05, A08 | P0/读取/BACKEND REQUIRED |

| V04 PoC关联/可用性及展开证据 | candidate/related、公开链接；独立核验记录/授权适用环境或unknown | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, GITHUB_CODE, TOB_BLOG | PoC关系与可用性独立记录 | A06, A08 | P0/读取/BACKEND REQUIRED |

| V05 处置建议/厂商链接/修复版本 | explicit fixed、厂商建议及适用包分支、未提供原因 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 修复事实/建议出处 | A05, A06, A08 | P0/读取/BACKEND REQUIRED |

| V06 Patch/Fix Commit | 候选commit完整SHA/PR/branch、关联状态、Evidence | VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, GITHUB_CODE, OSV | Patch关联（未实现时隐藏） | A06, A08 | P1/读取/BACKEND REQUIRED |

| V07 论文/分析及知识关联跳转 | 文献元数据、relation scope、关系候选依据 | ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 关系检索与知识详情 | A06, A10, A08 | P0/读取/BACKEND REQUIRED |

| V08 证据/Claim状态/差异 | Claim scope/revision、EvidenceID、support/refute/context、lineage | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Evidence Store与字段核验 | A08, A09 | P0/读取/BACKEND REQUIRED |

| V09 同范围冲突/进入复核 | 真实冲突ID、两候选、范围及review ID | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 冲突检测与Review | A05, A14, A15 | P1/读取/BACKEND REQUIRED |

| V10 时间线及事件证据 | 源发布/修改、系统首次发现、PoC关系/KEV/fix变化，事件证据 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 证据化事件时间线 | A07, A09 | P0/读取/BACKEND REQUIRED |

| V11 继续询问这个漏洞 | entityID/revision、当前Claim及问题、授权上下文 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 受控问答任务 | A17, A18 | P0/读取/BACKEND REQUIRED |

| V12 当前资产影响摘要/查看清单 | 授权inventory revision、三态匹配和依据 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | Asset Matching | A13 | P1/读取/BACKEND REQUIRED |

## ASSET

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| S01 组件清单/查找/选择 | 授权名称、ecosystem/package、原始精确version与校验状态 | 用户输入/本地上下文或内部运行数据 | 最小资产清单权限 | A11 | P1/读取/BACKEND REQUIRED |

| S02 人工添加/确认登记 | name/ecosystem/package/exact version、歧义原因、错误定位 | 用户输入/本地上下文或内部运行数据 | 资产登记校验与审计 | A12 | P1/人工写入/BACKEND REQUIRED |

| S03 影响三态/未知原因 | inventory revision、matched entity、range scope、reason/evidence | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 生态版本匹配 | A13, A08 | P1/读取/BACKEND REQUIRED |

| S04 优先处置列表/排序解释/详情 | 匹配证据、KEV收录/目录时间、PoC状态、CVSS版本、明确fixed及用户业务关键性 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, CISA_KEV, EPSS, VULNRICHMENT, GITHUB_CODE | 可解释规则排序 | A13, A05, A06 | P1/读取/BACKEND REQUIRED |

| S05 分析为什么影响我 | 资产ID和inventory revision、漏洞/ClaimID；问题 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 授权资产上下文问答 | A17, A18 | P1/读取/BACKEND REQUIRED |

## REVIEW

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| R01 问题队列/筛选/进入任务 | 对象、问题类型、风险理由、候选、证据数及创建日期 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Review过滤及权限 | A14, A15 | P1/读取/BACKEND REQUIRED |

| R02 对照范围/候选A/B/证据 | 原结论、候选、生态/版本/分支/date/CVSS version、lineage | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 同scope事实对照 | A15, A08, A09 | P1/读取/BACKEND REQUIRED |

| R03 确认A/B/证据不足/暂不判断/备注 | 选择值、理由、review revision、actor和幂等请求键 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 权限、并发校验及决策审计 | A16 | P1/人工写入/BACKEND REQUIRED |

| R04 审计历史/回详情 | 原/后结论、actor/time/reason、证据版本、entity/anchor | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 不可覆盖审计与详情回链 | A15, A05 | P1/读取/BACKEND REQUIRED |

| R05 刷新后比较/恢复草稿 | 409当前revision、草稿、差异及重新提交范围 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 并发差异返回 | A15, A16 | P1/读取/BACKEND REQUIRED |

## QA

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| Q01 问题输入/推荐问题/提交 | question、会话、entity/Claim上下文、as_of/time zone/coverage | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 问答任务接入与范围澄清 | A17 | P0/读取/BACKEND REQUIRED |

| Q02 任务过程/取消/重试 | 工具名、参数范围/状态/结果数、过滤原因、query_id；取消结果 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 真实任务公开事件与生命周期 | A18, A19, A17 | P0/读取/BACKEND REQUIRED |

| Q03 回答/未知部分/引用 | 有Claim引用的结论、适用范围、partial reason、snapshot revision | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 可核验证据回答 | A18, A08, A09 | P0/读取/BACKEND REQUIRED |

| Q04 相关漏洞列表/回详情 | entityID/revision、相关产品与来源、匹配过滤条件 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 受控结果投影及详情回链 | A18, A05 | P0/读取/BACKEND REQUIRED |

| Q05 相关知识/来源/跨文档引用 | knowledgeID/type/edition、EvidenceID、source/provider | ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 文档检索与关系工具 | A18, A10, A09 | P0/读取/BACKEND REQUIRED |

| Q06 相关资产/为什么优先 | 授权assetID/inventory revision、影响三态、解释因子 | CVE_LIST, OSV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 授权资产工具 | A18, A13 | P1/读取/BACKEND REQUIRED |

| Q07 澄清/续问/原查询恢复 | 缺失参数、先前query_id与scope、明确新时间窗 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 会话上下文及实际范围 | A17, A18 | P0/读取/BACKEND REQUIRED |

## SYSTEM

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| Y01 来源表/筛选/查看最近失败 | 注册SourceID、enabled、运行状态、类别及coverage | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 来源注册与真实运行聚合 | A20, A21 | P0/读取/BACKEND REQUIRED |

| Y02 来源时间/数量/延迟/下次计划 | last_success/newest source date、fetched/normalized/new/updated/failed、retry/latency samples/next_scheduled | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | SyncRun统计与调度时间 | A20, A21 | P0/读取/BACKEND REQUIRED |

| Y03 任务历史/失败筛选/详情 | runID、source/time/status、范围、尝试、恢复关系 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | SyncRun历史查询 | A21, A22 | P0/读取/BACKEND REQUIRED |

| Y04 失败详情/脱敏错误/重试 | 错误码/request ID、checkpoint、重试权限/queued/new runID | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 失败隔离与受控重试 | A22, A23 | P0/运维写入/BACKEND REQUIRED |

| Y05 实际健康摘要 | 已监测API/Collector/Queue及observed_at或NA | 用户输入/本地上下文或内部运行数据 | 已有监控摘要 | A24 | P0/读取/BACKEND REQUIRED |

## EVIDENCE

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| E01 来源/原文摘要/时间/URL | publisher/sourceID、excerpt、published/retrieved、original URL | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 证据内容与许可/权限控制 | A09 | P0/读取/BACKEND REQUIRED |

| E02 范围/多来源/lineage比较 | Claim/raw revision、scope、支持反驳关系、原始发布者与转录链 | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Claim与来源链检索 | A08, A09 | P0/读取/BACKEND REQUIRED |

| E03 原始定位/历史证据/分享 | raw hash、JSON Pointer/页码/span、已取raw受限读取、permalink | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | 不可变证据版本定位 | A09 | P0/读取/BACKEND REQUIRED |

| E04 进入对应复核/返回原字段 | reviewID/读写权限，返回Claim anchor/revision | CVE_LIST, OSV, CISA_KEV, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW, EPSS, GITHUB_CODE, VULNRICHMENT, ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI | Review及导航上下文 | A15, A01 | P1/读取/BACKEND REQUIRED |

## KNOWLEDGE

| 元素/UI模块 | 需要的数据 | 来源 | 后端能力 | API需求 | 阶段/动作/状态 |

|---|---|---|---|---|---|

| K01 知识详情/原文/版本/关联/询问 | type、ID、版次/status、publisher/author、dates、links/ClaimID | ARXIV, TOB_BLOG, GOOGLE_SECURITY_BLOG, SAMR_AI_STANDARD, NIST_AI, CAC_POLICY, ATLAS, OWASP_GENAI, VENDOR_PYTORCH, VENDOR_VLLM, VENDOR_MLFLOW | 共享知识详情及引用问答 | A10, A08, A17 | P0/读取/BACKEND REQUIRED |

## API提案目录（不是外部数据源API）

| ID | UX需要的接口提案 | 最低响应/操作要求 |

|---|---|---|

| A01 | GET /capabilities | 开放页面/读取与写入动作、当前用户权限、实际接入范围；无实现的功能不可启用 |

| A02 | GET /search | 按ID、包/产品、知识标题、授权资产名称分组返回；实体ID/类型/访问权限 |

| A03 | GET /overview | 同一as_of/revision下计数、时间窗、coverage及可复现筛选条件 |

| A04 | GET /intelligence | 类型/过滤/排序/游标、查询语义、可访问条目、总量与覆盖状态 |

| A05 | GET /vulnerabilities/{id} | 身份/原文/范围/风险/建议/Claim引用、按字段状态与快照版本 |

| A06 | GET /vulnerabilities/{id}/relations | 公告/论文/分析/PoC/Patch候选、关系依据、关联和可用性分别返回 |

| A07 | GET /vulnerabilities/{id}/timeline | 有依据的业务事件、源发布/修改/系统观察时间分开 |

| A08 | GET /claims/{id}/evidence | Claim适用范围、support/refute/context、lineage与核验历史 |

| A09 | GET /evidence/{id} | 原文片段、raw版本/hash/locator、原始出处、权限/许可限制 |

| A10 | GET /knowledge/{id} | 非CVE知识类型/作者或发布机关/版次/发布日期/生效日/原文与关联证据 |

| A11 | GET /assets | 仅当前用户授权清单、生态/包/原版本/规范状态、库存修订号 |

| A12 | POST /assets | 人工登记名称/生态/包/精确版本；校验错误定位；幂等请求键；不接SBOM |

| A13 | GET /assets/{id}/impacts | 版本判断三态、范围与依据、排序理由、库存及情报revision |

| A14 | GET /reviews | 待办对象/同scope冲突或缺证原因/候选/风险/创建及处理时间 |

| A15 | GET /reviews/{id} | 候选原值/原结论/适用范围/evidence/当前review revision/审计 |

| A16 | POST /reviews/{id}/decisions | 人工选择与理由、actor、expected_revision、idempotency_key；409不覆盖 |

| A17 | POST /assistant/queries | 问题、授权实体上下文、日期/快照、会话ID；返回真实query_id |

| A18 | GET /assistant/queries/{id} | queued/running/completed/partial/failed/cancelled；公开工具摘要、引用与结果 |

| A19 | POST /assistant/queries/{id}/cancel | 取消自己的活动查询；已完成任务返回实际状态，不删历史 |

| A20 | GET /sources | enabled/运行状态、最后成功、源内容日期、coverage/延迟样本与计算范围 |

| A21 | GET /sync-runs | source/status/time筛选、游标、采集/处理数量、失败/重试关联 |

| A22 | GET /sync-runs/{id} | 单次run的范围、时间、数量、脱敏错误、检查点与恢复情况 |

| A23 | POST /sync-runs/{id}/retry | 运维权限、同任务范围、去重幂等、限额检查；202表示排队而非成功 |

| A24 | GET /health-summary | 仅已经接入监测的API/Collector/Queue状态及测量时间；没有监控则NA |

## 共同读取/写入约束

读取响应需entity/Claim/raw revision、as_of、coverage、字段缺失reason、permission和partial errors；分页统计同快照，ID稳定。排序是所选CVSS版本/日期/真实信号，未知桶显式；任何派生结论带规则依据与source lineage，不能从页面展示需要倒推假事实。

写入只含人工资产登记、Review决定、授权Sync retry；actor由会话确定、服务器权限校验、幂等键和实际接受结果必需。Review expected_revision冲突返回409并保留草稿；输入422定位错误；读写403不泄露私有对象；查询和run取消/重试不自动覆盖决定。

外部PoC链接无执行API、任意SQL/任意URL/全网扫描均无入口。知识正文按许可/权限读取；资产隐私不送公共来源。能力未接入必须通过A01门控，P1不得默认为P0必有。

## 分期与真实字段映射

M0首批：CVE_LIST的cveMetadata/containers.cna/adp；OSV package/ranges/events.fixed/aliases；完整CISA_KEV目录/catalogVersion/dateReleased。先建立实体/版本/证据切片，不承诺完整参赛类别覆盖或PoC/Agent。

M1/P0：第二批厂商明确修复建议、GitHub有限引用PoC、ARXIV论文、TOB/Google分析、SAMR正式标准/NIST指导规范/CAC政策及版本化AI知识；真实至少3种富化和实际Agent/跨文档问答。EPSS有date/model，CISA ADP复用已有raw；独立同步按实际缺口。V07/C04/K01不能拖成决赛选做。

M2/P1：Asset Matching、同scope冲突/Review、Patch关联、复杂多轮/角色增强；分数预测、搜索、监控提升按冻结任务推进。NVD和GHSA独立全库仍暂缓；不得在UX硬依赖它们。任何源启用还需合法获取/频率/许可校验；本阶段不改源选型。

数据库/API设计输入：先支持字段级Claim—Evidence—RawDocument—Source与upstream lineage；记录版本/time/scope和来源观察；人工决定作为另一个有审计的层。这里只给业务关系/接口需求，不生成表、DDL、模型或代码。
