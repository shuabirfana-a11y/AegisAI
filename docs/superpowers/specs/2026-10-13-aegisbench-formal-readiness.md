# Phase 13-E：正式实验准入准备

用户已指定输入、流程、指标与停止条件；本轮在 Phase13-D 分支的实际实现上增量准备，不改系统。

- 首批门槛 10 个经原 loader 核验的 HUMAN_GOLD；沿用原 APPROVED/REVIEWED 完成态，并分别统计。不是10张任务卡、机器参考或文件。
- 只增加无网络的 preflight 工具与实验模板，复用数据哈希、证据定位、独立人审及原评测器；禁止放宽现有门禁。
- 检查不足时退出码3，保存阻塞报告，不运行 HTTP、模型、评分器或生成准确率。
- 人工答案、任务卡、工作流文件分开统计；工作流文件计数不决定评测准入。
- 模型 immutable digest、Prompt hash、正式数据集版本、库存绑定尚未冻结时，模板明确 NOT_FROZEN；数据通过不等于完整实验准备通过。
- 原 Online / Offline 调查入口复用；独立 RAG/无Verification对照为 NOT_IMPLEMENTED，不能声称公平对比已完成。
- OutcomeAudit 仍是 Evidence Coverage/Hallucination 的独立输出语义复核门禁。
- 当前批准为0则停在13-E.1；不开展13-E.2，不改人工答案或业务逻辑。
