from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field

from app.models.order import OrderStatus, PaymentMethod


class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int | None = None
    name: str
    price: Decimal
    quantity: int

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity


class OrderListItem(BaseModel):
    id: int
    created_at: datetime
    total: Decimal
    restaurant_id: int
    restaurant_name: str
    status: OrderStatus


class OrderList(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    limit: int


class OrderDetail(BaseModel):
    id: int
    status: OrderStatus
    pickup_time: datetime
    comment: str | None = None
    payment_method: PaymentMethod
    subtotal: Decimal
    discount_percent: int
    total: Decimal
    promo_code: str | None = None
    restaurant_id: int
    restaurant_name: str
    pickup_address: str
    created_at: datetime
    items: list[OrderItemOut]


class OrderCreate(BaseModel):
    pickup_time: datetime
    comment: str | None = None
    payment_method: PaymentMethod
    promo_code: str | None = None


class OrderOwnerListItem(BaseModel):
    id: int
    created_at: datetime
    pickup_time: datetime
    status: OrderStatus
    total: Decimal
    customer_name: str
    is_premium: bool


class OrderOwnerList(BaseModel):
    items: list[OrderOwnerListItem]
    total: int
    page: int
    limit: int


class OrderOwnerDetail(BaseModel):
    id: int
    status: OrderStatus
    pickup_time: datetime
    comment: str | None = None
    payment_method: PaymentMethod
    subtotal: Decimal
    discount_percent: int
    total: Decimal
    created_at: datetime
    customer_name: str
    customer_phone: str
    is_premium: bool
    items: list[OrderItemOut]
