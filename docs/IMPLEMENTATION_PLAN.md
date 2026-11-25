# Sahayak AI - Implementation Plan

## Phase 0: Discovery & Architecture (CURRENT)
*   [x] Analyze requirements and constraints.
*   [x] Establish architecture guidelines.
*   [x] Design database schema.
*   [x] Draft documentation.

## Phase 1: Infrastructure & Backend Foundation
*   Initialize Git repository.
*   Setup Docker Compose (PostgreSQL + pgvector).
*   Initialize Python FastAPI project (Poetry/Pipenv).
*   Configure SQLAlchemy, Alembic, and create initial DB migrations based on `DATABASE_DESIGN.md`.
*   Implement JWT Authentication logic for Admin.

## Phase 2: Admin Dashboard API & Frontend
*   **Backend:** Build CRUD REST APIs for Schemes, Rules, Sources, and Categories.
*   **Backend:** Implement Audit Logging middleware.
*   **Frontend:** Initialize Next.js project.
*   **Frontend:** Build Admin Login and Dashboard UI.
*   **Frontend:** Build Scheme Management interfaces (Forms for creating schemes, adding eligibility rules).

## Phase 3: AI Core & Eligibility Engine
*   Implement the Python Deterministic Eligibility Engine.
*   Integrate `pgvector` for semantic search on schemes.
*   Build the LangChain / LLM pipeline (Intent Extraction -> DB Search -> Eligibility Eval -> Response Generation).
*   Write unit tests for the deterministic engine to ensure 0% hallucination on rules.

## Phase 4: Voice Pipeline Integration
*   Implement the abstract `VoiceService`.
*   Integrate STT (Speech-to-Text) provider.
*   Integrate TTS (Text-to-Speech) provider.
*   Test multilingual audio in -> text -> processing -> text -> audio out loop.

## Phase 5: Citizen Frontend (Voice UI)
*   Build the mobile-first Next.js Citizen UI.
*   Implement MediaRecorder for microphone access.
*   Implement audio streaming playback.
*   Connect the UI to the backend conversational API.

## Phase 6: E2E Testing, Data Seeding & Hardening
*   Seed the database with 3-5 REAL government schemes (e.g., Ayushman Bharat, PM Kisan) using verified government URLs.
*   Perform E2E tests simulating conversational flows.

## Phase 7: Deployment Preparation
*   Finalize environment variable configurations.
*   Write deployment instructions (Docker, Nginx config).
