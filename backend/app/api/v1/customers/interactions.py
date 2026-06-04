from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.customer import Customer
from app.models.customer_interaction import CustomerInteraction, InteractionType
from app.models.user import User
from app.schemas.customer_interaction import (
    CustomerInteractionCreate,
    CustomerInteractionRead,
)
from app.services.audit import log_activity
from app.utils.pagination import Page, PageParams, page_params, paginate

router = APIRouter(prefix="/customers/{customer_id}/interactions")
ENTITY = "customer_interaction"


async def _get_customer(db: AsyncSession, customer_id: uuid.UUID) -> Customer:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")
    return c


@router.get("", response_model=Page[CustomerInteractionRead])
async def list_interactions(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
    params: PageParams = Depends(page_params),
    type_: InteractionType | None = Query(default=None, alias="type"),
    actor_id: uuid.UUID | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
) -> Page[CustomerInteractionRead]:
    await _get_customer(db, customer_id)

    stmt = (
        select(CustomerInteraction)
        .where(CustomerInteraction.customer_id == customer_id)
        .order_by(CustomerInteraction.occurred_at.desc())
    )
    if type_ is not None:
        stmt = stmt.where(CustomerInteraction.type == type_)
    if actor_id is not None:
        stmt = stmt.where(CustomerInteraction.actor_id == actor_id)
    if since is not None:
        stmt = stmt.where(CustomerInteraction.occurred_at >= since)
    if until is not None:
        stmt = stmt.where(CustomerInteraction.occurred_at <= until)

    items, total, pages = await paginate(db, stmt, params)
    return Page[CustomerInteractionRead](
        items=[CustomerInteractionRead.model_validate(i) for i in items],
        total=total, page=params.page, page_size=params.page_size, pages=pages,
    )


@router.post(
    "",
    response_model=CustomerInteractionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_interaction(
    customer_id: uuid.UUID,
    body: CustomerInteractionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> CustomerInteractionRead:
    await _get_customer(db, customer_id)

    interaction = CustomerInteraction(
        customer_id=customer_id,
        actor_id=actor.id,
        type=body.type,
        subject=body.subject,
        notes=body.notes,
        occurred_at=body.occurred_at or datetime.now(timezone.utc),
        follow_up_at=body.follow_up_at,
    )
    db.add(interaction)
    await db.flush()

    await log_activity(
        db, actor=actor, action=AuditAction.CREATE,
        entity_type=ENTITY, entity_id=interaction.id,
        changes={
            "customer_id": str(customer_id),
            "type": body.type, "subject": body.subject,
        },
        request=request,
    )
    await db.commit()
    await db.refresh(interaction)
    return CustomerInteractionRead.model_validate(interaction)
