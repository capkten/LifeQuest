from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.shop import (
    ShopItemCreate,
    ShopItemUpdate,
    ShopItemResponse,
    ExchangeHistoryCreate,
    ExchangeHistoryResponse,
)
from app.services.shop import ShopService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/shop", tags=["shop"])


# --- Shop item endpoints ---

@router.post("/items", response_model=ShopItemResponse)
def create_item(
    item_in: ShopItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.create_item(item_in, current_user.id)


@router.get("/items", response_model=List[ShopItemResponse])
def get_items(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.get_items(skip=skip, limit=limit)


@router.get("/items/{item_id}", response_model=ShopItemResponse)
def get_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.get_item(item_id)


@router.put("/items/{item_id}", response_model=ShopItemResponse)
def update_item(
    item_id: UUID,
    item_in: ShopItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    item = service.get_item_for_user(item_id, current_user.id)
    return service.update_item(item, item_in)


@router.delete("/items/{item_id}")
def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    service.get_item_for_user(item_id, current_user.id)
    service.delete_item(item_id)
    return {"message": "Item deleted"}


# --- Exchange (purchase) endpoints ---

@router.post("/exchange", response_model=ExchangeHistoryResponse)
def purchase_item(
    exchange_in: ExchangeHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.purchase_item(current_user.id, exchange_in)


@router.get("/exchange/history", response_model=List[ExchangeHistoryResponse])
def get_exchange_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.get_user_exchanges(current_user.id)


@router.get("/exchange/{exchange_id}", response_model=ExchangeHistoryResponse)
def get_exchange(
    exchange_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    return service.get_exchange_for_user(exchange_id, current_user.id)


@router.post("/exchange/{exchange_id}/refund", response_model=ExchangeHistoryResponse)
def refund_exchange(
    exchange_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ShopService(db)
    exchange = service.get_exchange_for_user(exchange_id, current_user.id)
    return service.refund_exchange(exchange)
