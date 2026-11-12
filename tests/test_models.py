from app.models.base import BaseModel
import app.models as models_module

def test_at_least_50_models_exist():
    model_classes = []
    for attr_name in dir(models_module):
        attr = getattr(models_module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr is not BaseModel:
            model_classes.append(attr)

    count = len(model_classes)
    assert count >= 50, f"Expected at least 50 models, but found {count}"
    print(f"\n[Model Count Verified: {count} models registered!]")

def test_every_model_has_audit_columns_and_soft_delete():
    model_classes = []
    for attr_name in dir(models_module):
        attr = getattr(models_module, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr is not BaseModel:
            model_classes.append(attr)

    required_cols = {'id', 'created_at', 'created_by', 'updated_at', 'updated_by', 'status', 'is_deleted', 'deleted_by'}
    for m in model_classes:
        col_names = {c.name for c in m.__table__.columns}
        missing = required_cols - col_names
        assert not missing, f"Model {m.__name__} is missing audit columns: {missing}"
        assert hasattr(m, 'active'), f"Model {m.__name__} missing active() helper"
