# Evidence 实现

Evidence 为实体，具备 claim/source/raw/observation FKs、scope、stance、excerpt、SHA256、原始 URL、published/retrieved、JSON pointer、publisher、lineage、observed_value、信任标记。原文与历史 Evidence 受22个不可变保护约束。

同 claim/observation/locator/stance 幂等；必须一致的 source/raw/observation 链。SUPPORT/CONTRADICT/NEUTRAL 保留原始值，冲突时两边来源不会覆盖。当前修订与30天新鲜度由核验使用；历史仍可查询。GET evidence/{id} 和漏洞 evidence 分页可直接追溯，返回 JSON 数据，不执行 HTML/README 指令。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。
