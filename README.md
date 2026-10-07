# Reservation / Order Service

A production-oriented Django REST API for limited-stock e-commerce.
Users reserve products temporarily, then confirm to create an order.

**Stack:** Django 5.1 · DRF · PostgreSQL 17 · Redis · Celery · JWT · Docker

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build


API: http://localhost:8000

Create a user:

docker compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
U.objects.create_user(username='alice', password='alice1234')
"

Get a JWT:

curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice1234"}'

Run tests:

docker compose exec web pytest -v
How the System Works
Product ──▶ Reservation ──confirm──▶ Order
A reservation temporarily holds product stock.
Confirming creates an order.
Cancelling or expiring releases the stock.
Concurrency Handling

Preventing overselling is the main requirement.

If stock=1 and two users reserve at the same time, only one succeeds.

Mechanism: transaction.atomic() + select_for_update() locks the product row while checking/updating stock.

Tested in reservations/tests/test_concurrency.py with real threads.

Idempotency

Create reservation supports Idempotency-Key header.

Same key + same request → returns existing reservation. No duplicate, no double stock decrement.

Protects against network retries, timeouts, and lost responses.

Reservation Expiration

PENDING reservations expire after RESERVATION_TTL_MINUTES (default 10).

PENDING ──expire──▶ release stock ──▶ EXPIRED
Celery Beat triggers periodically.
Celery Worker executes the task.
confirm_reservation also re-checks expiration as a safety net.
Reservation States

Valid transitions:

        PENDING
           │
   ┌───────┼────────┐
   ▼       ▼        ▼
CONFIRMED CANCELLED EXPIRED

Invalid transitions (rejected with 409):

CONFIRMED → CANCELLED
EXPIRED → CONFIRMED
CANCELLED → CONFIRMED
Orders
Reservation = temporary hold on inventory.
Order = final confirmed transaction.
One-to-one relationship prevents multiple orders per reservation (DB-level guarantee).
Authentication

JWT via djangorestframework-simplejwt.

POST /api/auth/token/
Header: Authorization: Bearer <access-token>
API Endpoints
Method	Endpoint	Purpose
POST	/api/reservations/	Create reservation (with Idempotency-Key)
GET	/api/reservations/	List my reservations
GET	/api/reservations/{id}/	Get my reservation
POST	/api/reservations/{id}/confirm/	Confirm reservation → Order
POST	/api/reservations/{id}/cancel/	Cancel reservation → release stock
GET	/api/orders/	List my orders
GET	/api/products/	List products
Error Handling

Centralized exception handler. Consistent format:

{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Requested quantity is not available."
  }
}

Covers:

Authentication errors
Permission errors
Invalid state transitions
Insufficient stock
Expired reservations
Validation errors
Idempotency conflicts
Testing
docker compose exec web pytest -v

20 tests passing.

Category	Tests
Normal	Create, get, list, confirm, cancel
Idempotency	Same key → same reservation; no double decrement
Stock	Zero rejected, over-request rejected, exact allowed
Expiration	Release stock, skip non-expired, block confirm
State transitions	Invalid transitions rejected, no double orders
Concurrency	Multiple users, no overselling
Local Development Commands
docker compose up -d
docker compose up --build -d
docker compose down
docker compose ps
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
docker compose exec web pytest -v
Production Considerations
Set DEBUG=False
Use a strong secret key and keep it out of Git
Use secure PostgreSQL credentials
Enable HTTPS
Configure ALLOWED_HOSTS
Secure Redis
Configure database backups
Add monitoring and logging
Tune Celery workers
Add CI/CD pipeline
Known Limitations
No distributed tracing
No advanced metrics
No rate limiting
No dead-letter queue
No CI/CD pipeline
No connection pooling
No automated backup
Limited integration tests
Design Decisions

PostgreSQL — reliable transactions and row-level locking.

select_for_update() — locks the product row during stock updates so concurrent requests cannot both consume the same inventory.

Idempotency — prevents duplicate reservations caused by client retries.

Celery — handles reservation expiration outside the HTTP request/response cycle.

Project Status

Included:

Django REST API
JWT authentication
Product inventory
Temporary reservations
Confirmation and cancellation
Automatic expiration
Idempotency
Concurrency protection
Order creation
PostgreSQL
Redis
Celery
Docker Compose
Automated tests
License

Developed as a backend engineering take-home assignment.