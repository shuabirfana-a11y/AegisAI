import os,secrets

def asset_principal(authorization):
    token=os.environ.get('AEGIS_ASSET_TOKEN')
    if not token:raise RuntimeError('Local asset access is not configured')
    if not authorization or not secrets.compare_digest(authorization,'Bearer '+token):raise PermissionError('Authentication required')
    return os.environ.get('AEGIS_ASSET_OWNER','local-analyst')
