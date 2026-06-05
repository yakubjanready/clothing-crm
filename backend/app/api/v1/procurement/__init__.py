from fastapi import APIRouter

from app.api.v1.procurement.purchase_orders import router as po_router
from app.api.v1.procurement.suppliers import router as suppliers_router

procurement_router = APIRouter(tags=["procurement"])
procurement_router.include_router(suppliers_router)
procurement_router.include_router(po_router)
