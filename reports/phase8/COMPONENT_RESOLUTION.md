# 组件身份解析

PURL精确→PackageIdentifier UUID→ecosystem/name/namespace→明确ProductAlias→UNRESOLVED。只读既有产品库、confirmed别名和人工维护注册表。PURL/display label可不同，但显式package_name/生态/namespace/版本矛盾报错，不能fallback猜身份。PURL qualifier/subpath存在时需精确标识，不能误当另一分发版本。

返回RESOLVED/AMBIGUOUS/UNRESOLVED、method/matched_product/matched_identifier/reason_summary和候选ID。无相似度/LLM，npm vllm不会合并PyPI，PyTorch明确别名可对应torch；显式PyPI pytorch不擅自当torch。
