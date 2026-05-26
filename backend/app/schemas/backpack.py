from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.backpack import ItemType, ItemStatus, UsageAction


class BackpackItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    shop_item_id: UUID
    item_type: ItemType
    status: ItemStatus
    quantity: int
    is_equipped: bool
    obtained_at: datetime
    updated_at: datetime


class UsageHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    item_id: UUID
    shop_item_id: UUID
    action: UsageAction
    quantity: int
    created_at: datetime
    item_name: Optional[str] = None
