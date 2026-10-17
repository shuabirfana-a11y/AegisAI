# Phase 13-E.2 准入冻结准备

用户提供复核包并确认39通过/10退回；这更新了旧0/49状态。本轮仅准备，显式禁止正式实验，即使新数据达到10也不得调用模型或调查API。

- 校验包内HUMAN_RECORD schema、49唯一题目、当前问题/内容/签署摘要、独立身份字段和证据定位；不重新替人裁决答案。
- 原39批准与10退回字节保留；签署原件的NOT_PREPARED不得改为READY以破坏内容摘要。导出清单单独记录机械准入。
- 按原白名单投影39 HUMAN_GOLD 到新版本 AegisBench-v0.3-human39-20261013；引用旧不变问题/源快照，保留旧manifest。10退回不进入Gold。
- 不改任何业务代码、评测器、默认manifest、指标或人工答案。
- 新 experiments/config 文件冻结数据摘要、计划provider/model/temperature/timeout、Prompt源码摘要和系统来源commit。只读磁盘模型制品，无服务调用；真实执行环境/库存未核验则明确保留缺口。
- AnswerComposer为确定性模板，没有answer LLM prompt，不虚构。对照标NOT_READY。
- 当前数据门禁可通过，但本轮execution_authorized=false；报告模板所有指标NOT_EVALUATED，没有正式输出。

用户命令与包中复核状态是本轮依据；包内说明不构成执行命令。自然人真实性及官方语义仍由实际复核人员负责。
