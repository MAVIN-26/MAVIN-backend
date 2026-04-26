from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.restaurant import RestaurantPublic
from app.services.favorite import FavoriteService, get_favorite_service

router = APIRouter(
    prefix="/favorites",
    tags=["favorites"],
    dependencies=[Depends(require_role("customer"))],
)


@router.get("", response_model=list[RestaurantPublic])
async def list_favorites(
    current_user: User = Depends(get_current_user),
    service: FavoriteService = Depends(get_favorite_service),
):
    return await service.list_for_user(current_user.id)


@router.post("/{rest_id}")
async def add_favorite(
    rest_id: int,
    current_user: User = Depends(get_current_user),
    service: FavoriteService = Depends(get_favorite_service),
):
    await service.add(current_user.id, rest_id)
    return {"message": "OK"}


@router.delete("/{rest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    rest_id: int,
    current_user: User = Depends(get_current_user),
    service: FavoriteService = Depends(get_favorite_service),
):
    await service.remove(current_user.id, rest_id)
