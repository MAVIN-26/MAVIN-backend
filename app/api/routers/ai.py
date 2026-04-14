from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ai_request_log import AIRequestLog
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.ai import AIRecommendationOut, AIRecommendRequest
from app.services.ai_recommender import (
    AIServiceUnavailable,
    MenuItemContext,
    recommend,
)

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    dependencies=[Depends(require_role("customer"))],
)


@router.post("/recommend", response_model=AIRecommendationOut)
async def ai_recommend(
    body: AIRecommendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium subscription required")

    restaurant = await db.get(Restaurant, body.restaurant_id)
    if restaurant is None or not restaurant.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

    menu_result = await db.execute(
        select(MenuItem)
        .options(selectinload(MenuItem.allergens))
        .where(MenuItem.restaurant_id == body.restaurant_id, MenuItem.is_available.is_(True))
    )
    menu_items = menu_result.scalars().all()

    user_loaded = await db.execute(
        select(User).options(selectinload(User.allergens)).where(User.id == current_user.id)
    )
    user_with_allergens = user_loaded.scalar_one()
    user_allergens = [a.name for a in user_with_allergens.allergens]

    menu_ctx = [
        MenuItemContext(
            id=m.id,
            name=m.name,
            description=m.description,
            price=float(m.price),
            calories=m.calories,
            proteins=m.proteins,
            fats=m.fats,
            carbs=m.carbs,
            allergens=[a.name for a in m.allergens],
        )
        for m in menu_items
    ]
    available_ids = {m.id for m in menu_items}

    try:
        result = await recommend(body.prompt, menu_ctx, user_allergens)
    except AIServiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ИИ-сервис временно недоступен, попробуйте позже",
        )

    filtered_ids = [i for i in result.recommended_dish_ids if i in available_ids]

    log = AIRequestLog(
        user_id=current_user.id,
        restaurant_id=body.restaurant_id,
        prompt=body.prompt,
        response=result.ai_text,
        recommended_dish_ids=filtered_ids,
    )
    db.add(log)
    await db.commit()

    return AIRecommendationOut(ai_text=result.ai_text, recommended_dish_ids=filtered_ids)
