def test_asset_risk_storage_models_exist():
    from app.db import models as m
    assert hasattr(m,'AssetRiskSnapshot') and hasattr(m,'AssetRiskChange')
    assert hasattr(m,'AssetInventoryEvent') and hasattr(m,'AssetRecomputeJob')
    assert hasattr(m.Asset,'environment') and hasattr(m.AssetComponent,'normalized_version')
