# 数据库合成测试样例

全部数据为SYNTHETIC，不对应真实CVE/资产或Benchmark gold。CVE-2099-9999001仅作为合法ID语法测试。种子构造在backend/tests/conftest.py的seed fixture：1漏洞/3源/3原文/3Evidence/2产品/2范围/1PoC候选/1资产/1Review。每项测试在专用数据库事务中创建，结束rollback，不进入正式业务库。fixture_spec.json是说明性种子定义；真实旧开发种子未更改、仍待人工gold确认。
