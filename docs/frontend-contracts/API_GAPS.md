# 当前未开放的能力

更新：2026-10-11，Phase12-C。调查提交、状态、Trace、Artifact、Integration、Answer、取消、历史已开放为 `/api/investigations` 的八个操作。`/api/v1/investigations` 不存在，不能据历史提案生成调用。

| 能力 | 状态 | 最小后续适配建议 |
|---|---|---|
| 新调查完整Task Run明细 | API_NOT_EXPOSED | 先确定白名单；现有trace仅task_statuses和工具摘要，不暴露Prompt/内部控制字段 |
| 聚合的内部InvestigationContext | INTERNAL_ONLY | 前端使用现有分项接口；不要原样开放actor/stage_keys/控制上下文 |
| SSE / WebSocket推送 | API_NOT_EXPOSED | 当前有限轮询已经可用；若后续新增，保持主体授权、revision和断线语义 |
| 跨进程队列、重启自动续跑 | BACKEND_REQUIRED | 当前进程内工作线程；recovery_required只表示待恢复，不承诺自动执行 |
| 多用户登录与团队权限 | BACKEND_REQUIRED | 当前服务端令牌主体；正式身份系统另行设计和授权 |
| 全局情报趋势、CPU/内存/模型实时遥测 | BACKEND_REQUIRED | 定义真实指标口径后再实现；页面不造随机值 |
| 公网域名访问 | BACKEND_REQUIRED | 当前Node代理只允许本机Host；部署和发布另行授权 |

上述建议没有虚构可调用URL，也没有在本轮增加接口。7个原有写操作的代理限制另见当前API清单，属于PROXY_BLOCKED。真实模型未配置是运行条件缺口，不是缺少调查HTTP接口。
