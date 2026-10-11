# 隔离评测模型与真实分母

evaluation schema独立保存Dataset/Case/Run/Result四表，不引用业务主体作为唯一真值，而保存稳定input/evidence_snapshot/as_of/lineage_group。Dataset(dataset_key,revision_hash)唯一，split=development/validation/final_test、rubric与冻结时间明确。Case有ground_truth及draft/validated/unknown、adjudicator/理由；未人工确认候选不是gold。Case修订新建数据集hash，当前表append-only，不能改完标签仍叫原冻结集。

Run在实际评测结束后一次保存started/finished/status/code/model/config/environment；本阶段没有执行Benchmark。Result以run/case唯一，复合FK防跨dataset串Case，逐题保存prediction/correct nullable、状态、完整latency_ms、0—2 rubric_score与错误。开始至结束的完整问答时间计入网络/模型/检索，不用首token代替。timeout/failed必须仍有Result并留在可回答任务分母。

AI相关性Precision/Recall/F1从Case真值和prediction逐条算TP/FP/FN，unknown单列coverage。PoC association与usability分任务；Patch需要完整SHA/适用分支；版本准确率报告全体、支持范围coverage、边界子类。富化正确相关输出/全部输出、限定可知真值内Recall按冻结需求公式；QA完整2分题/全部题、部分分/多跳/正确拒答分开，不通过丢掉超时抬分。

lineage_group用于同源镜像/相近repo修订/同主体分组拆分，防最终测试泄漏。外部人工Evidence快照包含源/locator/hash，而非只给CVE字符串。最终数据集和rubric更新需新hash，不原地重标。少样本或分母0报N/A，不能给100%；schema测试中的一题只是隔离存储检查，没有性能或正确率结论。

Source覆盖数按enabled且有效SyncRun/SourceObservation+类别算，不按研究目录行数或候选登记数。采集延迟使用原published与首次有效retrieved，仅前瞻新增/已验证时间；历史回补、未知/负时钟/未采集分别报coverage。Agent时延/工具次数来自实际Run/ToolCallRecord，模型自信分不作为真值。完整评分映射见SCORE_STORAGE_MAPPING。

当前12条真实开发种子仍是待人工确认候选，未导入正式业务/评测gold；新synthetic数据库fixture仅测试FK/事务，与真实Benchmark完全区分。测量方案按requirements/EVALUATION_REQUIREMENTS，当前没有已达95%或≤5s等成绩。
