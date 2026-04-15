from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartOut
from app.services.cart import CartService, get_cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
async def get_cart(
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    return await service.get(current_user.id)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    body: CartItemCreate,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    return await service.add_item(current_user.id, body)


@router.put("/items/{item_id}", response_model=CartOut)
async def update_cart_item(
    item_id: int,
    body: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    return await service.update_item(current_user.id, item_id, body)


@router.delete("/items/{item_id}", response_model=CartOut)
async def delete_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    return await service.delete_item(current_user.id, item_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    service: CartService = Depends(get_cart_service),
):
    await service.clear(current_user.id)
