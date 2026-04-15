from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.repositories.ai_request_log import AIRequestLogRepository
from app.repositories.menu_item import MenuItemRepository
from app.repositories.restaurant import RestaurantRepository
from app.repositories.user import UserRepository
from app.schemas.ai import AIRecommendationOut, AIRecommendRequest
from app.services.ai_recommender import (
    AIServiceUnavailable,
    MenuItemContext,
    recommend,
)


class AIRecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.logs = AIRequestLogRepository(db)
        self.menu_items = MenuItemRepository(db)
        self.restaurants = RestaurantRepository(db)
        self.users = UserRepository(db)

    async def recommend(self, user: User, body: AIRecommendRequest) -> AIRecommendationOut:
        if not user.is_premium:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium subscription required",
            )

        restaurant = await self.restaurants.get_by_id(body.restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )

        menu_items = await self.menu_items.list_public_filtered(
            body.restaurant_id, None, None, []
        )

        user_with_allergens = await self.users.get_with_allergens(user.id)
        assert user_with_allergens is not None
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

        self.logs.log(
            user_id=user.id,
            restaurant_id=body.restaurant_id,
            prompt=body.prompt,
            response=result.ai_text,
            recommended_dish_ids=filtered_ids,
        )
        await self.logs.commit()

        return AIRecommendationOut(ai_text=result.ai_text, recommended_dish_ids=filtered_ids)


def get_ai_recommendation_service(
    db: AsyncSession = Depends(get_db),
) -> AIRecommendationService:
    return AIRecommendationService(db)
