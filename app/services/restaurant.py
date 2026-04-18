from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.category import Category
from app.models.restaurant import Restaurant
from app.models.user import UserRole
from app.repositories.base import PaginatedResult
from app.repositories.category import CategoryRepository
from app.repositories.restaurant import RestaurantRepository
from app.repositories.user import UserRepository
from app.schemas.restaurant import RestaurantAdminCreate, RestaurantAdminUpdate, RestaurantOwnerUpdate


class RestaurantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = RestaurantRepository(db)
        self.users = UserRepository(db)
        self.categories = CategoryRepository(db)

    async def _load_categories(self, ids: list[int]) -> list[Category]:
        if not ids:
            return []
        categories = await self.categories.list_by_ids(ids)
        if len(categories) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_ids",
            )
        return list(categories)

    async def _validate_restaurant_admin(self, user_id: int) -> None:
        owner = await self.users.get_by_id(user_id)
        if owner is None or owner.role != UserRole.restaurant_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="restaurant_admin_id must reference a user with role restaurant_admin",
            )

    async def list_public(
        self,
        category_id: int | None,
        search: str | None,
        page: int,
        limit: int,
        sort: str | None = None,
    ) -> PaginatedResult[Restaurant]:
        return await self.repo.list_active_paginated(
            category_id, search, page, limit, sort
        )

    async def get_public(self, restaurant_id: int) -> Restaurant:
        restaurant = await self.repo.get_active_with_categories(restaurant_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return restaurant

    async def get_owner(self, user_id: int) -> Restaurant:
        restaurant = await self.repo.get_by_admin_id(user_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return restaurant

    async def update_owner(self, user_id: int, body: RestaurantOwnerUpdate) -> Restaurant:
        restaurant = await self.get_owner(user_id)
        data = body.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(restaurant, field, value)
        await self.repo.commit()
        return await self.get_owner(user_id)

    async def list_admin(self, page: int, limit: int) -> PaginatedResult[Restaurant]:
        return await self.repo.list_all_paginated(page, limit)

    async def create_admin(self, body: RestaurantAdminCreate) -> Restaurant:
        await self._validate_restaurant_admin(body.restaurant_admin_id)
        if await self.repo.exists_for_admin(body.restaurant_admin_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This restaurant admin already owns a restaurant",
            )
        categories = await self._load_categories(body.category_ids)

        restaurant = Restaurant(
            name=body.name,
            pickup_address=body.pickup_address,
            restaurant_admin_id=body.restaurant_admin_id,
            categories=categories,
            preparation_time_min=body.preparation_time_min,
            preparation_time_max=body.preparation_time_max,
        )
        self.repo.add(restaurant)
        await self.repo.commit()

        created = await self.repo.get_with_categories(restaurant.id)
        assert created is not None
        return created

    async def update_admin(self, restaurant_id: int, body: RestaurantAdminUpdate) -> Restaurant:
        restaurant = await self.repo.get_with_categories(restaurant_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )

        data = body.model_dump(exclude_unset=True)
        category_ids = data.pop("category_ids", None)
        new_admin_id = data.pop("restaurant_admin_id", None)

        if new_admin_id is not None and new_admin_id != restaurant.restaurant_admin_id:
            await self._validate_restaurant_admin(new_admin_id)
            if await self.repo.exists_for_admin(new_admin_id, exclude_id=restaurant_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This restaurant admin already owns a restaurant",
                )
            restaurant.restaurant_admin_id = new_admin_id

        for field, value in data.items():
            setattr(restaurant, field, value)

        if category_ids is not None:
            restaurant.categories = await self._load_categories(category_ids)

        await self.repo.commit()

        updated = await self.repo.get_with_categories(restaurant_id)
        assert updated is not None
        return updated

    async def delete_admin(self, restaurant_id: int) -> None:
        restaurant = await self.repo.get_by_id(restaurant_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        await self.repo.delete(restaurant)
        await self.repo.commit()


def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)
