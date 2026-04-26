from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.menu_category import MenuCategory
from app.repositories.exceptions import AlreadyExistsError
from app.repositories.menu_category import MenuCategoryRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.menu_category import MenuCategoryCreate, MenuCategoryUpdate


class MenuCategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = MenuCategoryRepository(db)
        self.restaurants = RestaurantRepository(db)

    async def _get_owner_restaurant_id(self, user_id: int) -> int:
        restaurant = await self.restaurants.get_by_admin_id(user_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return restaurant.id

    async def _get_owned_category(self, category_id: int, user_id: int) -> MenuCategory:
        category = await self.repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu category not found",
            )
        restaurant = await self.restaurants.get_by_id(category.restaurant_id)
        if restaurant is None or restaurant.restaurant_admin_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your menu category",
            )
        return category

    async def list_public(self, restaurant_id: int) -> Sequence[MenuCategory]:
        restaurant = await self.restaurants.get_by_id(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return await self.repo.list_by_restaurant(restaurant_id)

    async def list_owner(self, user_id: int) -> Sequence[MenuCategory]:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        return await self.repo.list_by_restaurant(restaurant_id)

    async def create_owner(
        self, user_id: int, body: MenuCategoryCreate
    ) -> MenuCategory:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        try:
            return await self.repo.create(
                restaurant_id=restaurant_id,
                name=body.name,
                sort_order=body.sort_order,
            )
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Menu category with this name already exists",
            )

    async def update_owner(
        self, category_id: int, user_id: int, body: MenuCategoryUpdate
    ) -> MenuCategory:
        category = await self._get_owned_category(category_id, user_id)
        try:
            return await self.repo.update(
                category, name=body.name, sort_order=body.sort_order
            )
        except AlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Menu category with this name already exists",
            )

    async def delete_owner(self, category_id: int, user_id: int) -> None:
        """Delete category. FK on menu_items.menu_category_id is RESTRICT,
        so deleting a category that still has menu items raises IntegrityError."""
        category = await self._get_owned_category(category_id, user_id)
        await self.repo.delete(category)
        try:
            await self.repo.commit()
        except IntegrityError:
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category has menu items; reassign or delete them first",
            )


def get_menu_category_service(
    db: AsyncSession = Depends(get_db),
) -> MenuCategoryService:
    return MenuCategoryService(db)
