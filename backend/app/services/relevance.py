from app.services.products import canonicalize,registry

def assess(record):
    for package in record.packages or []:
        if canonicalize(name=package['name'],ecosystem=package.get('ecosystem'),purl=package.get('purl'))['registry_match']:
            return {'result':'relevant','method':'package','reason_summary':'Exact registered AI package: '+package['name']}
    for product in record.products or []:
        if canonicalize(name=product['name'],vendor=product.get('vendor'))['registry_match']:
            return {'result':'relevant','method':'product','reason_summary':'Explicit registered AI product: '+product['name']}
    text=' '.join([record.title or '',record.description or '']).casefold()
    hints=['machine learning','large language model','neural network','pytorch','vllm','tensorflow','hugging face','langchain','mlflow','gradio','llamaindex']
    if any(hint in text for hint in hints):
        return {'result':'uncertain','method':'rule','reason_summary':'AI keyword only; identity not established'}
    if record.packages or record.products:
        return {'result':'irrelevant','method':'rule','reason_summary':'No current registry or AI context match; V0 result is revisable'}
    return {'result':'uncertain','method':'rule','reason_summary':'Insufficient product/package identity'}
