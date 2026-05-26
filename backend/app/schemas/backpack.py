from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.backpack import ItemType, ItemStatus, UsageAction


class BackpackItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    shop_item_id: UUID
    item_type: ItemType
    status: ItemStatus
    quantity: int
    is_equipped: bool = False
    obtained_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def derive_is_equipped(cls, data):
        """Derive is_equipped from status if not explicitly provided."""
        if isinstance(data, dict):
            if "is_equipped" not in data and "status" in data:
                data["is_equipped"] = data["status"] == ItemStatus.EQUIPPED
        else:
            # ORM object -- status is always present
            if not hasattr(data, "is_equipped"):
                data.is_equipped = data.status == ItemStatus.EQUIPPED
        return data


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
