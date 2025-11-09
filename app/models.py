# app/models.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, Enum, UniqueConstraint
from sqlalchemy.sql import expression
from sqlalchemy import Boolean
from sqlalchemy.types import TIMESTAMP
from .database import Base
import enum

class TransactionStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(128), nullable=False, unique=True, index=True)
    source_account = Column(String(128), nullable=False)
    destination_account = Column(String(128), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(12), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PROCESSING)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_enqueued_at = Column(TIMESTAMP(timezone=True), nullable=True)
