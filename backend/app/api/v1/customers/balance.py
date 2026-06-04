from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.customer import Customer
from app.models.customer_contact import CustomerContact
from app.models.customer_interaction import CustomerInteraction
from app.models.user import User
from app.schemas.customer_balance import CustomerBalanceResponse

router = APIRouter(prefix="/customers/{customer_id}/balance")


@router.get("", response_model=CustomerBalanceResponse)
async def get_balance(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
) -> CustomerBalanceResponse:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")

    contacts_total = (
        await db.execute(
            select(func.count(CustomerContact.id)).where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    primary = (
        await db.execute(
            select(CustomerContact.full_name).where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.deleted_at.is_(None),
                CustomerContact.is_primary.is_(True),
            )
        )
    ).scalar_one_or_none()

    interactions_total = (
        await db.execute(
            select(func.count(CustomerInteraction.id)).where(
                CustomerInteraction.customer_id == customer_id
            )
        )
    ).scalar_one()

    last = (
        await db.execute(
            select(CustomerInteraction)
            .where(CustomerInteraction.customer_id == customer_id)
            .order_by(CustomerInteraction.occurred_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return CustomerBalanceResponse(
        customer_id=c.id,
        name=c.name,
        credit_limit=c.credit_limit,
        current_debt=c.current_debt,
        available_credit=c.available_credit,
        is_blocked=c.is_blocked,
        contacts_total=contacts_total,
        primary_contact_name=primary,
        interactions_total=interactions_total,
        last_interaction_at=last.occurred_at if last else None,
        last_interaction_type=last.type if last else None,
    )
