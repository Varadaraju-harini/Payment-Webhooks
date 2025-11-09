# app/main.py
import os
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.responses import JSONResponse
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, update
from datetime import datetime
import redis
from rq import Queue
from .database import SessionLocal, engine, Base
from .models import Transaction, TransactionStatus
from .schemas import WebhookIn, TransactionOut
from .worker import process_transaction_job
from sqlalchemy import func
import os
from dotenv import load_dotenv

load_dotenv()

# create tables (simple approach)
Base.metadata.create_all(bind=engine)


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL)
q = Queue("transactions", connection=r, default_timeout=600)

app = FastAPI()

@app.get("/")
def health():
    return {"status": "HEALTHY", "current_time": datetime.utcnow().isoformat() + "Z"}

@app.post("/v1/webhooks/transactions", status_code=status.HTTP_202_ACCEPTED)
def receive_webhook(payload: WebhookIn, request: Request):
    """
    Immediate 202 Accepted response within 500ms.
    Idempotency: unique constraint on transaction_id and check status to avoid re-enqueue.
    """
    start = time.time()
    session = SessionLocal()
    try:
        # Try to insert a new transaction row with status PROCESSING
        new_tx = Transaction(
            transaction_id=payload.transaction_id,
            source_account=payload.source_account,
            destination_account=payload.destination_account,
            amount=payload.amount,
            currency=payload.currency,
            status=TransactionStatus.PROCESSING
        )
        session.add(new_tx)
        session.commit()
        session.refresh(new_tx)
        # Enqueue background processing
        job = q.enqueue(process_transaction_job, new_tx.transaction_id)
        # record enqueue time
        stmt = update(Transaction).where(Transaction.transaction_id == new_tx.transaction_id).values(last_enqueued_at=func.now())
        session.execute(stmt)
        session.commit()
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"ack": "accepted"})
    except IntegrityError:
        # transaction already exists (duplicate webhook). Handle idempotency:
        session.rollback()
        existing = session.execute(select(Transaction).where(Transaction.transaction_id == payload.transaction_id)).scalar_one_or_none()
        if existing is None:
            # strange — retry insertion once more or return accepted
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"ack": "accepted"})
        # If existing.status is PROCESSING -> do nothing (already in progress)
        # If existing.status is PROCESSED -> do nothing (already done)
        # If existing.status is FAILED -> optionally re-enqueue (we'll not re-enqueue automatically here)
        # We'll respond 202 in all cases (idempotent).
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"ack": "accepted", "note": "duplicate"})
    finally:
        # ensure we don't block >500ms for normal responses — but this code is small
        session.close()

@app.get("/v1/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str):
    session = SessionLocal()
    try:
        tx = session.execute(select(Transaction).where(Transaction.transaction_id == transaction_id)).scalar_one_or_none()
        if not tx:
            raise HTTPException(status_code=404, detail="transaction not found")
        return TransactionOut(
            transaction_id=tx.transaction_id,
            source_account=tx.source_account,
            destination_account=tx.destination_account,
            amount=tx.amount,
            currency=tx.currency,
            status=tx.status.value,
            created_at=tx.created_at,
            processed_at=tx.processed_at
        )
    finally:
        session.close()
