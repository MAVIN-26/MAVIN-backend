from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.allergen import Allergen
from app.models.menu_item import MenuItem
from app.repositories.allergen import AllergenRepository
from app.repositories.menu_category import MenuCategoryRepository
from app.repositories.menu_item import MenuItemRepository
from app.repositories.restaurant import RestaurantRepository
from app.schemas.menu_item import MenuItemAvailability, MenuItemCreate, MenuItemUpdate

USER_CHOICE_TOP_N = 6
USER_CHOICE_PERIOD_DAYS = 30


class MenuItemService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = MenuItemRepository(db)
        self.restaurants = RestaurantRepository(db)
        self.allergens = AllergenRepository(db)
        self.menu_categories = MenuCategoryRepository(db)

    async def _validate_menu_category(
        self, menu_category_id: int, restaurant_id: int
    ) -> None:
        category = await self.menu_categories.get_by_id(menu_category_id)
        if category is None or category.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="menu_category_id must reference a category of this restaurant",
            )

    async def _load_allergens(self, ids: list[int]) -> list[Allergen]:
        if not ids:
            return []
        allergens = await self.allergens.list_by_ids(ids)
        if len(allergens) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid allergen_ids",
            )
        return list(allergens)

    def _parse_exclude_ids(self, raw: str | None) -> list[int]:
        if not raw:
            return []
        try:
            return [int(x) for x in raw.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="exclude_allergen_ids must be a comma-separated list of integers",
            )

    async def _get_owner_restaurant_id(self, user_id: int) -> int:
        restaurant = await self.restaurants.get_by_admin_id(user_id)
        if restaurant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return restaurant.id

    async def _get_owner_menu_item(self, item_id: int, user_id: int) -> MenuItem:
        item = await self.repo.get_with_allergens(item_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found",
            )
        restaurant = await self.restaurants.get_by_id(item.restaurant_id)
        if restaurant is None or restaurant.restaurant_admin_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not your menu item",
            )
        return item

    async def list_public(
        self,
        restaurant_id: int,
        max_calories: int | None,
        max_price: float | None,
        max_proteins: float | None,
        max_fats: float | None,
        max_carbs: float | None,
        exclude_allergen_ids_raw: str | None,
    ) -> Sequence[MenuItem]:
        restaurant = await self.restaurants.get_by_id(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        exclude_ids = self._parse_exclude_ids(exclude_allergen_ids_raw)
        return await self.repo.list_public_filtered(
            restaurant_id,
            max_calories,
            max_price,
            max_proteins,
            max_fats,
            max_carbs,
            exclude_ids,
        )

    async def list_user_choice(self, restaurant_id: int) -> Sequence[MenuItem]:
        restaurant = await self.restaurants.get_by_id(restaurant_id)
        if restaurant is None or not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found",
            )
        return await self.repo.list_user_choice(
            restaurant_id,
            top_n=USER_CHOICE_TOP_N,
            period_days=USER_CHOICE_PERIOD_DAYS,
        )

    async def list_owner(self, user_id: int) -> Sequence[MenuItem]:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        return await self.repo.list_by_restaurant(restaurant_id)

    async def create_owner(self, user_id: int, body: MenuItemCreate) -> MenuItem:
        restaurant_id = await self._get_owner_restaurant_id(user_id)
        await self._validate_menu_category(body.menu_category_id, restaurant_id)
        allergens = await self._load_allergens(body.allergen_ids)

        data = body.model_dump(exclude={"allergen_ids"})
        item = MenuItem(restaurant_id=restaurant_id, allergens=allergens, **data)
        self.repo.add(item)
        await self.repo.commit()

        created = await self.repo.get_with_allergens(item.id)
        assert created is not None
        return created

    async def update_owner(self, item_id: int, user_id: int, body: MenuItemUpdate) -> MenuItem:
        item = await self._get_owner_menu_item(item_id, user_id)
        data = body.model_dump(exclude_unset=True)
        allergen_ids = data.pop("allergen_ids", None)

        if "menu_category_id" in data:
            if data["menu_category_id"] is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="menu_category_id is required",
                )
            await self._validate_menu_category(data["menu_category_id"], item.restaurant_id)

        for field, value in data.items():
            setattr(item, field, value)
        if allergen_ids is not None:
            item.allergens = await self._load_allergens(allergen_ids)

        await self.repo.commit()

        updated = await self.repo.get_with_allergens(item.id)
        assert updated is not None
        return updated

    async def set_availability(
        self, item_id: int, user_id: int, body: MenuItemAvailability
    ) -> MenuItem:
        item = await self._get_owner_menu_item(item_id, user_id)
        item.is_available = body.is_available
        await self.repo.commit()
        await self.repo.refresh(item)
        return item

    async def delete_owner(self, item_id: int, user_id: int) -> None:
        item = await self._get_owner_menu_item(item_id, user_id)
        await self.repo.delete(item)
        await self.repo.commit()


def get_menu_item_service(db: AsyncSession = Depends(get_db)) -> MenuItemService:
    return MenuItemService(db)
