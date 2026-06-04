from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CoinTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    amount: int
    type: str
    source: str
    source_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime


class CoinHistoryResponse(BaseModel):
    transactions: List[CoinTransactionResponse]
    total_earned: int
    total_spent: int
    count: int
