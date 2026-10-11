# Fresh-context final review

只读独立审查：gpt-6-astra high，未操作数据库/进程/网络或写文件。初次结论：0 Critical、8 Important、1 Minor，With fixes。源审查结果由当前阶段ledger记录，下面问题进入一次RED→GREEN修复，不再重复派发审查。

1. Public vulnerability aggregate仍包含私有asset reviews。
2. 当前风险投影未比较证据新鲜度/新SourceObservation或range/claim依赖，Phase6无事件时不能针对重算。
3. 采用的旧人工结论有新反驳证据时，资产gate仍可给确定影响或处置。
4. 同observation多个区间仅被一个局部Claim覆盖，丢失完整union。
5. CycloneDX无PURL metadata根的子组件未遍历，可误当空清单移除。
6. 同ref不同未解析包都package_id=null，未识别身份替换。
7. 已耗尽失败job即使后来重算成功仍永久stale。
8. product级Patch/公告被提升为具体包/分支适用。
9. Minor重新分级Important：expiry后snapshot引用旧确定Match，影响证据链，应进入同轮修复。

Declined to judge及裁决：生产环境/部署未提供，演示标签保留；人工gold指标不能测，保持待标注；运行报告实测单独验证；其他生态/规范版本用UNKNOWN；高可用部署延期，但队列正确性属于本轮。无虚构完成。

Final resolution: all nine findings addressed in the single fix pass. Public aggregate excludes private reviews; source/evidence dependency signatures and expiry invalidate snapshots; dispatcher covers package Claims without ranges and source deltas without events; current contraindications/conflicts/unreviewed evidence block trust; full observation unions remain represented; nested metadata components import correctly; unresolved identity replacement preserves history; old exhausted jobs do not poison newer results; product-related Patch applicability remains UNKNOWN; expiry changes Match FK.

13 final regression cases were observed failing before their fixes. Final full suite292 passed/0 failed/0 skipped; one third-party AnyIO deprecation warning. Actual final HTTP34 checks include public aggregate privacy and default401 protection. performance_final.json records the main review-repair matching/gate build; initial timings remain historical. No second reviewer or repeated review loop. No unaddressed Important finding; broader unsupported scopes remain in KNOWN_ISSUES.

性能时序：上述100组件计时在主要审查修复后记录；最后一项unsupported范围覆盖门控修复后已重跑全套工程测试与真实HTTP案例，未重复100组件计时。数值为已记录构建的实际测量，无最终版本SLA承诺。
