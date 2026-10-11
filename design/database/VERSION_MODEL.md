# 版本范围与生态语义

AffectedVersionRange关联Vulnerability/Product/Package/Source/Observation，并留raw_expression、introduced/fixed/last_affected/limit、range_type、events、explicit_versions、branch/scope、parser版本/状态/原因。一个漏洞多产品，一个产品多区间；显式版本列表与事件序列并存。Package.product复合FK防止同名包跨产品串联。

parsed仅表示产生机器可比较表示；CHECK至少有机器字段，仍不能证明边界语义正确。unsupported/failed保持原始表达和reason，固定版本留null，不用LLM猜。OSV introduced=0保存标记原义，不当版本0.0.0；last_affected为含上界，不推导fixed；limit是排他边界不一定是修复。多个OSV events按原顺序保存，包括不同introduced/fixed段；CVE versionType/status/changes、版本原比较符及包分支定位保留events/metadata和raw。

PyPI后续用PEP440比较，npm可用生态SemVer规则，GIT按repository/commit拓扑，Maven/Go/Container规则单独验证；不能一把SemVer比较所有源。名称也按生态规范，CPE和PURL不当同一编码。此阶段只实现存储，不实现解析/匹配引擎；TEST-06验证unsupported保留原文，TEST-08验证已给出结果的范围FK与快照。

来源版本范围不可变，修订时新Range/新候选观察，人工采用通过Claim/Verification/Audit层，不修改旧Range。Query只返回某package/scope/as_of适用的当前采用范围；未知版本、歧义版本或没有明确范围→unknown。资产2.x不得补成2.0.0；升级版本的影响要重新评估，旧匹配以inventory_revision和version_at_evaluation回看。

后续解析器必须覆盖pre-release、post/dev/local、多区间、withdrawn、explicit versions、缺失、最后受影响与fixed差别以及schema变化，记录支持率与错误率而非去掉难例。数据库未证明版本引擎性能或准确率。来源字段与原规则入口为SOURCE_FIELD_MAPPING/NORMALIZED_RECORD_DESIGN，范围语义发生改变需迁移/解析器版本并可从raw重放。
