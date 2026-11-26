# Sahayak AI - Production Deployment Guide

## 1. Prerequisites
- Docker & Docker Compose v2
- TLS-terminating load balancer or reverse proxy (e.g., Nginx + Certbot / cloud LB) in front of port `80`
- Valid OpenAI API key (and/or configured Bhashini credentials)

## 2. Required Production Environment Variables
Copy `.env.example` to `.env` and set **non-default** production values:
- `ENVIRONMENT=production`
- `JWT_SECRET_KEY`: Random 32+ character secret (`openssl rand -hex 32`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Strong database credentials
- `OPENAI_API_KEY`: Required when `ENVIRONMENT=production`
- `VOICE_STT_PROVIDER=openai` (or `bhashini`) — `mock` is blocked at startup in production
- `VOICE_TTS_PROVIDER=openai` (or `bhashini`) — `mock` is blocked at startup in production
- `CORS_ORIGINS`: Exact production origin(s), e.g. `["https://sahayak.example.org"]`
- `SESSION_RETENTION_DAYS=7`

## 3. Build & Start Production Stack
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 4. Database Initialization & Seeding
Run Alembic migrations, create the initial admin user, and seed verified schemes:
```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python -m scripts.create_first_admin
docker compose -f docker-compose.prod.yml exec api python -m scripts.seed_real_schemes
```

## 5. Anonymous Session Retention Cron
Schedule daily cleanup of expired `conversation_sessions` rows:
```bash
docker compose -f docker-compose.prod.yml exec -T api python -m scripts.purge_expired_sessions
```
