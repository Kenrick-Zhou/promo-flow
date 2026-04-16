from app.db.base_class import Base  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.content import Content  # noqa: F401
from app.models.feishu_group_chat import FeishuGroupChat  # noqa: F401
from app.models.tag import Tag  # noqa: F401

# Import all models here so Alembic can detect them
from app.models.user import User  # noqa: F401
