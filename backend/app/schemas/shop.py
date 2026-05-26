from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.shop import ExchangeStatus


class ShopItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    price: int = 0
    coin_price: int = 0
    stock: int = -1


class ShopItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    coin_price: Optional[int] = None
    stock: Optional[int] = None
    is_active: Optional[int] = None


class ShopItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    price: int
    coin_price: int
    stock: int
    is_active: int
    created_at: datetime
    updated_at: datetime


class ExchangeHistoryCreate(BaseModel):
    item_id: UUID
    quantity: int = 1


class ExchangeHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    item_id: UUID
    quantity: int
    total_cost: int
    status: ExchangeStatus
    created_at: datetime
