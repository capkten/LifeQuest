from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.backpack import ItemStatus
from app.schemas.backpack import BackpackItemResponse, UsageHistoryResponse
from app.services.backpack import BackpackService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/backpack", tags=["backpack"])


@router.get("/items", response_model=List[BackpackItemResponse])
def get_items(
    status: Optional[ItemStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BackpackService(db)
    return service.get_user_items(current_user.id, status=status)


@router.post("/items/{item_id}/use", response_model=BackpackItemResponse)
def use_item(
    item_id: UUID,
    quantity: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BackpackService(db)
    item = service.get_item_for_user(item_id, current_user.id)
    return service.use_item(item, quantity)


@router.post("/items/{item_id}/equip", response_model=BackpackItemResponse)
def equip_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BackpackService(db)
    item = service.get_item_for_user(item_id, current_user.id)
    return service.equip_item(item)


@router.post("/items/{item_id}/discard", response_model=BackpackItemResponse)
def discard_item(
    item_id: UUID,
    quantity: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BackpackService(db)
    item = service.get_item_for_user(item_id, current_user.id)
    return service.discard_item(item, quantity)


@router.get("/history", response_model=List[UsageHistoryResponse])
def get_usage_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BackpackService(db)
    history = service.get_usage_history(current_user.id)
    # Enrich with item names from shop items
    result = []
    for entry in history:
        shop_item = service.shop_item_repo.get_by_id(entry.shop_item_id)
        item_name = shop_item.name if shop_item else None
        response = UsageHistoryResponse(
            id=entry.id,
            user_id=entry.user_id,
            item_id=entry.item_id,
            shop_item_id=entry.shop_item_id,
            action=entry.action,
            quantity=entry.quantity,
            created_at=entry.created_at,
            item_name=item_name,
        )
        result.append(response)
    return result
