# payment-webhooks

FastAPI service that accepts payment webhooks and processes them reliably in background.

Features
- POST /v1/webhooks/transactions - immediate acknowledgment (202), enqueues background processing
- GET / - health check
- GET /v1/transactions/{transaction_id} - check transaction status
- Idempotent: duplicate webhook deliveries do not cause duplicate processing
- Background worker simulates a 30s external call and writes final status to PostgreSQL
- Docker Compose for easy local testing (Postgres + Redis + Web + Worker)

## Design choices
- FastAPI: quick, async-capable HTTP API.
- PostgreSQL: durable persistence with unique constraint for idempotency.
- Redis + RQ: simple, reliable job queue for background processing.
- Docker Compose: reproducible local environment.
- Idempotency handled by DB unique constraint + checking existing row status before enqueuing.

## Run locally (Docker)
1. Clone repo and `cd payment-webhooks`
2. `docker compose up --build`
   - web service available at http://localhost:8000

## Test flow (single transaction)
1. Send webhook:
    curl -X POST http://localhost:8000/v1/webhooks/transactions

    -H "Content-Type: application/json"
    -d '{"transaction_id":"txn_abc123def456","source_account":"acc_user_789","destination_account":"acc_merchant_456","amount":1500,"currency":"INR"}' -v
Expect HTTP 202 immediately.

2. Check status immediately (likely PROCESSING):
    curl http://localhost:8000/v1/transactions/txn_abc123def456


3. Wait ~30 seconds and check again — status should be `PROCESSED` and `processed_at` set.

## Test duplicate prevention
Sending the same POST multiple times rapidly — you should receive 202 each time but only one processing job and only one final processed row (no duplicate processing).

## Deployment
- For cloud deployment use Railway, Render, Fly, or Heroku.
- Ensure DATABASE_URL and REDIS_URL environment variables point to managed Postgres and Redis.
- Run an RQ worker process (recommended managed container or separate process) for background processing.

