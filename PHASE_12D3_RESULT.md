# Phase 12-D.3：资产风险业务闭环修复结果

状态：实现与真实 HTTP 验收已完成；全量回归复查与独立审查正在完成。以最终验证记录为准。

## 1. 问题原因

原核验只读取选定漏洞 Artifact 的祖先任务回执，遗漏后续版本任务及独立资产任务。风险输入又从当前库存重新读取版本，缺少调查时固定的观察对象。影响范围候选投影只保留 raw_expression，丢失来源已提供的 events / explicit_versions 等字段。旧 PyTorch 场景另有无效来源证据、未解析范围及候选 PoC，补齐资产不能自动确认这些事实。

## 2. 修改内容

- 原调查 Artifact 保留；服务器增加同运行、同漏洞、已完成任务的精确 supplementary Artifact 引用。
- 新建 frozen `VersionObservation`，从已授权 Tool Gateway 的 get_asset 回执提取精确组件；没有回执或有歧义时不读取新库存填补。
- 新建 `ImpactVersionEvidence`，关联原有 Claim / Evidence / RawDocument / SourceObservation。状态按证据自身支持/冲突关联绑定，不能继承另一条证据所确认的 Claim 状态。
- 完整保留已解析版本字段，复用既有解析和比较器；unsupported 不改成 parsed，来源冲突不删除。
- 风险输入使用已封存 Observation；仍检查资产所有权、精确身份和回执哈希。补充资产名称、观察 ID；重要性保持 unknown。
- 非匹配发行包的原 R1 低风险结果只在有封存观察时做 DTO 一致性适配：NOT_AFFECTED 仅限当前组件/漏洞，未修改 Risk 决策。

## 3. 数据链路变化

```text
原始请求的资产/组件范围
  → 原 Planner / Runtime 执行真实工具
  → get_asset 回执 → VersionObservation
  → 原漏洞及后续版本/证据回执 → Claim + ImpactVersionEvidence
  → 原 Verification 规则 → VerificationArtifact
  → 固定观察 + 已确认范围 → 原 Risk 规则
  → 原 Integration Gate → 封存 AnswerEnvelope
```

Planner、Runtime、调查 Agent、核验规则、风险规则及 Gate 规则没有改写；没有新模型、提示词优化或评分实验。

## 4. Artifact 与 Verification

`VersionObservation` 记录 id/type、asset_id/asset_name、component_id/component/version、发行包身份、environment/exposure/criticality、库存修订、更新时间、观察时间、来源 Artifact、回执 ID/哈希、is_demo。

`ImpactVersionEvidence` 记录漏洞/发行包/Claim、影响与修复声明、证据 ID、来源与引用、原文档与观察 ID、哈希及证据级状态。合法 Artifact 引用在 owner-bound Reader 再验证；输出的观察及证据投影不能改变封存输入。

新字段为空时不参与原有序列化，历史审计哈希兼容；新请求仍采用 v1 的可选扩展。超出限额保持部分结果和阻断，不扩大处理上限。

## 5. Risk 与 Gate

风险继续使用既有精确发行包匹配与版本算法。缺失版本、不可解析范围、未确认影响 Claim、来源冲突均不能产生确定影响或安全结论。Rule 文件和 Gate 优先级字节不变，详情见本目录源文件例外清单。

## 6. 真实 HTTP 验收

固定问题：对已指定的 vLLM 0.6.5 演示库存调查 CVE-2025-47277 风险与优先级。

来源：[vLLM 官方公告 GHSA-hjq4-87xh-g4fv](https://github.com/vllm-project/vllm/security/advisories/GHSA-hjq4-87xh-g4fv) 和 OSV 原始记录。实际取得的公告范围 `>=0.6.5,<0.8.5`、修复版本 0.8.5、CVSS 3.1 9.8 及其原始向量均保留引用和哈希；没有用 LLM 填事实。

模型：原 `aegisai-qwen25-planner:latest`；本地 Ollama OpenAI-compatible；原 v4 Prompt。沿用上一阶段独立实测配置的 40 秒 Provider 预算，未改变默认 20 秒配置。

最终实跑结果：5 个 Claim CONFIRMED → 版本 AFFECTED → 风险 HIGH / P1 → Gate PASS → AnswerEnvelope COMPLETE。真实调用身份、所有 HTTP 接口与冻结答案重复读取均已核验。

| 记录 | ID |
|---|---|
| 调查 | 6af4654c-0390-4959-acd1-6e991eecaefe |
| Planner Run | 574c6aeb-6fde-4dc6-b19b-567711b67159 |
| Investigation Run | 96a16a56-c9cc-47be-add9-09bc9ec8dc66 |
| Verification Run | 7f096e6e-6038-4bab-8305-308d0c247cb9 |
| Risk Run | f441673b-ec73-44a6-adef-ad0d25f15ead |
| Gate | 7305f0b7-1f08-4ee1-b3eb-e5ecfcf7e19f |
| Risk Artifact | ed053a7e-64ff-463b-8478-6906e9d71b19 |
| Answer | 8057bc87-0785-58f6-81b8-e05c7e7c73c3 |

第一次真实 HTTP 请求因必需 semantic_search 没有知识库资料返回 REPLAN_REQUIRED；用原 KnowledgeIndex 和现有缓存 Embedding 索引同一份官方公告后，同一问题通过。首次失败保留在 real-http-receipts.json。最终代码再次实跑 PASS，见 real-http-final.json。

这只是一个范围明确的工程验收：库存 is_demo=true、来源为独立快照库。没有修改旧开发库的 Claim/Evidence，没有伪造企业资产或人工 Ground Truth。实际是否启用 PyNcclPipe、通信端口可达性和补丁是否应用未扫描；HIGH 是既有规则在已声明条件下的结果，不是已验证成功利用。

## 7. 测试结果

本次新增 14 项测试，覆盖完整资产交接、版本/证据追溯、证据状态、缺证据、未知版本、冲突、组件不匹配、库存变更后固定快照及非法消费。

已执行：便携后端 530 passed / 1 explicitly deselected；TypeScript semantic compilation PASS；前端已有测试 23 passed；42 HTTP 操作及 5 Python Schema 组一致；HTTP 导出 10 个文件一致。

第一次全量后端：1419 passed / 1 failed / 24 warnings，全部 1420 项实际执行，无跳过。失败项 test_trace_is_owner_bound_and_links_real_tools_and_artifacts 的资产任务发生 AGENT_OUTPUT_INVALID；该模块独立复查 8 passed，原失败记录保留，未放宽断言或 Runtime。完整隔离复查结果稍后写入 verification.json。

关键命令：

```text
python scripts/ci/run_backend_tests.py
python -m pytest
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
node --test frontend/tests/*.test.mjs
```

全量 pytest 使用新建、空的专用 PostgreSQL 集群：迁移/空数据契约先执行，再执行其他全部测试，避免破坏已有人工作业或演示数据库。第一次端口 55438，复查为另一全新集群 55439。测试环境只用 Mock LLM；真实本地模型 HTTP 记录分别保存，不能相加为业务准确率。历史 1261 不计入本轮执行数。

## 8. 修改文件

新增领域对象及 verification/asset_snapshot 适配器；更新 orchestration/handoff、verification schemas/snapshot/reader、analysis schemas/snapshot、两个 Tool 适配器。增加 5 个测试文件、精确源文件授权清单、CI 单元列表和文档；同步 HTTP/内部 Schema 与 TypeScript 镜像。无数据库 Schema 迁移、无前端页面实现。

## 9. 当前限制

尚无真实企业扫描库存；资产ID/精确组件/版本由注册库存与请求指定，模型不能自主猜缺失字段。仅传资产 ID 而不选择组件/提供版本，可能需要补充信息；现有库存 criticality 保持 unknown。

旧数据的无效证据和未解析表达式仍会阻断，未批量修复采集器或历史数据。本次成功不能证明这些旧案例已经解决。正式 Ground Truth 和 AegisBench 实验不在本阶段。

## 10. 停止范围

本阶段结束后停止，未进入正式评测、公网部署、模型优化或新 Agent。
