from app.schemas.activity_log import ActivityLogFilter, ActivityLogRead
from app.schemas.attribute_value import (
    AttributeValueCreate,
    AttributeValueRead,
    AttributeValueUpdate,
)
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RoleRead,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.department import (
    DepartmentCreate,
    DepartmentFilter,
    DepartmentRead,
    DepartmentUpdate,
)
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeFilter,
    EmployeeRead,
    EmployeeUpdate,
)
from app.schemas.position import (
    PositionCreate,
    PositionFilter,
    PositionRead,
    PositionUpdate,
)
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.schemas.product_variant import (
    VariantColorSpec,
    VariantCreate,
    VariantMatrixRequest,
    VariantMatrixResponse,
    VariantRead,
    VariantUpdate,
)
from app.schemas.inventory import (
    InventoryCreate,
    InventoryFinalizeResponse,
    InventoryItemCount,
    InventoryItemRead,
    InventoryRead,
)
from app.schemas.stock import (
    MovementIssue,
    MovementReceive,
    MovementRelease,
    MovementReserve,
    MovementTransfer,
    StockMinUpdate,
    StockMovementRead,
    StockRead,
)
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.customer_balance import CustomerBalanceResponse
from app.schemas.customer_contact import CustomerContactCreate, CustomerContactRead
from app.schemas.customer_interaction import (
    CustomerInteractionCreate,
    CustomerInteractionRead,
)
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate

__all__ = [
    "LoginRequest", "RefreshRequest", "TokenPair", "UserRead", "UserCreate", "RoleRead",
    "DepartmentCreate", "DepartmentUpdate", "DepartmentRead", "DepartmentFilter",
    "PositionCreate", "PositionUpdate", "PositionRead", "PositionFilter",
    "EmployeeCreate", "EmployeeUpdate", "EmployeeRead", "EmployeeFilter",
    "ActivityLogRead", "ActivityLogFilter",
    "CategoryCreate", "CategoryUpdate", "CategoryRead",
    "BrandCreate", "BrandUpdate", "BrandRead",
    "ProductCreate", "ProductUpdate", "ProductRead",
    "VariantCreate", "VariantUpdate", "VariantRead",
    "VariantColorSpec", "VariantMatrixRequest", "VariantMatrixResponse",
    "AttributeValueCreate", "AttributeValueUpdate", "AttributeValueRead",
    "WarehouseCreate", "WarehouseUpdate", "WarehouseRead",
    "StockRead", "StockMinUpdate", "StockMovementRead",
    "MovementReceive", "MovementIssue", "MovementTransfer",
    "MovementReserve", "MovementRelease",
    "InventoryCreate", "InventoryRead", "InventoryItemRead",
    "InventoryItemCount", "InventoryFinalizeResponse",
    "CustomerCreate", "CustomerUpdate", "CustomerRead",
    "CustomerContactCreate", "CustomerContactRead",
    "CustomerInteractionCreate", "CustomerInteractionRead",
    "CustomerBalanceResponse",
]
