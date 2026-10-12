# 前端需要知道的模型联调状态

2026-10-12，AegisAI Phase12D：**PARTIAL，完整真实调查尚未成功，比赛Live演示未就绪。**

八个调查HTTP操作不变。TraceResponse新字段：

```typescript
model_execution?: {
  execution_mode: 'MOCK' | 'REAL';
  provider: string;
  model: string;
  source: 'PERSISTED_PLANNER_CALL';
  attempt_count: number;
} | null;
```

以包内 `api/reference/investigation-http.d.ts` 为实际契约。没有保存模型调用时为null，显示“调用身份尚未确认”。MOCK/REAL来自保存回执，不依据当前后端配置重新标记历史调查；REAL只标识使用非Mock Provider，不意味着规划、核验或答案成功。

当前创建响应旧model_provider/is_mock语义保持原样，同键复用时请用Trace字段显示本次存储执行身份。调用失败也可显示REAL，同时显示PLANNING_FAILED和失败原因；不要把model_execution为空当Mock，不要把失败调查画成三个Agent已完成。

实际本地模型默认配置：健康、文本、小型JSON5/5；两种Planner场景0/2；完整真实HTTP调查没有Agent/Artifact/Gate结果。Integration可能409 RESULT_UNAVAILABLE，Answer HTTP200仍可能answer_status=FAILED。前端必须按业务状态展示空、失败、待补输入等情况。

既有成功示例和Mock JSON依然属于受控合成/历史样例，不是实际本地模型成功输出。包内 `PHASE12D_VERIFICATION.json`明确区分记录来源，不能据此宣传安全准确率。

前端继续调用同源后端API；不调用11434，不连接Python内部服务，不持有模型Key。Answer仍为确定性模板/FROZEN_GATE_CONTEXT，读取答案不会额外调用模型。没有修改本包API Client或队友页面。
