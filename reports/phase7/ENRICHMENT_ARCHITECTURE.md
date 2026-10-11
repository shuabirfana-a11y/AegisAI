# 情报富化架构

复用 Phase6 标准化记录、关联 ID、产品标识、参考链接与不可变原文。`app/enrichment/` 划分 contracts、controlled acquisition、context、六类 enricher、repository、evidence、verification、conflict、review、integration、service、scheduler 与 queries。新增固定 0002 迁移的两个表；0001 未修改。

EnrichmentService 按明确依赖顺序执行本机任务，每任务独立事务。网络原始字节独立提交在 JSON 解析之前，域事务失败不删除原文；任务终态另外提交。输出统一 EnrichmentResult 和结构化 artifact。SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 有不同语义。手动首次/事件触发调查与每日到期排程可用，未部署常驻队列。

所有外部内容携带 UNTRUSTED_EXTERNAL_CONTENT。没有 LLM、Agent、Dify 或未知仓库代码执行。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。
