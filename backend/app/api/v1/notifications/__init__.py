from fastapi import APIRouter

from app.api.v1.notifications.rest import router as rest_router
from app.api.v1.notifications.websocket import router as ws_router

notifications_router = APIRouter(tags=["notifications"])
notifications_router.include_router(rest_router)
notifications_router.include_router(ws_router)
