# Phase 7 开始前核验

任务依据为 sources/phase7_request.docx 的用户新文稿，继续此前“直接按文档执行”的授权。本阶段增加富化与可信结论；结束后停止，不进入资产/SBOM阶段。

实际复核：开发数据库 aegis_phase6:55436 与 API:8000 可用，迁移仍0001；278个漏洞、347份原文、198个产品、3个来源、1378份来源观察、19次SyncRun。逐原文SHA256均正确。CVE-2025-32434仍为唯一主体，CVE_LIST与OSV并存、3份原文可追溯。专用测试数据库55435独立启动，完整131项回归重新通过，迁移upgrade/downgrade/re-upgrade、43表与22历史保护通过。实际结果见 preflight_reality.json、phase6_regression_preflight.json、phase6_migration_preflight.json。

此前完整读取的Phase1–5冻结材料77份指纹再次一致；本轮复核需求、第一批/第二批源选型、外部内容安全、Evidence、Review、迁移设计与现有工程。输入清单保存Phase6代码/文档原指纹，后续扩展不改0001或旧原文，不以报告替代真库检查。

可直接复用：Collector/Normalizer/身份去重/产品注册表/基础PEP440；原文先提交、不可变SourceObservation；Source/SyncRun；Claim/Evidence/VerificationResult/VerificationEvidence/POC/Patch/EPSS/KEV/Review/Audit/Timeline等43表；record_review的幂等和修订控制；现有5条只读API与测试隔离。

需要扩展：富化契约、受控GitHub/FIRST查询、六类Enricher；确定性关联与静态POC分类；真实Claim/Evidence持久化；独立来源/版本/时间核验；冲突与自动复核；再富化/轻量调度；聚合详情、证据与复核提交接口。增加轻量EnrichmentJob和ConflictRecord，使用新的0002增量迁移；为Phase7拒绝结论扩展核验CHECK，不更改已发布0001。

影响Phase7的已知问题：有限源覆盖、OSV pending50/KEV pending1622、SEMVER/GIT不支持、来源转载不独立、网络超时、原JSON键序修订、loopback无完整认证、Docker未实测。KEV复用完整1733条目录原文做目标核对，不为缺席写known_exploited=false；既有采集backlog不伪报清空。复杂版本或低信息POC明确abstain。对人工采用结论追加复核，不让网络富化悄悄覆写。

缺少文稿列出的 docs/tooling/ 与 THIRD_PARTY.md，本阶段按要求建立；现有第三方许可证据在 reports/phase6/THIRD_PARTY_NOTICES.md。没有发现阻塞Phase7的Phase6缺陷，PHASE6_FIXES.md记录为无；扩展项单独列明。

实现方式：当前会话逐任务执行，先失败测试再实现。用户文稿已给出架构、状态、禁止事项和验收细则，作为设计规格；不增加额外确认流程。工作区无Git仓库，沿用文件清单/ledger记录，不创建虚假提交或删除本地库。
