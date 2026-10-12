# Phase 12-D.3：资产风险业务闭环修复结果

状态：Phase 12-D.3 已完成。最终真实 HTTP 场景 Gate PASS；独立审查三项问题已修复，最终完整后端回归 1426 passed，无失败/跳过。

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
| 调查 | e2eec722-e3a6-4452-bc03-1c972fa21ff1 |
| Planner Run | 9753e509-2f8a-4ca2-8b7d-c5bfd6443ec7 |
| Investigation Run | 19896859-9b44-498f-a185-b5dac9aa7bbd |
| Verification Run | 75d29b34-3c67-49f7-b6e3-a91226bccd57 |
| Risk Run | 8eed030a-2a87-4e22-9562-18d2347580e8 |
| Gate | 9ae43a98-aded-4b26-9121-a9fa468b8842 |
| Risk Artifact | 1d0eeb15-a025-4a6f-9346-3f0276131fcc |
| Answer | 3ff1b0a1-5de7-5bc5-998e-b87caba84a57 |

第一次真实 HTTP 请求因必需 semantic_search 没有知识库资料返回 REPLAN_REQUIRED；用原 KnowledgeIndex 和现有缓存 Embedding 索引同一份官方公告后，同一问题通过。首次失败保留在 real-http-receipts.json。证据级状态加固后一次 PASS 保存在 real-http-final.json。独立审查的最小输入修复后，再次使用同一场景实跑 PASS，耗时 68.656 秒，八个接口均通过；最新见 real-http-post-review.json。Planner 第一次输出因 QUERY_SCOPE_MISMATCH 拒绝，第二次由原重试机制通过；两次调用均留存，未改模型、提示词或验证规则。

这只是一个范围明确的工程验收：库存 is_demo=true、来源为独立快照库。没有修改旧开发库的 Claim/Evidence，没有伪造企业资产或人工 Ground Truth。实际是否启用 PyNcclPipe、通信端口可达性和补丁是否应用未扫描；HIGH 是既有规则在已声明条件下的结果，不是已验证成功利用。

## 7. 测试结果

本次新增 20 项测试，覆盖完整资产交接、版本/证据追溯、证据状态、缺证据、未知版本、冲突、组件不匹配、库存变更后固定快照及非法消费；补充旧库存空字段、限定 PURL 四个边界及真实事务过期后的演示导出。

已执行：便携后端 531 passed / 1 explicitly deselected；工程门禁 18 passed；17 个前端 JavaScript 语法检查通过；TypeScript semantic compilation PASS；前端已有测试 23 passed；42 HTTP 操作及 5 Python Schema 组一致；HTTP 导出 10 个文件一致。

第一次全量后端：1419 passed / 1 failed / 24 warnings，全部 1420 项实际执行，无跳过。失败项 test_trace_is_owner_bound_and_links_real_tools_and_artifacts 的资产任务发生 AGENT_OUTPUT_INVALID；该模块独立复查 8 passed，原失败记录保留，未放宽断言或 Runtime。第二个全新空库的完整复查为 1420 passed / 23 warnings / 827.91 秒，无跳过。独立审查后新增六个复现控制：修复前 6 failed，最终 6 passed / 65.40 秒；最终第三个全新空库完整回归 1426 passed / 23 warnings / 900.02 秒，无失败、跳过或 deselection。第一次失败的原因尚未诊断，记录保留，不能称作已定位原因。

关键命令：

```text
python scripts/ci/run_backend_tests.py
python work/phase12d3/run_full_regression.py
python work/phase12d3/full_rerun.py
python demo/phase12d3/run_backend_regression.py
python scripts/ci/check_contracts.py
python scripts/export_investigation_api.py --check
node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json
node --test frontend/tests/*.test.mjs
```

全量 pytest 使用新建、空的专用 PostgreSQL 集群：迁移/空数据契约先执行，再执行其他全部测试，避免破坏已有人工作业或演示数据库。第一次端口 55438，复查为另一全新集群 55439，最终修复后回归使用 55440。公开的最终测试入口是 demo/phase12d3/run_backend_regression.py；前两次内部驱动的真实命令同时保留。测试环境只用 Mock LLM；真实本地模型 HTTP 记录分别保存，不能相加为业务准确率。历史 1261 不计入本轮执行数。

独立审查共 3 项 Important，已同一次最小修复处理：未知生态不充当显式冲突、恢复原 qualified/subpath 适用性限制、导出使用事务内捕获的标量 ID。限定身份保持 UNKNOWN，原 Gate 的 OBJECTIVE_PACKAGE_MISMATCH 为 FATAL，仍 FAILED；没有将其改成 Warning 或 REPLAN。演示准备脚本已实际独立运行并导出本机用例。详见 FINAL_REVIEW.md。

## 8. 修改文件

新增领域对象及 verification/asset_snapshot 适配器；更新 orchestration/handoff、verification schemas/snapshot/reader、analysis schemas/snapshot、两个 Tool 适配器。增加 7 个测试文件、精确源文件授权清单、CI 单元列表和文档；同步 HTTP/内部 Schema 与 TypeScript 镜像。无数据库 Schema 迁移、无前端页面实现。

## 9. 当前限制

尚无真实企业扫描库存；资产ID/精确组件/版本由注册库存与请求指定，模型不能自主猜缺失字段。仅传资产 ID 而不选择组件/提供版本，可能需要补充信息；现有库存 criticality 保持 unknown。

旧数据的无效证据和未解析表达式仍会阻断，未批量修复采集器或历史数据。本次成功不能证明这些旧案例已经解决。正式 Ground Truth 和 AegisBench 实验不在本阶段。

## 10. 停止范围

本阶段结束后停止，未进入正式评测、公网部署、模型优化或新 Agent。
