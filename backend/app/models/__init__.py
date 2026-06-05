"""Barcha modellar shu yerda import qilinadi — Base.metadata'ga registratsiya uchun.
Alembic env.py va testlardagi create_all shu modulga tayanadi.
"""

from app.models.account import Account, AccountType
from app.models.activity_log import ActivityLog, AuditAction
from app.models.associations import role_permissions, user_roles
from app.models.attribute_value import AttributeValue
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer, CustomerSegment, PriceType
from app.models.customer_contact import CustomerContact
from app.models.customer_interaction import CustomerInteraction, InteractionType
from app.models.debt_record import DebtDirection, DebtPartyType, DebtRecord
from app.models.department import Department
from app.models.employee import Employee, EmployeeStatus
from app.models.finance_payment import (
    FinanceCategory,
    FinancePayment,
    PaymentDirection,
)
from app.models.inventory import Inventory, InventoryItem, InventoryStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.notification import (
    Notification,
    NotificationSeverity,
    NotificationType,
)
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.order_return import Return, ReturnItem, ReturnStatus
from app.models.payment import Payment, PaymentMethod
from app.models.permission import Permission
from app.models.position import Position
from app.models.product import Gender, Product
from app.models.product_variant import ProductVariant
from app.models.purchase_item import PurchaseItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.role import Role, RoleName
from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseType

__all__ = [
    "Account",
    "AccountType",
    "ActivityLog",
    "AttributeValue",
    "AuditAction",
    "Brand",
    "Category",
    "Customer",
    "CustomerContact",
    "CustomerInteraction",
    "CustomerSegment",
    "DebtDirection",
    "DebtPartyType",
    "DebtRecord",
    "Department",
    "Employee",
    "EmployeeStatus",
    "FinanceCategory",
    "FinancePayment",
    "Gender",
    "InteractionType",
    "Inventory",
    "InventoryItem",
    "InventoryStatus",
    "Invoice",
    "InvoiceStatus",
    "MovementType",
    "Notification",
    "NotificationSeverity",
    "NotificationType",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Payment",
    "PaymentDirection",
    "PaymentMethod",
    "Permission",
    "Position",
    "PriceType",
    "Product",
    "ProductVariant",
    "PurchaseItem",
    "PurchaseOrder",
    "PurchaseOrderStatus",
    "Return",
    "ReturnItem",
    "ReturnStatus",
    "Role",
    "RoleName",
    "Stock",
    "StockMovement",
    "Supplier",
    "SupplierPayment",
    "User",
    "Warehouse",
    "WarehouseType",
    "role_permissions",
    "user_roles",
]
