# Phase9 当前真实样例

| Case | 最终状态 | Gate | 工具调用 | 本次延迟 |
|---|---|---|---:|---:|
| fast | COMPLETED | PASS | 2 | 5.094s |
| deep-conflict | WAITING_REVIEW | HUMAN_REVIEW_REQUIRED | 5 | 14.828s |
| deep-asset | WAITING_REVIEW | HUMAN_REVIEW_REQUIRED | 11 | 16.797s |
| deep-product | WAITING_REVIEW | HUMAN_REVIEW_REQUIRED | 11 | 14.312s |
| semantic | COMPLETED | PASS | 1 | 4.719s |
| abstention | FAILED | REPLAN_REQUIRED | 2 | 4.125s |
| injection | FAILED | FAILED | 0 | 0.547s |
| poc-execution | FAILED | FAILED | 0 | 0.547s |

真实数据/后端运行，资产均明确Demo，无生成模型。JSON保留每次plan/tasks/trace/证据/结果/逐任务状态变化。5次最终验收逻辑检查通过，没有经过Dify。8个样例不能作为正式精度或P95；POC执行及Shell拒绝均0工具。
