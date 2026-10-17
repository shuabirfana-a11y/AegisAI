# 8 题黄金回归结果

模式：两次真实本地模型 HTTP 全链路诊断。修复前 12 份原始来源；修复后保留这些来源并增加 1 份实际读取的官方公告。金标、模型、Prompt、Gate、评分公式不变。
整题匹配：3/8 → 4/8。已有三题均保留；没有把缺版本或冲突问题改成确定判断。这是选定 8 题的结果，不能外推为 49 题准确率。
计分字段：4/12 → 5/12。

| 题号 | 修复前 | 修复后 | Gate |
|---|---|---|---|
| GHSA-935w-9g4m-p28p-affected | {"affected":"AFFECTED"} | {"affected":"AFFECTED"} | PASS_WITH_WARNINGS |
| GHSA-935w-9g4m-p28p-fixed | {"affected":"NOT_AFFECTED"} | {"affected":"NOT_AFFECTED"} | PASS_WITH_WARNINGS |
| GHSA-935w-9g4m-p28p-multihop | {"priority_asset_ids":["demo-GHSA-935w-9g4m-p28p-affected"]} | {"priority_asset_ids":["demo-GHSA-935w-9g4m-p28p-affected"]} | PASS_WITH_WARNINGS,PASS_WITH_WARNINGS |
| GHSA-53q9-r3pm-6pq6-facts | {"cve":"CVE-2025-32434","cvss_v3":null,"cvss_v4":null,"cwes":null,"summary":null} | {"cve":"CVE-2025-32434","cvss_v3":null,"cvss_v4":null,"cwes":null,"summary":null} | PASS_WITH_WARNINGS |
| GHSA-53q9-r3pm-6pq6-affected | {"affected":"UNKNOWN"} | {"affected":"UNKNOWN"} | REPLAN_REQUIRED |
| GHSA-c67j-w6g6-q2cm-affected | {"affected":"UNKNOWN"} | {"affected":"UNKNOWN"} | HUMAN_REVIEW_REQUIRED |
| GHSA-9rwj-6rc7-p77c-affected | {"affected":"UNKNOWN"} | {"affected":"AFFECTED"} | PASS_WITH_WARNINGS |
| GHSA-53q9-r3pm-6pq6-unknown | {"affected":null} | {"affected":null} | NEED_CONTEXT |

LangGraph：UNKNOWN / REPLAN_REQUIRED → AFFECTED / HIGH / PASS_WITH_WARNINGS。官方影响范围、修复版本、CVSS、CVE 和组件均生成来源绑定证据，通过原核验规则。
本组没有 risk 类型金标题，Risk Match 为 N/A；记录子任务实际风险而不新增金标。Evidence Support 与幻觉率均 PENDING。
8 题修复验证门槛通过，可以另行冻结全 49 题。本阶段未启动新 49 题，以保持诊断与正式实验分开；旧 3/49 原始结果完整保留。
