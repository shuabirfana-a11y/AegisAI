# 核心业务对象

本阶段仅定义对象语义、存在理由和关系。这里没有数据库表、主键、索引、外键、迁移或ER物理结构；后续数据库阶段再映射。对象/术语均是团队设计，不是官方指定类名。

| 业务对象 | 是什么/为什么存在 | 关系 |
|---|---|---|
| Intelligence Item | 漏洞/AI风险事件/知识信息的业务入口，避免只有CVE才能入系统 | 连接Vulnerability、Knowledge Document、Claim、Intelligence Event |
| Vulnerability | 某安全问题的主体及有效/撤销状态，可关联CVE或其他外部身份 | 影响Product/Package/Version Range，连接Claim、Advisory、POC、Patch |
| Product | 用户理解的软件/框架/AI组件产品 | 拥有Package/可审核别名，与资产和漏洞连接 |
| Package | 有生态/包名/PURL等明确身份的分发组件 | 属于Product，连接Version Range与Asset |
| Version Range | 来源表达的受影响边界/显式版本及未知状态 | 属于源Claim，作用于Package/Vulnerability |
| Source | 信息发布/获取入口、类型、权威范围与使用条款 | 产生Source Observation，原始发布者和聚合平台分开 |
| Source Observation | 一次获取及其来源时间、上游和修订身份 | 关联Source、Raw Document、Evidence、Sync Task |
| Raw Document | 不变的原始响应/文档及Hash，保留未知字段 | 被Observation和Evidence定位；正文不充当指令 |
| Claim | 带适用范围的事实/候选结论，如影响版本或某PoC关联 | 同Claim多Evidence，多值冲突并存，连接主体与Review Task |
| Evidence | 支持/反驳/上下文的原始位置、发布者、时间和Hash | 来自Raw/Observation，连接Claim与回答引用 |
| POC | 验证代码线索及相关性/可用性状态，不是执行任务 | 关联漏洞、版本、repo和Evidence；未经确认保留候选 |
| Patch | 修复代码候选及分支/适用范围，非默认已修复 | 关联漏洞、产品、版本、Advisory与Evidence |
| Advisory | 厂商或安全组织公告与修复/缓解原文 | 连接漏洞、产品、明确fixed与Evidence |
| Knowledge Document | 论文、分析文章、技术标准、政策法规等有类型/版本的知识资料 | 连接Source、Raw、Evidence、问答；漏洞关系是候选或确认关联 |
| Paper | 学术论文ID/版本/作者/摘要及原文许可 | Knowledge Document一种，连接候选技术关联与Evidence |
| Standard / Policy | 标准或政策法规的官方出处、版本、发布/生效信息（可缺） | Knowledge Document类型；不默认生成适用法律判断 |
| Asset | 用户授权登记的组件、版本、部署/暴露信息 | 连接Product/Package及Asset Impact；演示配置与真实资产明确区分 |
| Asset Impact | 某资产与漏洞关系的affected/not_affected/unknown判断 | 连接Asset、Version Range、Claim/Evidence及处置建议 |
| Intelligence Event | 发现、更新、撤销、新证据、复核或风险变化事件 | 关联主体、Observation、Claim与时间 |
| Review Task | 对候选/冲突进行确认或保持未知的工作项 | 关联Claim、Evidence、审核者及修订，不删除来源 |
| Sync Task / Run | 周期/按需获取任务和一次运行的业务结果 | 关联Source、Observation、失败/回补/覆盖状态 |
| Query Session | 用户问题、上下文、受控工具结果和引用回答 | 连接Agent任务、Claim/Evidence；不将回答自动写回事实 |

同一Claim可有多份Evidence；同一漏洞可有不同范围与结论；POC/Patch候选及已确认状态不同；论文/标准/政策保留自身身份而不假造CVE。风险由来源、版本、资产与时效解释，不预先冻结任意CVSS×概率乘积。


需求属性与来源的完整登记以 [FEATURE_LIST.md](FEATURE_LIST.md) / [requirements.json](requirements.json) 为准；具体实现尚未开始。
