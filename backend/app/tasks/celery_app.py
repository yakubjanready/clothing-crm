from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "clothing_crm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
)


@celery_app.task(name="ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="notify_low_stock")
def notify_low_stock(
    stock_id: str,
    warehouse_id: str,
    variant_id: str,
    available: int,
    min_quantity: int,
) -> str:
    """Stock minimal chegaradan past tushganda bildirishnoma yuboradi.
    Hozir log+placeholder; keyin Slack/Email/Push integratsiyasi qo'shiladi.
    """
    msg = (
        f"[LOW STOCK] stock={stock_id} wh={warehouse_id} variant={variant_id} "
        f"available={available} min={min_quantity}"
    )
    print(msg)
    return msg
