# 独立审查与修复记录

审查使用只读协作审查员；审查员未修改代码、未执行数据库测试。最终结论：没有未解决的Critical/Important，允许收尾。

已修复并有实际失败→通过记录：

1. 原生GHSA上界没有introduced事件；补充原OSV约定的无下界哨兵，并消除逗号区间词序影响。
2. 重复采集skip版本无法触发次日富化；回查同源、Raw与外部ID对应parsed观察，再调用原Scheduler。
3. 显式修复版本未进入DTO；从原normalized_payload读取修复版本、包范围与原始定位。
4. 文献旧版参与当前检索；保留正文/Raw/Chunk/Evidence，归档旧版可见性，新增当前性元数据。RSS A→B→A重新记录当前内容。
5. 历史PoC确认能错误显示有效利用；复用现有trusted_claim与当前Claim revision人工核验要求。
6. 超过100个自有资产分页被截断；移除静默上限，保持稳定排序和实际总数。
7. 条件缓存错用旧validator/请求URL；绑定原请求，200无validator清除旧值；同字节不同URL回归通过。
8. 公开投影泄露资产范围Evidence；按Claim.asset_component_id过滤，库存内容只在授权子接口显示。
9. 新厂商配置遮蔽旧核验分支；恢复共享旧目录，分离native配置，保持精确官方repo scope。

非阻塞Minor：对已知、更旧、带明确版本/更新时间的Feed版次反复回放，会产生立即归档的副本。安全和当前检索不受影响，但未来可复用历史edition减少Chunk/Event计数。未为此扩大范围或修改检索/Agent内核。

审查不评价实时情报准确率、正式Benchmark准确率或生产就绪状态。
