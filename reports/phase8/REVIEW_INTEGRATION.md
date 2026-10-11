# 资产复核

生产环境的UNCERTAIN且有真实版本Claim时，生成ASSET_MATCH_REVIEW，按component/claim去重；范围冲突priority1，其余priority2。未知且无候选组件仅在自身resolution/match_summary提示补身份，不创建无根Claim或满库Review。

私有资产复核只能通过owner鉴权资产路径查看原文/Claim/Evidence，旧公开复核API屏蔽此类库存上下文。当前没有在真实库伪造human resolution；不得用系统测试fixture充当真实人工确认。未提供完整IAM/用户目录。

BACKEND_GAP：无候选的歧义组件是待补信息列表，不在Claim Review表建立孤立任务；问答按钮/Dify未在此阶段接入。
