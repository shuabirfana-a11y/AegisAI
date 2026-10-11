# 数据流与失败语义

| 步骤 | 输入→输出 | 失败/日志 |
|---|---|---|
| 取CVE/OSV/KEV | source+外部ID/包名/目录快照→完整HTTP字节+更新时间 | connect/read timeout分开；记录source/id/status/trace，不记header/key |
| 存raw | 字节→sha256/blob | 固定目录，temp→atomic rename；上限；写失败不推进游标 |
| 规范化 | raw→统一模型＋原始扩展 | 非JSON/missing identity隔离单条；其他字段可unknown；raw不丢 |
| 去重 | CVE/sourceID/URL/hash→复用或revision | 相同hash复用blob；同URL变内容保留新revision；跨源不删 |
| 产品 | 生态+准确包名/规则→Product/Package | 别名冲突UNKNOWN；规则ID入日志 |
| 版本 | source ranges/events→结构化/UNSUPPORTED | 解析失败存原文，禁止排除该漏洞；不猜固定版本 |
| AI初筛 | Product类别/上下文→三态和理由 | 精确包规则优先；关键词只提候选，必要时UNKNOWN |
| 基础富化 | source observations→CVSS/CWE/版本/refs claims | CNA/OSV不足允许缺失；不调用8个源补完成度 |
| Evidence/持久化 | raw/locator/claims→事务内关系与projection | 一记录一事务；失败rollback/回补；blob孤儿延时清理 |
| API查询 | 受限参数/授权→分页详情/证据 | 候选明确PENDING_HUMAN；缺失404，unsupported返回UNKNOWN理由 |

Dedup三层：CVE identity归并；canonical URL定位源对象但不作为唯一内容键；sha256去重存储。source_record(source,external_id,raw_hash)保存观察；同源重复不增事实，不同源共享内容仍保留两个source_record与同源lineage。共享OSV别名不做无条件传递式合并；多个CVE关联需复核。

时间：source_published/modified是发布者时间；retrieved是本次响应完成观察；first/last_seen是本系统历史；created/updated是DB记录时间；as_of是查询时间点。缺时间保存null，不拿抓取时间代填来源发表时间。fixtures时间取原始响应落盘完成时间，保留依据。

错误：429按Retry-After＋预算；timeout/500/503/network可重试3次指数退避+jitter，超预算入回补；404记录源无记录不推漏洞不存在；invalid JSON保存raw并隔离；必需ID缺失标INVALID；unsupported范围继续落库；duplicate幂等复用；DB不可用暂停批次并返回失败，不把游标推进到成功。批次状态PARTIAL，其他可处理记录继续；全DB故障不伪装局部成功。

单worker用source/scope advisory lock防重入；游标推进与成功记录同事务/确认后更新。有重叠窗口和周期对账；blob与DB无法跨存储原子提交，先存blob再DB提交，失败留可识别孤儿，有宽限GC与恢复策略。API不显示未提交projection。
