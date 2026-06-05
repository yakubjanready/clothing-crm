"""perf indexes — eng ko'p ishlatiladigan filtr ustunlari

Maqsad (B.M2/D.M4 optimizatsiya):
- orders.created_at — dashboard sanasi bo'yicha tartiblash
- (customer_id, created_at) — mijoz buyurtmalari tarixi
- (warehouse_id, status) — ombor xizmati holati bo'yicha guruhlash
- payments.created_at — moliya hisoboti
- notifications.created_at — ro'yxat tartibi
- activity_logs (created_at, entity_type) — audit search

Revision ID: d4e7a2c8f3b1
Revises: c1e9c4b3fdcb
Create Date: 2026-06-05 19:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e7a2c8f3b1"
down_revision: Union[str, None] = "c1e9c4b3fdcb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Indekslar ro'yxati: (jadval, nom, ustunlar)
_INDEXES = [
    # Sotuv — dashboard va mijoz tarixi uchun
    ("orders", "ix_orders_created_at", ["created_at"]),
    ("orders", "ix_orders_customer_created", ["customer_id", "created_at"]),
    ("orders", "ix_orders_warehouse_status", ["warehouse_id", "status"]),
    ("orders", "ix_orders_status_created", ["status", "created_at"]),
    # Moliya
    ("payments", "ix_payments_created_at", ["created_at"]),
    ("payments", "ix_payments_order_id", ["order_id"]),
    # Notifikatsiyalar — foydalanuvchining o'qilmagan ro'yxati
    ("notifications", "ix_notifications_user_read", ["user_id", "read_at"]),
    ("notifications", "ix_notifications_created_at", ["created_at"]),
    # Audit log — vaqt bo'yicha qidiruv
    ("activity_logs", "ix_activity_logs_created_at", ["created_at"]),
    ("activity_logs", "ix_activity_logs_entity", ["entity_type", "entity_id"]),
    # Mahsulot — qidiruv (gender + brand) ko'p ishlatiladi
    ("products", "ix_products_brand_gender", ["brand_id", "gender"]),
    # Stock — joriy holat (warehouse_id index allaqachon bor, qo'shimcha)
    ("stocks", "ix_stocks_quantity", ["quantity"]),
]


def upgrade() -> None:
    for table, name, cols in _INDEXES:
        op.create_index(name, table, cols, unique=False, if_not_exists=True)


def downgrade() -> None:
    for table, name, _ in _INDEXES:
        op.drop_index(name, table_name=table, if_exists=True)
