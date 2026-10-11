# Intelligence Timeline

后端保存 IntelligenceEvent，event_key 幂等；不是前端拼接。真实富化可产生 VENDOR_ADVISORY_FOUND、POC_CANDIDATE_FOUND、POC_CONFIRMED、PATCH_FOUND、FIX_VERSION_FOUND、KEV_ADDED、EPSS_CHANGED、CONFLICT_DETECTED、REVIEW_CREATED、REVIEW_RESOLVED、VERIFICATION_CHANGED。发生时间未知时为 null，检测时间有值。

VULNERABILITY_DISCOVERED 的历史发生时间不反向编造；Phase6 没有产生该 Timeline 事件时保留为空，这属于 BACKEND_GAP。API 返回持久化事件，真实运行中不存在的事件类型不会编造出来。

实际测试见 [TEST_RESULTS.md](TEST_RESULTS.md)，真实运行见 [REAL_CASES.md](REAL_CASES.md)。Phase1–6 历史报告与原文保持冻结。
