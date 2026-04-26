from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.ai import AIRecommendationOut, AIRecommendRequest
from app.services.ai_recommendation import (
    AIRecommendationService,
    get_ai_recommendation_service,
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
    service: AIRecommendationService = Depends(get_ai_recommendation_service),
):
    return await service.recommend(current_user, body)
