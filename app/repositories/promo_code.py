from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models.promo_code import PromoCode, used_promo_codes
from app.repositories.base import BaseRepository, PaginatedResult
from app.repositories.exceptions import AlreadyExistsError


class PromoCodeRepository(BaseRepository[PromoCode]):
    model = PromoCode

    async def list_active_paginated(
        self, now: datetime, page: int, limit: int
    ) -> PaginatedResult[PromoCode]:
        base = select(PromoCode).where(
            PromoCode.is_active.is_(True),
            or_(PromoCode.expires_at.is_(None), PromoCode.expires_at > now),
        )
        total = await self.db.scalar(select(func.count()).select_from(base.subquery()))
        result = await self.db.execute(
            base.order_by(PromoCode.id).offset((page - 1) * limit).limit(limit)
        )
        items = result.scalars().all()
        return PaginatedResult(items=items, total=total or 0, page=page, limit=limit)

    async def list_all_paginated(self, page: int, limit: int) -> PaginatedResult[PromoCode]:
        total = await self.db.scalar(select(func.count(PromoCode.id)))
        result = await self.db.execute(
            select(PromoCode).order_by(PromoCode.id).offset((page - 1) * limit).limit(limit)
        )
        items = result.scalars().all()
        return PaginatedResult(items=items, total=total or 0, page=page, limit=limit)

    async def find_by_code(self, code: str) -> PromoCode | None:
        return await self.db.scalar(select(PromoCode).where(PromoCode.code == code))

    async def is_used_by(self, user_id: int, promo_id: int) -> bool:
        result = await self.db.scalar(
            select(used_promo_codes).where(
                used_promo_codes.c.user_id == user_id,
                used_promo_codes.c.promo_code_id == promo_id,
            )
        )
        return result is not None

    async def create(
        self, code: str, discount_percent: int, expires_at: datetime | None
    ) -> PromoCode:
        promo = PromoCode(code=code, discount_percent=discount_percent, expires_at=expires_at)
        self.db.add(promo)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsError()
        await self.db.refresh(promo)
        return promo
