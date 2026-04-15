from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.promo_code import PromoCode
from app.repositories.base import PaginatedResult
from app.repositories.exceptions import AlreadyExistsError
from app.repositories.promo_code import PromoCodeRepository
from app.schemas.promo import PromoCreate, PromoUpdate


class PromoService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PromoCodeRepository(db)

    async def list_active(self, page: int, limit: int) -> PaginatedResult[PromoCode]:
        now = datetime.now(timezone.utc)
        return await self.repo.list_active_paginated(now, page, limit)

    async def validate(self, user_id: int, code: str) -> PromoCode:
        now = datetime.now(timezone.utc)
        promo = await self.repo.find_by_code(code)
        if promo is None or not promo.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        if promo.expires_at is not None and promo.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        if await self.repo.is_used_by(user_id, promo.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        return promo

    async def list_admin(self, page: int, limit: int) -> PaginatedResult[PromoCode]:
        return await self.repo.list_all_paginated(page, limit)

    async def create_admin(self, body: PromoCreate) -> PromoCode:
        try:
            return await self.repo.create(body.code, body.discount_percent, body.expires_at)
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Promo code already exists",
            )

    async def update_admin(self, promo_id: int, body: PromoUpdate) -> PromoCode:
        promo = await self.repo.get_by_id(promo_id)
        if promo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        data = body.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(promo, field, value)
        await self.repo.commit()
        await self.repo.refresh(promo)
        return promo

    async def delete_admin(self, promo_id: int) -> None:
        promo = await self.repo.get_by_id(promo_id)
        if promo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        await self.repo.delete(promo)
        await self.repo.commit()


def get_promo_service(db: AsyncSession = Depends(get_db)) -> PromoService:
    return PromoService(db)
