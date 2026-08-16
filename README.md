
# LocalQuick V3 — Complete Local Quick-Commerce Starter

A complete, runnable local-commerce platform foundation for a specific locality.

## Stack
- FastAPI + SQLAlchemy
- SQLite by default for zero-setup local development
- PostgreSQL-ready through DATABASE_URL
- JWT authentication
- Role-based Customer / Shop / Delivery / Admin
- Responsive mobile-first web frontend
- Cart + checkout
- COD + mock online payment
- Shop order workflow
- Delivery assignment
- Rider GPS endpoint
- WebSocket live order updates
- Admin dashboard
- Delivery-radius enforcement
- Docker Compose
- Razorpay/Google Maps configuration hooks

## 1. Run locally

### Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
In another terminal:
```bash
cd frontend
python -m http.server 5500
```

Open:
http://127.0.0.1:5500

API:
http://127.0.0.1:8000

Swagger:
http://127.0.0.1:8000/docs

## 2. Seed the demo data

Open Swagger and execute:
POST /seed

Demo accounts:
- Customer: customer@localquick.test / customer123
- Shop: shop@localquick.test / shop123
- Delivery: rider@localquick.test / rider123
- Admin: admin@localquick.test / admin123

## 3. Docker + PostgreSQL

```bash
docker compose up --build
```

API:
http://127.0.0.1:8000

PostgreSQL is exposed on localhost:5432.

## 4. Product flow

Customer:
Login → location → shop → products → cart → checkout → order tracking.

Shop:
Login → dashboard → accept → pack → ready for rider.

Delivery:
Login → available orders → accept → share GPS → delivered.

Admin:
Login → metrics → orders → assign rider.

## 5. Production integrations

The code is deliberately safe to run without secret keys. Add:
- RAZORPAY_KEY_ID
- RAZORPAY_KEY_SECRET
- GOOGLE_MAPS_API_KEY

Before production:
- Replace mock payment with Razorpay server-side order creation + signature verification.
- Restrict Google Maps API key by application/domain.
- Use PostgreSQL.
- Set a long random JWT_SECRET.
- Put API behind HTTPS.
- Configure CORS to the production frontend origin.
- Add Redis for scale-out WebSocket broadcasting.
- Add object storage for product images.
- Add SMS/WhatsApp/email provider for notifications.

## Important
This is a complete runnable application starter, but no assistant can safely invent your real Razorpay account credentials, Google API key, domain, payment webhooks, or production cloud account. Those are configured through `.env`.
