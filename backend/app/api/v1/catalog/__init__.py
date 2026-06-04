from fastapi import APIRouter

from app.api.v1.catalog.brands import router as brands_router
from app.api.v1.catalog.categories import router as categories_router
from app.api.v1.catalog.products import router as products_router
from app.api.v1.catalog.upload import router as upload_router
from app.api.v1.catalog.variants import router as variants_router

catalog_router = APIRouter(tags=["catalog"])
catalog_router.include_router(categories_router)
catalog_router.include_router(brands_router)
catalog_router.include_router(products_router)
catalog_router.include_router(variants_router)
catalog_router.include_router(upload_router)
