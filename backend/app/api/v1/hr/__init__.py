from fastapi import APIRouter

from app.api.v1.hr.audit import router as audit_router
from app.api.v1.hr.departments import router as departments_router
from app.api.v1.hr.employees import router as employees_router
from app.api.v1.hr.positions import router as positions_router

hr_router = APIRouter(prefix="/hr", tags=["hr"])
hr_router.include_router(departments_router)
hr_router.include_router(positions_router)
hr_router.include_router(employees_router)
hr_router.include_router(audit_router)
