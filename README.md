# LocalQuick

Production-foundation quick-commerce starter for local shops.

## Stack (current)
- FastAPI + SQLAlchemy + Pydantic
- PostgreSQL/SQLite (env configurable)
- JWT auth with role-based guards
- WebSocket rider location updates
- Docker Compose (API + Postgres + Redis + Web)

## Local setup (single process)

1. Create `.env` from `.env.example` and set secrets.
2. Start services:

```bash
docker compose up --build
```

3. Open:
- Web: http://127.0.0.1:5500
- API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

4. Seed demo data:

```bash
curl -X POST http://127.0.0.1:8000/seed
```

Demo users:
- `customer@localquick.test` / `customer123`
- `shop@localquick.test` / `shop123`
- `rider@localquick.test` / `rider123`
- `admin@localquick.test` / `admin123`

## Environment variables
See `.env.example`.

## API style
All API responses use:

```json
{
  "success": true,
  "message": "...",
  "error_code": null,
  "data": {}
}
```

Routes are available on both:
- Backward compatibility: `/...`
- Versioned: `/api/v1/...`

## Notes
- `payments/mock-success` exists for local testing only.
- Razorpay and Google Maps keys must be provided by environment variables.
- Never commit secrets.
