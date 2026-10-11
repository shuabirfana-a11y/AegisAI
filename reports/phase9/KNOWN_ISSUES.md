# Phase9 known issues

总体 PARTIAL。

1. 本机没有Docker运行环境；实际Bootstrap退出1。WSL2和Docker Desktop需要宿主机设置；Dify Console/DSL导入/发布/真实Dify→Backend尚未发生。Docker私网到Windows loopback的可达性仍需实际验收。
2. 用户选择“稍后配置模型”。当前只有真实本地384维Embedding；自然语言生成、LLM Agent规划/切换、RAG-only基线均未激活。确定性角色不能冒充完整LLM Agent。
3. 规则路由及候选展开有界；最多3漏洞、8资产、1000向量片段。未声明全网覆盖或所有自然语言问法正确。单漏洞存在任何冲突时门禁较保守，可能同时阻止无冲突字段答案。
4. 人工gold0条；24个候选题仅为准备。没有正式Precision/Recall/F1/消融结论；少量真实查询延迟是运行样例，不能当作基准P95。
5. 资产5个均为Demo，默认owner只看其中3个；另一个owner的性能样本保持隔离。已有Phase8人工标注缺口不因Phase9而消失。
6. 公开执行摘要不含隐藏推理。服务退出重启后的持久化queued/running恢复、长期状态机、缓存TTL及生产发布属于后续明确工作，未宣称实现。
7. Fast目前为结构化确定性结果；真实两次子进程查询存在秒级启动开销。没有无Profile优化或虚构全部<2秒。
8. 模型/原公告再分发须遵守各自许可证。知识索引保留unknown许可标记，不把下载成功当作分发授权。
9. 本轮验证Bearer仅在子进程内存；正常使用时需在本机配置自己的AEGIS_ASSET_TOKEN及owner再启动，不能把验证token当作交付密码。
10. 测试存在Starlette/AnyIO依赖弃用提示，未影响已执行结果。动态网络刷新可能部分更新数据库；杀worker不意味着回滚此前已提交采集批次。

按最新Phase9文档停止，不自行进入Phase10或Phase11，不购买云服务器/域名或发布外网。

本次续作已修复三个Minor：逐任务状态读取最新事件，最终Artifact状态优先；Dify/UI/Backend问题上限统一2000字；明确POC执行请求在工具调用前拒绝。Dify202票据后最终run/tasks/trace/Evidence/Gate轮询验收已实现，真实Dify运行仍受宿主环境限制。旧预审审计仍保留，不纳入当前引用校验。
