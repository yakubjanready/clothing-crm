from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.activity_log import AuditAction
from app.models.customer import Customer
from app.models.customer_contact import CustomerContact
from app.models.user import User
from app.schemas.customer_contact import (
    CustomerContactCreate,
    CustomerContactRead,
)
from app.services.audit import log_activity

router = APIRouter(prefix="/customers/{customer_id}/contacts")
ENTITY = "customer_contact"


async def _get_customer(db: AsyncSession, customer_id: uuid.UUID) -> Customer:
    c = await db.get(Customer, customer_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mijoz topilmadi")
    return c


@router.get("", response_model=list[CustomerContactRead])
async def list_contacts(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("customer:read")),
) -> list[CustomerContactRead]:
    await _get_customer(db, customer_id)
    rows = (
        (
            await db.execute(
                select(CustomerContact)
                .where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.deleted_at.is_(None),
                )
                .order_by(CustomerContact.is_primary.desc(), CustomerContact.full_name)
            )
        )
        .scalars()
        .all()
    )
    return [CustomerContactRead.model_validate(r) for r in rows]


@router.post("", response_model=CustomerContactRead, status_code=status.HTTP_201_CREATED)
async def add_contact(
    customer_id: uuid.UUID,
    body: CustomerContactCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> CustomerContactRead:
    await _get_customer(db, customer_id)

    # is_primary belgilansa, boshqalarni False qilamiz
    if body.is_primary:
        await db.execute(
            update(CustomerContact)
            .where(CustomerContact.customer_id == customer_id)
            .values(is_primary=False)
        )

    contact = CustomerContact(customer_id=customer_id, **body.model_dump())
    db.add(contact)
    await db.flush()

    await log_activity(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type=ENTITY,
        entity_id=contact.id,
        changes={**body.model_dump(), "customer_id": str(customer_id)},
        request=request,
    )
    await db.commit()
    await db.refresh(contact)
    return CustomerContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_contact(
    customer_id: uuid.UUID,
    contact_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission("customer:write")),
) -> None:
    contact = await db.get(CustomerContact, contact_id)
    if contact is None or contact.deleted_at is not None or contact.customer_id != customer_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kontakt topilmadi")
    contact.soft_delete()
    await log_activity(
        db,
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        entity_type=ENTITY,
        entity_id=contact.id,
        request=request,
    )
    await db.commit()
