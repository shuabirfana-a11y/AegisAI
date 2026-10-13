# 首轮失败诊断材料

入口：[PHASE_13F1_RESULT.md](../../../PHASE_13F1_RESULT.md)。

- original39-debug.jsonl：从封存记录读取的39题多层诊断，含原问题输入、HTTP请求/状态、Planner最终错误和输出后的字段比较。
- original39-summary.json：35规划失败、2业务Artifact不完整、2UNKNOWN不匹配；Loader/HTTP/REAL模式及问题ID绑定核对。
- diagnostic3/：修复后固定3题真实HTTP记录、Trace/Gate/Answer和真实模型规划审计；属于诊断，不是新正式Benchmark。

所有Gold字段仅出现在离线比较资料。它们没有进入模型、检索或HTTP请求。原39题失败、标准答案和统计未改写。

评价状态与业务状态分别保存：FAILED可能是评测器拒绝不完整业务链，并非HTTP失败；SUCCEEDED只表示数据可投影。Gate通过的有限总览也不证明CVSS/CWE等完整事实已交付。
