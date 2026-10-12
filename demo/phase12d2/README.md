# Phase12D.2 固定场景与诊断复查

本目录不是Benchmark或标准答案。默认复用Phase12D.1的本机Qwen2.5、investigation-plan-v4和20秒Provider预算；没有改Planner提示、模型或业务规则。

- cases.json：初始五类场景，各一次真实HTTP调用，所有失败保留。
- followup-cases.json：两项诊断复查，与初始五次分开记录。
- budget-control-profile.json：只将本次诊断Provider预算从20改为40秒；不覆盖默认profile或系统配置，不表示该预算已获全业务验收。

资产输入引用开发库已有的is_demo=true库存，字段是用户登记而非真实扫描结果。新机器上的库存UUID不同，必须显式配置属于本机用户的资产，不能伪造记录或忽略所有权。

运行本阶段新脚本时，数据库地址只设置在本机进程环境中：

```text
python backend/scripts/probe_investigation_failures.py --cases demo/phase12d2/cases.json --profile demo/phase12d1/local-real-profile.json --output work/phase12d2/scene-receipts.json --ollama-executable <本机已有Ollama>
python backend/scripts/probe_investigation_failures.py --cases demo/phase12d2/followup-cases.json --profile demo/phase12d2/budget-control-profile.json --output work/phase12d2/followup-receipts.json --ollama-executable <本机已有Ollama>
```

脚本临时启动仅本机可访问的HTTP服务，创建带新幂等键的调查，读取本次拥有的审计，结束后关闭临时服务。不会更改正在运行的其他后端进程。若配置、请求或调查失败，输出必须按真实阶段解读；没有Gate结果时gate_status为null。

公开回执在docs/phase12d2。原始测量报告在忽略目录work/phase12d2，仅公开脱敏的计划、审计元数据和失败原因，没有原始模型输出或凭据。

gate-controls.json是独立测试库中明确SYNTHETIC输入的原规则控制。它证明规则在该控制输入下的行为，不算真实模型调查、真实资产验证或安全准确率。
