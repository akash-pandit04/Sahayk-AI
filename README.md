# Sahayak AI

A multilingual, voice-first AI assistant to help underserved citizens in India discover and navigate Government of India welfare schemes.

## Phase 1 Implementation Status
- [x] Dockerized PostgreSQL with `pgvector`
- [x] FastAPI Backend Base
- [x] SQLAlchemy 2.x & Alembic setup
- [x] Admin Authentication (JWT, bcrypt)
- [x] Health check endpoints
- [x] Backend tests

## Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development outside docker)

## Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with secure values (especially `JWT_SECRET_KEY` and passwords) for production.

## Running with Docker
Start the infrastructure:
```bash
docker-compose up -d
```
This will start PostgreSQL and the FastAPI application on `http://localhost:8000`.

## Database Migrations
To initialize or upgrade the database schema:
```bash
docker-compose exec api alembic upgrade head
```

## Admin Creation
To create the first admin user, configure `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD` in your `.env` file, then run:
```bash
docker-compose exec api python -m scripts.create_first_admin
```

## API Documentation
Once running, visit:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Running Tests
To run the automated test suite locally:
```bash
docker-compose exec api pytest
```
