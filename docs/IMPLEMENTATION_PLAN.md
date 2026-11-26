# Sahayak AI - Implementation Plan

## Phase 1: Infrastructure & Backend Foundation
*   [x] Setup Docker Compose (PostgreSQL 16 + `pgvector`, FastAPI API, Next.js frontend).
*   [x] Configure SQLAlchemy 2.x, Alembic migrations, health checks, and structured logging.
*   [x] Implement JWT authentication and bcrypt password hashing for Admin access.

## Phase 2: Admin Dashboard API & Frontend
*   [x] Build CRUD REST APIs for Schemes, Rules, Benefits, Documents, Steps, Sources, and Categories.
*   [x] Implement Audit Logging (`audit_logs`) on administrative mutations.
*   [x] Initialize Next.js App Router frontend with cookie-authenticated `/admin` dashboard and scheme editor.

## Phase 3: AI Core, RAG & Deterministic Eligibility Engine
*   [x] Implement the Python Deterministic Eligibility Engine (`evaluate_eligibility` with `AND`/`OR` AST logic).
*   [x] Integrate `pgvector` (`scheme_embeddings`) for semantic search over `PUBLISHED` schemes.
*   [x] Build `AssistantOrchestrator` (Session Profile -> Intent/Entity Extraction -> Retrieval -> Deterministic Eligibility -> Grounded Response).

## Phase 4: Citizen PWA & Voice Pipeline
*   [x] Implement abstract `STTProvider` and `TTSProvider` interfaces and factory configuration.
*   [x] Build mobile-first Citizen PWA (`/`) with `MediaRecorder` voice loop and audio playback.
*   [x] Add end-to-end voice pipeline tests.

## Phase 5: Real Scheme Knowledge Base & Verified Ingestion
*   [x] Seed verified Government of India welfare schemes (`seed_real_schemes.py`).
*   [x] Build SSRF-protected URL/PDF ingestion pipeline (`fetcher.py`, `extractor.py`, `normalizer.py`, `IngestionRecord`).
*   [x] Build `/admin/ingestion` review UI and `/admin/schemes/[id]` source freshness re-check & versioning workflows.
*   [x] Complete Scenarios A–J integration tests (`test_phase5_scenarios.py`).

## Phase 6: Security Hardening & Production Preparation
*   [x] Enforce production startup and factory guardrails (`ENVIRONMENT=production` blocks `mock` providers and weak JWT secrets).
*   [x] Add HTTP security headers middleware, PII minimization scrubbing, and `purge_expired_sessions.py`.
*   [x] Implement `OpenAISTTProvider` / `OpenAITTSProvider`, Nginx reverse proxy, `docker-compose.prod.yml`, `DEPLOYMENT.md`, and GitHub Actions CI.

## Phase 7: Bhashini Provider, BFF Routing & Live Stack Verification
*   [x] Implement `BhashiniSTTProvider` and `BhashiniTTSProvider` ULCA inference client.
*   [x] Route browser voice/assistant requests through Next.js BFF API routes (`/api/voice/*`, `/api/assistant/query`) for seamless Docker & local networking.
*   [x] Verify full Docker Compose stack (PostgreSQL + `pgvector`, FastAPI, Next.js frontend) end-to-end.
