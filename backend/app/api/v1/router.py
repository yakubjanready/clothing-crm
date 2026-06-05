from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import catalog_router
from app.api.v1.customers import customers_module_router
from app.api.v1.hr import hr_router
from app.api.v1.procurement import procurement_router
from app.api.v1.sales import sales_router
from app.api.v1.warehouse import warehouse_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(hr_router)
api_router.include_router(catalog_router)
api_router.include_router(warehouse_router)
api_router.include_router(customers_module_router)
api_router.include_router(sales_router)
api_router.include_router(procurement_router)


@api_router.get("/ping", tags=["meta"])
async def ping() -> dict[str, str]:
    return {"pong": "ok"}
