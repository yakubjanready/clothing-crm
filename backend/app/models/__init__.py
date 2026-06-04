"""Barcha modellar shu yerda import qilinadi — Base.metadata'ga registratsiya uchun.
Alembic env.py va testlardagi create_all shu modulga tayanadi.
"""
from app.models.activity_log import ActivityLog, AuditAction
from app.models.associations import role_permissions, user_roles
from app.models.attribute_value import AttributeValue
from app.models.brand import Brand
from app.models.category import Category
from app.models.department import Department
from app.models.employee import Employee, EmployeeStatus
from app.models.permission import Permission
from app.models.position import Position
from app.models.product import Gender, Product
from app.models.product_variant import ProductVariant
from app.models.role import Role, RoleName
from app.models.user import User

__all__ = [
    "ActivityLog",
    "AuditAction",
    "AttributeValue",
    "Brand",
    "Category",
    "Department",
    "Employee",
    "EmployeeStatus",
    "Gender",
    "Permission",
    "Position",
    "Product",
    "ProductVariant",
    "Role",
    "RoleName",
    "User",
    "role_permissions",
    "user_roles",
]
