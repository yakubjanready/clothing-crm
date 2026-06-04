from fastapi import APIRouter

from app.api.v1.customers.balance import router as balance_router
from app.api.v1.customers.contacts import router as contacts_router
from app.api.v1.customers.customers import router as customers_router
from app.api.v1.customers.interactions import router as interactions_router

# Nested sub-routerlar avval, parent CRUD ("/{id}") oxirgi —
# /customers/{id}/balance va /customers/{id}/balance kabi yo'llarni qoplanmasligi uchun.
customers_module_router = APIRouter(tags=["customers"])
customers_module_router.include_router(balance_router)
customers_module_router.include_router(contacts_router)
customers_module_router.include_router(interactions_router)
customers_module_router.include_router(customers_router)
