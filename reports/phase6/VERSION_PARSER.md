# 基础版本解析 V0

parser_version=version-v0.1。保留 raw_expression、events、explicit_versions、生态、来源 versionType 和 locator。结果只能是 parsed/unsupported/failed；unsupported 不产生猜测的匹配结论。

| 输入 | 支持行为 |
|---|---|
| PyPI >=、<、<=、==，以及简单上下界组合 | packaging.Version/PEP440 校验，保留边界与显式单版本 |
| pre/dev/post/local 版本 | PEP440 有效版本形式可解析，原字符串保持 |
| >=1.0,<=1.0 | 合法含端点单版本区间 |
| >=1.0,<1.0 或 introduced=1.0/fixed=1.0 | 空的严格区间，unsupported |
| OSV PyPI ECOSYSTEM events | introduced=0 哨兵、fixed、last_affected、limit 分开；多段事件顺序全部保留 |
| CVE CNA lessThan/lessThanOrEqual | 只表示 affected 边界；lessThan 转 limit，不推断 fixed release |
| GIT、SEMVER、非 PyPI 范围、通配符、自然语言、~=、>、CNA changes/custom等非Python明确类型 | unsupported 并保留原文 |
| 空字符串 | failed，不自动填版本 |

SEMVER 的 build/prerelease 排序不能冒用 PEP440；当前明确留 unsupported。OSV 来源原生 fixed 可以保存为显式修复版本事实候选，但本阶段没有做 Patch/commit 关联。CVE 受影响上界不具备同等语义，不能宣传为正式修复版本。

CVE适配器 cve-normalizer-v0.2 先检查来源versionType：未提供或明确python/pep440/pep-440才尝试PyPI表达式；显式semver/git/custom等保持unsupported。已登记PyPI产品不能覆盖来源显式声明的另一版本语义。

此阶段提供结构解析，不提供完整生态比较器、资产影响判断或复杂区间代数。多段 events 保留完整，平铺字段只代表首个相应边界，调用者不得忽略原 events 把多段当连续区间。原文/来源时间与 parse_reason 可回查。pytest 边界用例见 test_ingestion_units.py 与 test_normalizers.py。
