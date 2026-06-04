from fastapi import APIRouter

from app.api.v1.warehouse.inventory import router as inventory_router
from app.api.v1.warehouse.movements import router as movements_router
from app.api.v1.warehouse.stock import router as stock_router
from app.api.v1.warehouse.warehouses import router as warehouses_router

warehouse_router = APIRouter(tags=["warehouse"])
warehouse_router.include_router(warehouses_router)
# Diqqat: movements_router avval, chunki /stock/movements va /stock/{id}
# bir prefiksdan farq qiladi va FastAPI birinchi mosini tanlaydi.
warehouse_router.include_router(movements_router)
warehouse_router.include_router(stock_router)
warehouse_router.include_router(inventory_router)
