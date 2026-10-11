# 数据库审查与当前风险

## 数据库工程视角

43张表由用户要求38模型加五项必要来源/关系对象组成，UUID/外键/唯一/CHECK/部分索引明确。最大宽度主要为范围化Claim而不是巨型Vulnerability；Source/Raw/评分/候选/时序/资产/评测分离。表字段、FK和DDL快照对应，迁移往返及ORM比较为真实PostgreSQL测试。没有万能Entity/Relation、几十层继承或全JSON存储；JSON仅扩展/结构化局部值与范围事件。

## 情报分析视角

Raw准确字节及内容hash不变，Evidence原文/locator/source/time/publisher/lineage回查固定修订，来源两值并存。CVE精确身份单归属，公告可多漏洞，不用aliases union硬合并；不同CVSS版本不是Conflict。缺数据保留null/unknown，未在KEV目录不表示未利用。PoC association与usability分开，Patch完整SHA/适用范围留候选，未启动任何PoC执行。

人工决定在Claim采用层，原Range/CVSS/Evidence不覆盖；Review状态与核验四态分开，Audit保存before/after/actor/理由和幂等指纹。历史不可删触发器及RESTRICT实际测试；这些检查不证明来源真实或语义解析正确，需要后续核验器。

## 比赛评委视角

页面57元素有存储对应及明确服务缺口，知识论文/标准/政策非漏洞类型保留，实际Agent仍P0、资产/人审P1。Benchmark隔离schema+数据集hash+逐题时间/失败/真值状态，不编造准确率/在线率。当前实测成绩只为数据库测试，不能把43表或43测试换算成富化/QA指标。G01能力/授权与Y05健康监控仍依赖未来服务。

## 已知未解决边界

1. 版本解析、实体别名推断、同scope/lineage判定、撤销传播与匹配引擎未实现；FK保证连接，不能证明结论真伪。骨架helper只接受给定精确身份或人审决定。
2. actor须后续认证/授权；生产运行角色最小权限/Secret输入脱敏、HTML/PDF处理/受控URL获取尚未实现。测试trust只监听本机并在验证后停止，不能用于生产。
3. 源/PoC/Patch等当前状态投影与Claim依据一致性要由受控事务维护；直接owner SQL可写无语义证据的状态，不应授予运行用户任意UPDATE。当前无生产API入口。
4. 已测单连接事务、幂等/锁逻辑与真实DDL；未做多进程并发压力、长证据/大列表/连接池性能或备份恢复演练，未宣称SLA。
5. 原文16MiB内保留；大文件Object Storage与许可限制策略待真实量级决定。长URL/PURL唯一B-tree大小限制需源输入校验或后续digest键，不截断。
6. Knowledge/Observation修订与parser版本、Agent citation初始核验revision、Asset stale/recompute要由第6阶段服务遵守契约；当前未启动调度/问答/RAG。中文全文/向量检索未测。
7. 自建hash只验证提取文件与记录一致；EDB官方下载页面未提供独立vendor SHA256，下载使用官方HTTPS与ZIP CRC，运行环境版本真实可查；生产构建需进一步锁供应链校验。

发布前需按真实业务/量级收敛索引与未用接口，不继续扩展通用平台。完成本阶段后停止，下一阶段是后端基础架构+第一批真实源采集+标准化/去重，不自动启动。
