# 首批正式实验操作说明

## 当前停止点

首批10个经独立人工确认并导出的 HUMAN_GOLD 尚未存在，本轮停止在13-E.1。正式准确率为未评测，不是0%。下列为将来的流程，本轮没有执行。

## 1. 冻结人工数据

沿用标注/双人复核/导出流程，不更改人工答案迎合系统输出。至少10个合格问题，建议覆盖3事实、3版本、2POC/Patch、2资产风险。正式清单需要新 dataset version、确切问题ID、原问题和来源哈希、标注文件哈希及真实人审记录。旧 machine SOURCE_REFERENCE 不得改标记充当 HUMAN_GOLD。原 Runner 接受 APPROVED/REVIEWED 完成态，但两者都须真实且独立；文件检查不能验证自然人身份。

在项目根目录运行无网络检查，使用新的输出目录：

```powershell
python scripts/check_bench_readiness.py --manifest <正式清单路径> --minimum 10 --output work/phase13e/<新检查目录>
if ($LASTEXITCODE -ne 0) { throw '数据准入未通过，禁止开始正式实验' }
```

不足或数据无效返回3，不发出网络请求、调用模型或运行评分器。返回0仅表示数据门禁通过；模型、Prompt、库存和实验配置仍需冻结。工作流目录的文件数量及49张任务卡不参与正式准入。

## 2. 冻结运行环境

先合并依赖 PR 或明确登记使用的已审查分支，记录准确 Git commit，不假定 PR #13 已合并。复制准备模板到本机 ignored local 目录，填写正式 manifest 及 SHA-256、模型 tag与实际不可变 digest/模型文件 SHA-256、实际Provider、Prompt版本及模板文件摘要、模型参数、原 Runtime 配置、预算、实际资产绑定文件摘要和时间。

未批准前不自动选择新模型，不把 `latest` 当模型版本。模型由服务侧 Model Gateway配置；评测器不能用标准答案向模型补上下文。环境/版本应与原库存观察一致，未知不能补全，多资产不适配需要保留 NOT_EVALUATED 和覆盖缺口。

## 3. 执行完整系统

仅当数据与环境准备完成，使用已实现的公开 HTTP 入口：

```powershell
python evaluate.py --mode online --manifest <正式清单路径> --base-url $env:AEGIS_API_BASE --bindings <本机库存绑定JSON> --timeout 180 --output <新实验结果目录>
```

认证只取本机 `AEGIS_ASSET_TOKEN`。提交问题→原 Planner/Runtime/三 Agent/Gate→冻结 AnswerEnvelope；不可绕过核验或把历史 Mock 输出导入正式对照。前置准入命令和环境冻结是本操作流程的门禁；旧 evaluate.py 的准备模式本身仍可生成 NOT_EVALUATED 检查报告，不宣称已新加一套自动正式实验调度器。

## 4. 检查输出与指标

保留 report、每题预测、原生HTTP记录、experiment.json、待审核输出与错误状态。记录 eligible/scored/failed/NOT_EVALUATED 数量，注明分类分母和覆盖范围。原 Accuracy 对可计分人审题逐例比较所有标准字段，FAILED不当正确拒答；没有可用结果时指标为 null。

Risk Accuracy只针对人工标有 risk_level 的题；优先级使用原生P1/P2/P3/DEFER/REVIEW_REQUIRED，不偷换标注分类。Answer Accuracy、Abstention 与风险分类按原评分器口径计算，不调整业务逻辑提高指标。

Evidence Coverage/Hallucination 需要独立人工 OutcomeAudit，绑定本次 prediction_sha256 并完整审核关键事实、风险和建议；有引用或系统 CONFIRMED不能代替复核。尚未审核则标 NOT_EVALUATED，不能写成0%幻觉。核对输出实际模型/Prompt与冻结配置，漂移、标签泄漏或覆盖缺口都须明确报告。

## 5. 离线复现

人审输出后只回放冻结记录重新计分，不再调用模型：

```powershell
python evaluate.py --mode offline --manifest <同题目和来源的已批准清单> --rescore-report <原结果目录/report.json> --outcome-audit <独立审核jsonl> --output <新离线结果目录>
```

明确标 OFFLINE，保留原模型和延迟，核对原回执/报告/原生记录及来源哈希。新模型输出不能沿用旧输出的 OutcomeAudit。

## 6. 比较和报告边界

先做完整 AegisAI 的10题小样本实验，不必等49题。RAG-only和无Verification独立控制尚未接入，只记录 NOT_IMPLEMENTED。不能把缺少对照的单系统指标称为相对提升；不能把工程测试或固定模型场景成功率当安全答案准确率。正式49题版本须重新登记数据版本、样本依赖簇和覆盖范围。
