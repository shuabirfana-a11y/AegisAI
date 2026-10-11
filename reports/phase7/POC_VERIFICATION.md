# PoC 静态核验

PocVerificationService 使用可解释特征：精确 CVE、产品词、漏洞机制、复现说明、版本提及/影响范围命中、官方独立引用、fork 与 scanner/list 负面特征。Stars 不参与真实性判断。仅名字带 CVE 不会 Confirmed；scanner/list/明确其他 CVE 为 REJECTED，缺关键信息为 INSUFFICIENT_EVIDENCE。

强静态关联还需命中已知受影响版本和独立明确引用。核验状态不等于利用可用性；usability_status 始终 not_evaluated。README base64 解码有512 KiB限制，外部文字仅作为数据。复杂描述语义与 README 复制检测未达到完整覆盖，因此候选可留人工复核，不宣称检测全部攻击代码。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。
