# Claim Evidence 与核验历史

Claim以claim_key、typed root(subject漏洞或知识之一)、typed subject、predicate、结构化value_json以及scope_key表达结论。subject可为Product/Package/Range/PoC/Patch/CVSS/AssetComponent之一，避免万能entity_id。scope包含生态包、分支、评估版本/类型、as_of；scope_key由调用方确定性构造，数据库不能替代范围解析。

Evidence必须关联存在的raw、source、observation和Claim，并保留原文片段hash/locator/实际URL/出版与获取时间/publisher/lineage/observed_value。scope复合FK不允许不同scope伪装contradict。same raw/locator/stance重复不能重复Evidence。支持/反驳/中立只是该命题的关系；不是整条漏洞“可信认证”。转载同lineage不增加独立票。

四态pending/confirmed/insufficient/conflict存在Claim当前投影及不可变VerificationResult。每个Claim revision最多一份核验结果，VerificationEvidence将实际引用的Evidence与结果同Claim约束。Result保存method、理由摘要、human/system操作者、时间、采用值与decision_key，禁止私有Chain-of-Thought。重要当前投影变更须在受控事务内追加新Result/Audit；原Observation、Range、CVSS和Evidence不覆盖。

真正Conflict：先证明同对象/生态包/分支/CVSS版本/评估时间/字段定义，再保存support和contradict的原始不同值及结果status=conflict，Review关联同Claim。仅缺数据是insufficient；CVSS4.0与3.1不同值是并存评估。DB不做自动来源投票或Conflict检测；TEST-04验证同scope矛盾的持久化能力，未来检测器由第6阶段实现。

采用CVSS使用Claim.cvss_assessment_id，原评分多源并存；当前主严重度是可重建展示投影，不能作为唯一原事实。adopted同root/predicate/scope部分唯一。PoC可信关联与usability对应不同predicate，不能因URL存在把候选变confirmed或verified_usable；Patch/知识关系同样经Claim+Evidence+Result。

AgentCitation钉住Evidence及存在的Claim核验revision，提供assertion_summary；即使未来Claim改变，引用raw仍不可变。生产问答必须对初始pending revision也创建核验记录才能引用，不能引用不存在修订。强FK只证明关联一致，事实真伪/许可/实际actor权限仍由后续业务服务核验；本阶段没有模型或外部工具调用。
