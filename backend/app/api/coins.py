from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.coin import CoinHistoryResponse
from app.services.coin import CoinService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/coins", tags=["coins"])


@router.get("/history", response_model=CoinHistoryResponse)
def get_history(
    coin_type: Optional[str] = Query(None, description="Filter by type: earn or spend"),
    source: Optional[str] = Query(None, description="Filter by source: task, habit, goal, checkin, shop, achievement"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CoinService(db)
    return service.get_history(
        current_user.id,
        skip=skip,
        limit=limit,
        coin_type=coin_type,
        source=source,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/totals")
def get_totals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CoinService(db)
    return service.get_totals(current_user.id)
