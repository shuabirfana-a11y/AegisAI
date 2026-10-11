import re

def route(question,*,target=None,asset_id=None,mode='auto'):
    q=question.casefold()
    blocked=bool(re.search(r'执行.{0,20}(shell|python|命令)|run\s+(shell|python|command)|ignore\s+(previous|all)\s+instructions|忽略.{0,12}(规则|指令).{0,20}(执行|泄露)|(任意|arbitrary)\s*(sql|url)|泄露.{0,8}(token|密钥)',q))
    blocked=blocked or bool(re.search(r'(执行|运行|跑一下|跑这个).{0,16}(?<![a-z0-9_])(poc|exploit|proof[- ]of[- ]concept)(?![a-z0-9_])|\b(run|execute|launch)\s+(?:(?:this|the|a)\s+)?(?:poc|exploit|proof[- ]of[- ]concept)\b',q))
    cves=list(dict.fromkeys(re.findall(r'CVE-\d{4}-\d{4,}',question.upper())))
    if target:cves.insert(0,target)
    asset=bool(asset_id or any(x in q for x in ('我的资产','资产风险','affect my','my asset','inventory','my inference components'))
        or re.search(r'我的\s*.{0,16}(组件|推理|训练|部署|服务|vllm|pytorch|mlflow)',q))
    product=next((name for name in ['vllm','mlflow','pytorch','torch','langchain','transformers'] if re.search(r'(?<![a-z])'+name+r'(?![a-z])',q)),None)
    semantic=not cves and not asset and not any(x in q for x in ('最近','漏洞列表','recent','list vulnerabilities','系统状态','system status'))
    deep=asset or bool(product and not cves) or len(cves)>1 or any(x in q for x in ('调查','多跳','证据链','investigate','multi-hop','交叉核验'))
    if mode=='deep':deep=True
    if mode=='fast' and not deep:deep=False
    days=re.search(r'(\d{1,3})\s*(天|days)',q)
    return {'path':'deep' if deep else 'fast','retrieval':'hybrid' if deep else 'semantic' if semantic else 'structured',
        'targets':list(dict.fromkeys(cves))[:3],'asset':asset,'asset_id':str(asset_id) if asset_id else None,'product':product,
        'high_severity':bool(re.search(r'高危|严重|high|critical',q)),
        'days':min(int(days[1]),365) if days else None,'blocked':blocked,
        'router':'bounded-rules-v1','model_capability':'DETERMINISTIC_ONLY; no generation model configured'}
