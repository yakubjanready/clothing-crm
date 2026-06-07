from fastapi import APIRouter

from app.api.v1.users.roles import router as roles_router
from app.api.v1.users.users import router as users_router

users_module_router = APIRouter()
users_module_router.include_router(users_router)
users_module_router.include_router(roles_router)
