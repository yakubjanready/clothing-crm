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
from app.models.inventory import Inventory, InventoryItem, InventoryStatus
from app.models.permission import Permission
from app.models.position import Position
from app.models.product import Gender, Product
from app.models.product_variant import ProductVariant
from app.models.role import Role, RoleName
from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseType

__all__ = [
    "ActivityLog", "AuditAction",
    "AttributeValue",
    "Brand",
    "Category",
    "Department",
    "Employee", "EmployeeStatus",
    "Gender",
    "Inventory", "InventoryItem", "InventoryStatus",
    "Permission",
    "Position",
    "Product", "ProductVariant",
    "Role", "RoleName",
    "Stock",
    "StockMovement", "MovementType",
    "User",
    "Warehouse", "WarehouseType",
    "role_permissions", "user_roles",
]
