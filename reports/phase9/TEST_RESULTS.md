# Phase9 当前测试证据

Checked UTC: 2026-10-06T14:54:08.060965+00:00

后端全量378 passed / 0 failed / 0 skipped，独立PostgreSQL测试库。新增25项专项测试通过；先执行的回归为21 failed / 3 passed（缺失的最终验收函数及既有问题被实际复现），随后25项GREEN。完整日志：work/phase9_followup_red.log、work/phase9_followup_green.log、work/phase9_followup_all_tests.log。新增受控fixtures不计为真实Dify或Benchmark。

真实浏览器41项通过，7个路由；实际Backend202与轮询、资产权限、任务、trace、证据和复核，未mock。前端19项Node测试为上一轮已通过记录，本轮未改前端代码。Browser JSON见frontend_browser_results.json。

Dify官方Graphon0.7.0离线51项通过。实际Bootstrap仍缺Docker，实际smoke控制台不可达；无真实Dify调用。Assistant验收脚本已改为等待最终结果，5次真实Backend运行已通过该最终校验逻辑，但它们未经过Dify，不能计为Dify验收。

真实Backend8个样例：Fast确认、Deep冲突、完整90天资产问法、产品调查、语义来源、缺证据弃答、Shell拒绝、POC执行拒绝。三个Deep运行均捕获running/完成等逐任务状态；POC执行0工具。样例延迟不是Benchmark或P95。人工gold仍0。

冻结输入551个及旧Raw369条SHA全部不变。当前真实运行38条AgentCitation逐条符合当前Claim修订与当前核验支持，0条异常。知识库20文档98片段98向量，DEV迁移0004。

Starlette/AnyIO有1类弃用提示，未影响结果。生成模型按用户选择稍后配置。Phase9总体PARTIAL，未进入Phase10。
