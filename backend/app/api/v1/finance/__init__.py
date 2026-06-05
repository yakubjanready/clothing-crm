from fastapi import APIRouter

from app.api.v1.finance.accounts import router as accounts_router
from app.api.v1.finance.debts import router as debts_router
from app.api.v1.finance.payments import router as payments_router

finance_router = APIRouter(tags=["finance"])
finance_router.include_router(accounts_router)
finance_router.include_router(payments_router)
finance_router.include_router(debts_router)
