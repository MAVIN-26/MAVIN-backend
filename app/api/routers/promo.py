from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.promo_code import PromoCode, used_promo_codes
from app.models.user import User
from app.schemas.promo import (
    PromoAdminList,
    PromoAdminOut,
    PromoCreate,
    PromoList,
    PromoOut,
    PromoUpdate,
    PromoValidateRequest,
)

customer_router = APIRouter(
    prefix="/promo",
    tags=["promo"],
    dependencies=[Depends(require_role("customer"))],
)
admin_router = APIRouter(
    prefix="/admin/promo",
    tags=["admin-promo"],
    dependencies=[Depends(require_role("site_admin"))],
)


@customer_router.get("", response_model=PromoList)
async def list_active_promos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    base = select(PromoCode).where(
        PromoCode.is_active.is_(True),
        or_(PromoCode.expires_at.is_(None), PromoCode.expires_at > now),
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(
        base.order_by(PromoCode.id).offset((page - 1) * limit).limit(limit)
    )
    items = result.scalars().all()
    return PromoList(items=items, total=total or 0, page=page, limit=limit)


@customer_router.post("/validate", response_model=PromoOut)
async def validate_promo(
    body: PromoValidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    promo = await db.scalar(select(PromoCode).where(PromoCode.code == body.code))
    if promo is None or not promo.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    if promo.expires_at is not None and promo.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    already = await db.scalar(
        select(used_promo_codes).where(
            used_promo_codes.c.user_id == current_user.id,
            used_promo_codes.c.promo_code_id == promo.id,
        )
    )
    if already is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    return promo


@admin_router.get("", response_model=PromoAdminList)
async def admin_list_promos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(PromoCode.id)))
    result = await db.execute(
        select(PromoCode).order_by(PromoCode.id).offset((page - 1) * limit).limit(limit)
    )
    items = result.scalars().all()
    return PromoAdminList(items=items, total=total or 0, page=page, limit=limit)


@admin_router.post("", response_model=PromoAdminOut, status_code=status.HTTP_201_CREATED)
async def admin_create_promo(body: PromoCreate, db: AsyncSession = Depends(get_db)):
    promo = PromoCode(
        code=body.code,
        discount_percent=body.discount_percent,
        expires_at=body.expires_at,
    )
    db.add(promo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Promo code already exists")
    await db.refresh(promo)
    return promo


@admin_router.put("/{promo_id}", response_model=PromoAdminOut)
async def admin_update_promo(
    promo_id: int, body: PromoUpdate, db: AsyncSession = Depends(get_db)
):
    promo = await db.get(PromoCode, promo_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(promo, field, value)
    await db.commit()
    await db.refresh(promo)
    return promo


@admin_router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_promo(promo_id: int, db: AsyncSession = Depends(get_db)):
    promo = await db.get(PromoCode, promo_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    await db.delete(promo)
    await db.commit()
