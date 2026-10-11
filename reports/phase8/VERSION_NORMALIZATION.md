# 生态版本规范化

PyPI使用既有packaging PEP440，原始版本永久保留。支持v前缀、pre/post/dev/local，不拆点猜版本。local版本保留，但上游范围比较用public version，不假定本地backport修复。[PEP440规范](https://packaging.python.org/en/latest/specifications/version-specifiers/)。

实际数据出现PyPI/unknown/NuGet/Maven/RubyGems，未见npm。npm/SemVer/Git及其他生态尚无已验证策略：UNKNOWN，复杂commit比较不套PEP440。4.x/0.8.2-custom/缺版本未知。250组生成输入验证规范化幂等及包含/排他边界，未新增PBT依赖。
