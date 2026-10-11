# Phase9 independent final review

Fresh read-only reviewer: gpt-6-astra / high. No Critical confirmed. Five Important and three Minor found. This is one review plus one RED→GREEN fix pass, not a second review.

Important修复：

1. 历史Evidence继承Claim可信标记：复用current_evidence/现有可信服务，verified仅表示当前支持且被当前核验采纳；AgentCitation写入再次校验数据库；测试old support/old contradict/核验成员。
2. 必要主查询被语义补充掩盖：Task记录required_tools，必要失败不满足handoff；最终unresolved显式列失败工具。补充成功保留为诊断，不能变成门禁PASS。
3. 被拒handoff仍被使用及自报verified：拒绝后替换blocked Artifact；服务端Gateway保存本run证据/Claim字段指纹receipt，handoff/gate绑定真实工具输出；布尔值与随机UUID不能授予事实权限。
4. realtime=true仍走Fast缓存：强制Deep并实际规划refresh调用，服务端网络许可仍需开启；不知道目标时不声称已刷新。
5. 核心中文题面误查全局列表：所有权问法进入owner inventory；时间/严重程度在截断候选前应用，Unknown仍为候选不冒充高危确认。

9个回归用例先全部RED，修复后专项24GREEN，全量353GREEN，真实浏览器再次41GREEN；RED/GREEN日志均保留。

Minor延期：运行中tasks接口的逐任务状态仍pending（整体状态与事件真实）；Dify输入4000字与Backend2000字限制不一致（会422，不执行）；“执行这个POC看看”尚未明确路由拒绝（白名单仍没有执行工具，不会运行POC）。

未判定事项的处理：Dify真实运行→PARTIAL直到部署并完成票据后poll/Gate/Evidence验收；LLM规划/协作/生成模型注入→用户明确稍后配置模型，当前不作认证；Benchmark/消融→0人工gold，不给正式分数；宕机/数据库故障/已提交批次恢复→未系统注入、不声称杀worker等于事务回滚；Phase6–8全部业务正确性→复用既有测试和服务、不作全业务重新认证；Fast宽泛与保守弃判→记录回答粒度局限，不误报确定安全。

另外Dify Assistant bridge当前只提交202票据；现有smoke不能单独证明Deep最终答案。后续真实部署必须补上轮询和最终Evidence/Gate检查。


## 本次续作更新

历史审查记录保留。本次续作修复全部3个Minor及Assistant最终验收缺口，新增25项GREEN、全量378GREEN、真实浏览器41GREEN。未发起第二轮独立审查，新增测试及真实运行作为修复证据。Dify真运行和LLM、正式Benchmark仍未认证。
