# Sahayak AI - Architecture

## 1. System Overview
Sahayak AI is a modern, decoupled web application featuring a React-based frontend for both the Voice UI (Citizen) and Dashboard (Admin), powered by a Python REST API and PostgreSQL database.

## 2. Technology Stack
*   **Frontend (Citizen & Admin):** Next.js (App Router), React, TypeScript, TailwindCSS.
*   **Backend:** Python 3.11+, FastAPI (for high-performance async API).
*   **Database:** PostgreSQL with `pgvector` extension for storing scheme embeddings.
*   **ORM:** SQLAlchemy 2.0 + Alembic (for migrations).
*   **AI/LLM:** Integration via LangChain or native API clients (Gemini/OpenAI/Claude).
*   **Voice (STT/TTS):** Bhashini/Whisper/Google Cloud via API abstraction.
*   **Infrastructure:** Docker & Docker Compose for reproducible environments.

## 3. High-Level Component Diagram

```text
[ Citizen Voice UI ] <--> (Audio/Text) <--> [ Next.js BFF / API ]
                                                  |
[ Admin Dashboard ]  <--> (JSON/REST)  <--> [ FastAPI Backend ]
                                                  |
                                                  +--> [ PostgreSQL (Relational Data) ]
                                                  +--> [ pgvector (Embeddings) ]
                                                  +--> [ External AI APIs (LLM) ]
                                                  +--> [ External Voice APIs (STT/TTS) ]
```

## 4. Backend Module Structure
*   `/backend/app/api`: FastAPI routers (endpoints for admin, chat, schemes).
*   `/backend/app/core`: Configuration, security, JWT middleware.
*   `/backend/app/models`: SQLAlchemy ORM definitions.
*   `/backend/app/schemas`: Pydantic models for request/response validation.
*   `/backend/app/services`: Business logic (RAG pipeline, eligibility engine, voice orchestration).
*   `/backend/app/db`: Database connection and session management.

## 5. Frontend Structure
*   `/frontend/app/(citizen)`: Main voice-first UI (mobile-optimized).
*   `/frontend/app/(admin)`: Protected admin dashboard.
*   `/frontend/components`: Reusable UI components.
*   `/frontend/lib`: API clients, state management, audio processing utilities.

## 6. Deployment Architecture
*   Local/Dev: `docker-compose up` spins up PostgreSQL, FastAPI backend, and Next.js frontend.
*   Production: Containerized deployments, protected by Nginx/Traefik reverse proxy and HTTPS.

## 7. Detailed Architecture Diagrams
See [ARCHITECTURE_DIAGRAMS.md](./ARCHITECTURE_DIAGRAMS.md) for detailed Mermaid diagrams covering the deployment topology, voice + RAG sequence flow, deterministic eligibility pipeline, ingestion workflow, and database ER schema.
