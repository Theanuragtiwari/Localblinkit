from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class CartItemInput(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100)


class CreateOrderRequest(BaseModel):
    shop_id: int
    address: str = Field(min_length=5, max_length=500)
    lat: float
    lng: float
    items: list[CartItemInput]
    payment_method: str = 'COD'


class LocationUpdateRequest(BaseModel):
    order_id: int
    lat: float
    lng: float


class ProductCreateRequest(BaseModel):
    name: str
    category: str = 'General'
    price: float
    stock: int = 0
    image: str = ''


class ApiEnvelope(BaseModel):
    success: bool
    message: str
    error_code: str | None = None
    data: Any = None
