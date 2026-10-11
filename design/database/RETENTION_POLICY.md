# 保留与删除策略

历史不可被普通运行代码UPDATE/DELETE；22张表装数据库触发器（实际迁移测试检查数量），并使用RESTRICT外键，不级联丢Evidence。

| 对象 | 策略 | 处理理由 |
|---|---|---|
| `raw.raw_documents` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `raw.source_observations` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `core.external_identifiers` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `core.vulnerability_identifiers` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `core.affected_version_ranges` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `core.cvss_assessments` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `core.ai_relevance_assessments` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.evidence` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.verification_results` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.verification_evidence` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.epss_snapshots` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.known_exploitation` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.intelligence_events` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `intel.knowledge_chunks` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `app.audit_logs` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `app.asset_vulnerability_matches` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `app.tool_call_records` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `app.agent_citations` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `evaluation.datasets` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `evaluation.cases` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `evaluation.runs` | append-only | 修订新建，保护来源/证据/采用/评测历史 |
| `evaluation.results` | append-only | 修订新建，保护来源/证据/采用/评测历史 |

Vulnerability/Product/KnowledgeDocument/Asset/AssetComponent可soft delete，不默认hard delete；Source用enabled=false关闭，不删历史。Claim/Review/Source/SyncRun/AgentRun是可更新当前投影，但关键事实/人工决定必须事务追加历史。Evaluation集合和Case一旦导入不可修改，同hash原真值留存；修正需要新Dataset revision。

长期保留采用证据/核验/审计至少覆盖评测及答辩回放窗口；180天是团队起始策略，不是官方法律或许可承诺。许可受限知识正文按实际条款最小保存，metadata+link+允许片段优先。隐私删除/Secret泄露/法律或许可要求可触发例外清除：由特权运维走审批与记录删除证据、重新计算保留/脱敏hash；普通角色不能关触发器，不能默默破坏引用。该例外未自动实现，不能宣称永久保留优于实际隐私要求。

纯未引用临时失败草稿可hard delete，但目前没有专门scratch表，因此不额外设计清扫服务。数据库owner能drop trigger或schema；生产迁移owner与运行角色分离，历史表运行角色只SELECT/INSERT，未正式配置生产角色权限。

备份：pg_dump custom格式受控路径、权限/加密/secret环境变量；恢复到新测试库用pg_restore --no-owner后检查行数、hash、FK、trigger、引用。当前只跑过迁移往返与事务测试，尚未跑生产备份恢复演练，不将可执行恢复方案写成已测成功。数据库本机测试cluster验证完停止，保留空schema便于下次复跑。
