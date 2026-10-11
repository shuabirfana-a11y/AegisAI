# 已知边界

1. Phase7本身正式验收PARTIAL：真实来源范围冲突/未确认/unsupported仍存在。此阶段坚持信任门控，因此当前真实demo风险最终仍UNCERTAIN；技术比较升级不等于核验完成。
2.30条资产评测样本均待真实人工ground truth，无准确率/FP/FN。既有Phase7的28条样本未被冒充标注。
3.只有PyPI可靠比较；npm/Git/Maven/NuGet/RubyGems/未知语义不猜。限定本地采集覆盖，不声称完整全球漏洞库。
4.单owner本地Bearer配置；没有生产IAM/TLS/多租户身份目录。资产上下文私有，不外传。Syft可选，未安装。
5.CycloneDX1.6/SPDX2.3 JSON限定规范版；不支持所有SBOM格式。解析时间检查是同步有界输入下的协作检查，并非操作系统强制中断，完整硬截止仍需工程增强。
6.100组件审查修复构建实测见performance_final.json，初次实测performance_actual.json另保留；当前重复SQL较多，不能称大规模CMDB高性能。
7.队列需管理员dispatch/due；没有常驻daemon。重试有上限，服务崩溃回收与并发规模需要部署阶段验证。
8.重要未解析组件无候选时留待补信息，不构造假根Claim；问答/Dify/S05仍待Phase9。原型仍Mock，无前后端资产联调。
9.GitHub公共API限流保留实际失败任务，不修改漏洞事实凑Demo。没有PoC执行或公网扫描。
10.无Git/Docker环境，不伪造commit/镜像上线。文件和日志留在工作区。

性能时序：上述100组件计时在主要审查修复后记录；最后一项unsupported范围覆盖门控修复后已重跑全套工程测试与真实HTTP案例，未重复100组件计时。数值为已记录构建的实际测量，无最终版本SLA承诺。
