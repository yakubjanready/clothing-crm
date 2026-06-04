from fastapi import APIRouter

from app.api.v1.sales.invoices import router as invoices_router
from app.api.v1.sales.orders import router as orders_router
from app.api.v1.sales.returns import router as returns_router

sales_router = APIRouter(tags=["sales"])
sales_router.include_router(orders_router)
sales_router.include_router(invoices_router)
sales_router.include_router(returns_router)
