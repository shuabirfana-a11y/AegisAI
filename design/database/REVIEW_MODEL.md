# 人工复核 幂等与审计事务

ReviewTask固定指向Claim：version_conflict、poc_association、patch、evidence不足均通过Claim typed subject定位真正对象。status=open/assigned/resolved/deferred/cancelled与事实核验四态独立。暂缓不等于已确认；reason、actor、expected review revision与expected Claim revision是提交必需参数，不能在抽屉绕过复核写入。

record_review是本阶段最小持久化事务助手；调用方必须先认证actor并授权，本阶段未实现业务API/认证系统。调用方用Session事务控制提交，助手不会自行commit。按actor/request_key请求锁、Review行锁、Claim行锁读取；相同键相同完整payload返回旧Audit，相同键不同payload拒绝。旧revision或已关闭任务拒绝更新，对应未来API409。

confirmed必须有explicit value与至少一条同scope support；conflict必须有同scope support/contradict；不足/pending允许缺口；deferred保留Claim值/状态/revision，Review保持deferred且resolved_at=null，只追加Audit。上述输入校验不取代分析师对事实/lineage的判断，不会按来源数量提升可信度。

正式决定事务：增Claim修订→保存新VerificationResult→关联实际Evidence→更新Review前后快照/状态→追加Audit(actor/action/request hash/before/after/reason/time)。原始Evidence/Range/CVSS/Observation无任何UPDATE；任一步失败整体rollback。新来源记录不得自动覆盖人工采用层，必须新候选或复核。

请求指纹包含task、actor、两expected revisions、decision、value、reason和Evidence集合；retry无需用更新后的revision改写原请求，必须重发完全相同请求。事务锁避免同键并发插入竞态，审计UNIQUE兜底。单一事务持有Review→Claim的固定锁顺序；未来跨任务批处理要另行验证锁顺序及死锁恢复。

实际测试已覆盖一次写入、同键重试、键冲突、stale拒绝、无证据确认拒绝、暂缓保留和中断回滚。多连接并发压力和正式auth仍是已知未测项，不以单连接测试冒充并发证明。Audit append-only保护历史，数据库owner能改DDL，因此生产必须分离迁移owner与最小运行角色。
