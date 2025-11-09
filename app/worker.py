# app/worker.py
import os
import time
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from .database import SessionLocal, engine
from .models import Transaction, TransactionStatus
from datetime import datetime

def process_transaction_job(transaction_id: str):
    """
    This function runs inside an RQ worker.
    Simulates external API calls by sleeping 30 seconds, then marks transaction as PROCESSED.
    """
    session = SessionLocal()
    try:
        tx = session.execute(select(Transaction).where(Transaction.transaction_id == transaction_id)).scalar_one_or_none()
        if tx is None:
            # nothing to do
            return {"error": "not found"}
        # If already processed, skip
        if tx.status == TransactionStatus.PROCESSED:
            return {"status": "already processed"}

        # simulate external calls
        time.sleep(30)

        # Here you'd call payment gateway, update balances, etc.
        # For demo: mark processed
        stmt = update(Transaction).where(Transaction.transaction_id == transaction_id).values(
            status=TransactionStatus.PROCESSED,
            processed_at=datetime.utcnow()
        )
        session.execute(stmt)
        session.commit()
        return {"status": "processed"}
    except Exception as e:
        session.rollback()
        # mark as FAILED maybe
        try:
            stmt = update(Transaction).where(Transaction.transaction_id == transaction_id).values(
                status=TransactionStatus.FAILED
            )
            session.execute(stmt)
            session.commit()
        except Exception:
            session.rollback()
        raise
    finally:
        session.close()
