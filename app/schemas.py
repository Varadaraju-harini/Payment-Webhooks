# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

class WebhookIn(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str

class TransactionOut(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
    status: str
    created_at: Optional[datetime]
    processed_at: Optional[datetime]
