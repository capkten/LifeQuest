import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy import Uuid, Enum as SAEnum

from app.database import Base


class ItemType(str, Enum):
    CONSUMABLE = "consumable"
    GEAR = "gear"
    COLLECTIBLE = "collectible"
    QUEST = "quest"


class ItemStatus(str, Enum):
    ACTIVE = "active"
    EQUIPPED = "equipped"
    USED = "used"
    EXPIRED = "expired"


class UsageAction(str, Enum):
    ADD = "add"
    USE = "use"
    EQUIP = "equip"
    UNEQUIP = "unequip"
    DISCARD = "discard"


class BackpackItem(Base):
    __tablename__ = "backpack_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    shop_item_id = Column(Uuid, ForeignKey("shop_items.id"), nullable=False)
    item_type = Column(SAEnum(ItemType, native_enum=False), default=ItemType.CONSUMABLE)
    status = Column(SAEnum(ItemStatus, native_enum=False), default=ItemStatus.ACTIVE)
    quantity = Column(Integer, default=1)
    obtained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class UsageHistory(Base):
    __tablename__ = "usage_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    # item_id is intentionally NOT a ForeignKey -- the backpack item may be
    # deleted when its quantity reaches zero, but the usage history must survive.
    item_id = Column(Uuid, nullable=False)
    shop_item_id = Column(Uuid, ForeignKey("shop_items.id"), nullable=False)
    action = Column(SAEnum(UsageAction, native_enum=False), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
