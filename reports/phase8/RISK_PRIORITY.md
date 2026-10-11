# 透明优先级规则

规则asset-priority-v1：AFFECTED+已确认KEV→P0；AFFECTED+(confirmedPoC+high/critical，或EPSS>=0.5+high/critical，或critical+用户标internet)→P1；AFFECTED+(high/critical、confirmedPoC或highEPSS)→P2；其他确定受影响→P3。NOT_AFFECTED→INFO；UNCERTAIN/NOT_EVALUATED→REVIEW，不能用猜测输出紧急受影响。

Production/Internet标记是用户声明，用于因素和复核，不直接把Production硬编码P0。Patch/fixed提升可处置性说明，不伪造漏洞风险乘积。无数字AI分。阈值和规则版本在priority.py明确可改并测试。
