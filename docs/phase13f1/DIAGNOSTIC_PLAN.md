# Phase 13-F.1 有界诊断方案

用户授权：定位原37条FAILED与2条未匹配，修复评测/数据适配问题，仅实跑事实、版本、风险各1题，不改模型、Agent、Gate、金标或评分标准，不重跑39题正式实验。

已确认的边界：39题均被API接受且是REAL模式；35个Planner计划未通过现有验证，2个langchain版本调查因来源冲突没有Verification Artifact。另2个vLLM版本调查返回UNKNOWN，与人工AFFECTED/NOT_AFFECTED不匹配，ID和原问题一致。

输入适配的两处修复：

1. 读取单对象`input_context.asset`，携带原版本；不静默覆盖顶层冲突字段、不接受同时指定的asset/assets。原虚拟ID和场景标签不进入API。
2. facts/PoC/Patch使用已有overview_v1，仅传原问题与目标；组件名称是公告提示，不升级为AssetScope.component触发现有Planner资产/版本约束。资产任务继续要求真实拥有的asset_id/component_id及原组件、版本。

修改范围：evaluation/bench/http_investigation.py、针对性回归测试、诊断资料及阶段状态。评分器不改，旧实验归档不回写。先实际复现5失败/1通过，再运行114项评测测试通过。

固定诊断题（在新调用前选定）：

| 类别 | 原题ID | 选择依据 |
|---|---|---|
| 事实 | GHSA-53q9-r3pm-6pq6-facts | 原overview组件提示触发VERSION_INPUT_REQUIRED |
| 版本 | GHSA-935w-9g4m-p28p-affected | 原API/投影成功但UNKNOWN，检查真实业务拒绝而非ID错配 |
| 风险 | GHSA-53q9-r3pm-6pq6-risk-affected | 原asset内版本未进入请求，验证补传 |

诊断数据库只复制封存的来源图，排除旧资产/Agent/Artifact；创建2个中性演示资产。沿用原Qwen2.5制品、40秒Provider及180秒HTTP预算、investigation-plan-v4，不调Prompt。只创建3个新调查，失败也保存，不选最佳输出。

每题保存原请求、状态、Trace、Artifact、Gate、Answer及评测状态；诊断只证明边界是否正确，不输出新正式准确率。若剩余问题属于Planner/Agent/证据业务，报告后停止，不越界优化。
