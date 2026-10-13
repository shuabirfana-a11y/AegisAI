# Phase 13-F.2 实施计划

基线：e55f6783b3df0c963c5046620be634a8e51b65b7；AegisAI 独立工作树，分支 codex/phase13f2-planner-contract。
直接执行用户已指定的最小修复范围，停止于5题诊断，不运行39题评分。

1. 读取原35个Planner私有诊断、原Question及F.1请求记录。每题保存原问题、输入完整性、脱敏候选计划、全部尝试错误、A/B/C/D分类及多因关系；原记录不回写。
2. 在evaluation添加BenchmarkQuestionContract，只从Question.input_context及真实拥有的资产绑定建立请求；无版本是一种明确缺失状态，不能填值。Evaluator、Gold、原问题不改。
3. InvestigationPlanner仅增加模型侧作用域JSON Schema和v5提示约束：既有工具参数必须精确等于输入，缺版本禁用版本工具但保留input_required；真实模型仍自行规划任务。原Validator、角色白名单、Runtime不变；无自动任务补全、无回退Mock。
4. 冲突交接增加VERIFY_ONLY：仅完整来源冲突观察可交核验，失败/缺失/阻断任务继续保留；新增VERIFY_ONLY分支不运行风险分析、不视为成功。原来完整冲突的CONTINUE路径保持既有Risk/Gate判断。既有结构化InvestigationArtifact.conflicts与Evidence原样关联；增加内部、不可变ConflictEvidenceArtifact，保存于Verifier的冻结输入快照，引用原Artifact/Claim/Evidence，不产生新来源事实、不改变核验规则。公开VerificationArtifact既有conflicts继续输出规则判定。
5. 控制先RED再GREEN。真实测试固定5题，在新隔离库中复制原来源图，不复制旧运行/资产/Gold；仅从原输入登记中性演示资产。冻结模型、提示、代码/来源哈希，然后每题只创建一次调查（正常Planner两次尝试允许）。保留失败/UNKNOWN/冲突。
6. 回归、契约检查、独立代码审查、结果包及PHASE_13F2_RESULT.md；经既有授权提交草稿PR，禁止自动合并。

验收依据是合法且可审计的规划、结构化冲突核验与诚实的5题结果；Gate仍可拒绝。不得把Gate通过等同语义准确，不为提高分数复制发现字段至答案。

保护：Gold/评分器/原实验归档、Runtime、Validator、专业Agent执行、Risk/Gate规则及模型制品；仅上述输入、Prompt/模型侧Schema和交接快照适配允许改。

风险：模型侧Schema增大解码成本；未知版本必须仍被阻断；VERIFY_ONLY若被误用会把不完整数据当完整，所以须有缺源/部分/失败/非冲突拒绝测试，Gate未完成任务检查仍独立运行。
