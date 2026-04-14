import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 600


async def _expire_once(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Subscription).where(
            Subscription.is_active.is_(True),
            Subscription.expires_at <= now,
        )
    )
    expired = result.scalars().all()
    if not expired:
        return 0

    user_ids: set[int] = set()
    for sub in expired:
        sub.is_active = False
        user_ids.add(sub.user_id)

    await db.flush()

    for user_id in user_ids:
        still_active = await db.scalar(
            select(Subscription.id).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
            )
        )
        if still_active is None:
            await db.execute(
                update(User).where(User.id == user_id).values(is_premium=False)
            )

    await db.commit()
    return len(expired)


async def run_expiry_loop() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await _expire_once(db)
                if count:
                    logger.info("Expired %d subscription(s)", count)
        except Exception:
            logger.exception("Subscription expiry task failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
