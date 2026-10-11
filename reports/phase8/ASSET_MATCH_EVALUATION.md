# 资产匹配评测准备

已有30条候选离线输入，涉及三个真实漏洞与原始Claim/Evidence，版本为人工配置的评测输入；字段human_label_status=PENDING/reviewer=null/ground_truth=null。不是已人工gold。

SampleSize30，Correct0，Incorrect0，Uncertain30（标注待定）；FalsePositive/FalseNegative/Accuracy均null，不能把无标签写成0%错误。候选schema和真实规则单测明确分离，测试断言独立给定；既有250组性质检查不充当比赛准确率。

性能实测：100组件导入含首次风险计算56776.760ms；100组件确定性匹配38872.548ms；100组件重算54447.694ms；单asset风险查询1405.008ms，300候选pair。受控重复实例性能负载为合成inventory，不是生产SLA。

性能时序：上述100组件计时在主要审查修复后记录；最后一项unsupported范围覆盖门控修复后已重跑全套工程测试与真实HTTP案例，未重复100组件计时。数值为已记录构建的实际测量，无最终版本SLA承诺。
