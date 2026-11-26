# Sahayak AI

A multilingual, voice-first AI assistant to help underserved citizens in India discover and navigate Government of India welfare schemes using a verified CMS knowledge base, `pgvector` semantic retrieval, and a deterministic eligibility engine.

## Implementation Status
- [x] **Phase 1 — Infrastructure & Backend Foundation**: Dockerized PostgreSQL 16 + `pgvector`, FastAPI, SQLAlchemy 2.x, Alembic migrations, JWT Admin Auth
- [x] **Phase 2 — Admin Dashboard & Scheme CMS**: Authenticated Next.js Admin CMS (`/admin`), scheme CRUD, rules, benefits, sources, audit logs
- [x] **Phase 3 — AI Core, RAG & Deterministic Eligibility**: `pgvector` embeddings (`scheme_embeddings`), AST `rule_logic` engine, grounded orchestrator
- [x] **Phase 4 — Citizen PWA & Voice Pipeline**: Mobile-first Citizen Voice UI (`/`), BFF voice routes (`/api/voice/*`, `/api/assistant/query`), STT/TTS abstraction
- [x] **Phase 5 — Real Scheme Knowledge Base & Verified Ingestion**: Human-in-the-loop URL/PDF ingestion (`/admin/ingestion`), SSRF protection, prompt-injection safeguards, source freshness & scheme versioning
- [x] **Phase 6 — Security Hardening & Production Prep**: Production provider/JWT guardrails, security headers, PII scrubbing, session retention purge, Nginx + `docker-compose.prod.yml`, GitHub Actions CI
- [x] **Phase 7 — Gemini Integration, BFF Routing & Live Verification**: Google Gemini LLM, 1536-dim Embeddings, and STT/TTS voice providers (`GEMINI_API_KEY`), Next.js BFF routes for browser/Docker parity, full-stack container verification

## Prerequisites
- Docker and Docker Compose v2
- Python 3.10+ & Node.js 18+ (for local development outside Docker)

## Environment Setup
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with secure values (especially `JWT_SECRET_KEY`, `GEMINI_API_KEY`, and `VOICE_STT_PROVIDER=gemini` / `VOICE_TTS_PROVIDER=gemini` for production).

## Running with Docker (Development)
Start PostgreSQL, FastAPI API (`http://localhost:8000`), and Next.js Frontend (`http://localhost:3000`):
```bash
docker-compose up -d --build
```

Initialize schema, create the first admin user, and seed verified schemes:
```bash
docker-compose exec api alembic upgrade head
docker-compose exec api python -m scripts.create_first_admin
docker-compose exec api python -m scripts.seed_real_schemes
```

## Running Tests & Builds
Backend suite (via Docker):
```bash
docker-compose exec -T api pytest -v
```

Frontend production build:
```bash
cd frontend && npm run build
```

## API Documentation
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Architecture & Documentation
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Architecture Diagrams (System, Voice/RAG Sequence, Eligibility, Ingestion, ER Schema)](docs/ARCHITECTURE_DIAGRAMS.md)
- [AI Architecture](docs/AI_ARCHITECTURE.md)
- [Voice Architecture](docs/VOICE_ARCHITECTURE.md)
- [Database Design](docs/DATABASE_DESIGN.md)
- [Security](docs/SECURITY.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)
