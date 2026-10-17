# 冲突观察的结构化交接

原 InvestigationArtifact.conflicts 已是结构化数据；本次补的是阻断 DAG 的核验交接和 Verifier 冻结快照中的独立 ConflictEvidenceArtifact，不新增爬虫、证据事实或核验规则。

## VERIFY_ONLY

只有根调查已有完整 CONFLICT 观察、运行和 Trace 均为 WAITING_REVIEW、没有 partial_result 或失败工具、且保留原 conflicts 时，才允许把该观察交给独立 Verifier。依赖节点的 BLOCKED/WAITING_REVIEW、失败原因仍保留。

新 VERIFY_ONLY 分支不进入风险分析，不解锁 DAG 节点，不把 Gate 结果改为通过。部分数据、失败工具或非冲突状态仍拒绝交接。原来完整冲突已有的 CONTINUE 路径保持原行为，后续风险与 Gate 仍由既有规则裁决。

## ConflictEvidenceArtifact

内部冻结对象包含：artifact_id、type=CONFLICT_EVIDENCE、schema_version、source_artifact(run/task/artifact)、conflict_index、conflict_sha256、conflict_reason、sources、information_status=CANDIDATE、unresolved_items。

每个 source 引用现有 evidence_id/claim_id/source_id/raw_document_id/observation_id，以及来源内容 hash 与 reference_sha256。完整原始冲突保留在父 InvestigationArtifact，完整引用内容保留在既有 VerificationEvidence；不重复复制正文。

派生 ID 和 SHA 使用既有 canonical fingerprint，数据库 JSONB 重排键不会改变身份。快照消费会重新计算来源关联，篡改 reason/hash/来源会拒绝。

最多衍生 32 条冲突观察；更多记录仍保留于原父对象并注明限额。无相应来源证据时标注 CONFLICT_SOURCE_EVIDENCE_INCOMPLETE，不生成来源。

## 对前端的影响

公开 VerificationArtifact、8 个调查 API 和既有 TypeScript/OpenAPI 无变化。前端继续读已有 verification.conflicts、supporting/conflicting evidence、Gate checks。内部 ConflictEvidenceArtifact 位于后端冻结核验输入，不能虚构新的浏览器 URL。

## 已验证与未验证

合成边界测试覆盖：源引用、冻结不可变、篡改拒绝、JSONB 键排序、70KB 原冲突、128 Evidence/28 冲突、VERIFY_ONLY 保留阻断状态和跳过风险分析。

本轮 5 题中的真实来源冲突问题在 Planner 阶段因重复 JSON 键失败，未进入核验；因此本次不能声称该真实问题已完成 Conflict → Verification → Gate 闭环。原始失败和新的失败都保留，不删题。
