from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemOut, CartItemUpdate, CartOut

router = APIRouter(prefix="/cart", tags=["cart"])


async def _get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        cart.items = []
    return cart


async def _build_cart_out(db: AsyncSession, cart: Cart) -> CartOut:
    if not cart.items:
        return CartOut()

    menu_item_ids = [ci.menu_item_id for ci in cart.items]
    menu_result = await db.execute(select(MenuItem).where(MenuItem.id.in_(menu_item_ids)))
    menu_by_id = {mi.id: mi for mi in menu_result.scalars().all()}

    restaurant_name = None
    if cart.restaurant_id is not None:
        restaurant_name = await db.scalar(
            select(Restaurant.name).where(Restaurant.id == cart.restaurant_id)
        )

    items_out: list[CartItemOut] = []
    total = Decimal("0")
    for ci in cart.items:
        mi = menu_by_id.get(ci.menu_item_id)
        if mi is None:
            continue
        items_out.append(
            CartItemOut(
                id=ci.id,
                menu_item_id=mi.id,
                name=mi.name,
                photo_url=mi.photo_url,
                price=mi.price,
                quantity=ci.quantity,
            )
        )
        total += Decimal(mi.price) * ci.quantity

    return CartOut(
        restaurant_id=cart.restaurant_id,
        restaurant_name=restaurant_name,
        items=items_out,
        total=total,
    )


@router.get("", response_model=CartOut)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cart = await _get_or_create_cart(db, current_user.id)
    return await _build_cart_out(db, cart)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    body: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    menu_item = await db.get(MenuItem, body.menu_item_id)
    if menu_item is None or not menu_item.is_available:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not available")

    cart = await _get_or_create_cart(db, current_user.id)

    if cart.restaurant_id is not None and cart.restaurant_id != menu_item.restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item is from another restaurant. Clear the cart first.",
        )

    if cart.restaurant_id is None:
        cart.restaurant_id = menu_item.restaurant_id

    existing = next((ci for ci in cart.items if ci.menu_item_id == menu_item.id), None)
    if existing is not None:
        existing.quantity += body.quantity
    else:
        db.add(CartItem(cart_id=cart.id, menu_item_id=menu_item.id, quantity=body.quantity))

    await db.commit()

    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
    )
    cart = result.scalar_one()
    return await _build_cart_out(db, cart)


async def _get_user_cart_item(db: AsyncSession, item_id: int, user_id: int) -> tuple[CartItem, Cart]:
    result = await db.execute(
        select(CartItem, Cart)
        .join(Cart, Cart.id == CartItem.cart_id)
        .where(CartItem.id == item_id, Cart.user_id == user_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    return row[0], row[1]


@router.put("/items/{item_id}", response_model=CartOut)
async def update_cart_item(
    item_id: int,
    body: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item, cart = await _get_user_cart_item(db, item_id, current_user.id)
    if body.quantity == 0:
        await db.delete(item)
    else:
        item.quantity = body.quantity
    await db.commit()

    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
    )
    cart = result.scalar_one()
    if not cart.items:
        cart.restaurant_id = None
        await db.commit()
    return await _build_cart_out(db, cart)


@router.delete("/items/{item_id}", response_model=CartOut)
async def delete_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item, cart = await _get_user_cart_item(db, item_id, current_user.id)
    await db.delete(item)
    await db.commit()

    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id)
    )
    cart = result.scalar_one()
    if not cart.items:
        cart.restaurant_id = None
        await db.commit()
    return await _build_cart_out(db, cart)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == current_user.id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        return
    for ci in list(cart.items):
        await db.delete(ci)
    cart.restaurant_id = None
    await db.commit()
