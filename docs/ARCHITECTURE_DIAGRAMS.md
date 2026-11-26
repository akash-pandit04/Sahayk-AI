# Sahayak AI - Architecture Diagrams

This document contains the visual architecture, sequence, pipeline, workflow, and database schema diagrams for **Sahayak AI**, reflecting the implemented codebase.

---

## 1. High-Level System & Docker Deployment Architecture

Defined in `docker-compose.yml`, `backend/app/main.py`, and `backend/app/api/v1/api.py`:

```mermaid
flowchart LR
    Citizen["Citizen Browser / PWA"] -->|"Voice & Text"| Frontend["Next.js Frontend Container (Port 3000)"]
    Admin["Admin Browser"] -->|"JWT Auth / CMS"| Frontend

    Frontend -->|"POST /api/v1/voice/*"| Backend["FastAPI Backend Container (Port 8000)"]
    Frontend -->|"POST /api/v1/assistant/query"| Backend
    Frontend -->|"/api/admin_proxy -> /api/v1/admin/*"| Backend

    Backend -->|"SQLAlchemy 2.x"| DB["PostgreSQL 16 + pgvector (Port 5433 -> 5432)"]
    Backend -->|"LLM & 1536-dim Embeddings"| AIProvider["Google Gemini API (or Mock in Dev)"]
    Backend -->|"STT & TTS"| VoiceProvider["Gemini Multimodal Voice / TTS (or Mock in Dev)"]
    Backend -->|"SSRF-Protected Fetch"| GovtSites["Official Govt Portals & PDFs"]
```

---

## 2. End-to-End Voice, RAG & Eligibility Sequence

Implemented across `frontend/src/hooks/useVoicePipeline.ts`, `backend/app/api/v1/endpoints/voice.py`, `backend/app/api/v1/endpoints/assistant.py`, and `backend/app/services/ai/orchestrator.py`:

```mermaid
sequenceDiagram
    actor Citizen
    participant UI as "Citizen PWA (useVoicePipeline)"
    participant VoiceAPI as "FastAPI /api/v1/voice"
    participant AsstAPI as "FastAPI /api/v1/assistant/query"
    participant Orch as "AssistantOrchestrator"
    participant Ret as "RetrievalService (pgvector)"
    participant Engine as "Eligibility Engine"
    participant LLM as "LLMProvider"

    Citizen->>UI: Presses mic and speaks
    UI->>VoiceAPI: POST /transcribe (audio, language)
    VoiceAPI-->>UI: Transcribed text

    UI->>AsstAPI: POST /query (message, conversation_id, language)
    AsstAPI->>Orch: process_query()
    Orch->>Orch: get_or_create_session()
    Orch->>LLM: extract_intent_and_profile(message, profile_data)
    LLM-->>Orch: intent + profile_updates + missing_fields
    Orch->>Orch: update_session_profile()

    Orch->>Ret: search_schemes(message)
    Ret-->>Orch: Top PUBLISHED schemes (cosine_distance)

    loop For each candidate scheme
        Orch->>Engine: evaluate_eligibility(profile_data, rules, rule_logic)
        Engine-->>Orch: POTENTIALLY_ELIGIBLE / NOT_ELIGIBLE / INSUFFICIENT_INFORMATION
    end

    Orch->>LLM: generate_response(message, grounded context + VERIFIED sources)
    LLM-->>Orch: Natural-language response
    Orch-->>AsstAPI: response_text + scheme_results + sources
    AsstAPI-->>UI: AssistantQueryResponse

    UI->>VoiceAPI: POST /synthesize (response_text, language)
    VoiceAPI-->>UI: audio/wav stream
    UI-->>Citizen: Plays spoken answer
```

---

## 3. Deterministic Eligibility & Source-of-Truth Pipeline

Implemented in `backend/app/services/eligibility/engine.py` and `backend/app/services/ai/retrieval.py`:

```mermaid
flowchart TD
    CMS["Verified CMS Scheme Data (status = PUBLISHED)"] --> Embed["SchemeEmbedding (pgvector 1536-dim + content_hash)"]
    Embed --> Search["RetrievalService.search_schemes()"]
    Profile["ConversationSession.profile_data (JSON)"] --> Eval["evaluate_eligibility()"]
    Search --> Eval
    Rules["Scheme.rule_logic AST (AND/OR tree) & EligibilityRule rows"] --> Eval

    Eval -->|"All required rules match"| Pot["POTENTIALLY_ELIGIBLE"]
    Eval -->|"Any mandatory/AND rule fails"| Not["NOT_ELIGIBLE"]
    Eval -->|"Required profile fields absent"| Insuff["INSUFFICIENT_INFORMATION (missing_information)"]

    Pot --> Ctx["Serialized Grounded Context + VERIFIED SchemeSource"]
    Not --> Ctx
    Insuff --> Ctx
    Ctx --> Resp["LLMProvider.generate_response()"]
```

---

## 4. Human-in-the-Loop Scheme Ingestion Workflow

Implemented in `backend/app/api/v1/endpoints/admin/ingestion.py`, `backend/app/services/ingestion/fetcher.py`, `backend/app/services/ingestion/extractor.py`, and `backend/app/services/ingestion/normalizer.py`:

```mermaid
flowchart LR
    Input["Admin submits URL or PDF"] --> Guard["is_safe_url() SSRF Check (blocks private/loopback IPs)"]
    Guard --> Fetch["fetch_url() / Upload PDF (10MB max)"]
    Fetch --> Extract["extract_html() / extract_pdf() + SHA-256 hash"]
    Extract --> RecExt["IngestionRecord (status = EXTRACTED)"]
    RecExt --> Norm["normalize_scheme_text() (LLM JSON + ambiguity_flags)"]
    Norm --> RecNorm["IngestionRecord (status = NORMALIZED)"]
    RecNorm --> Review["Admin Review & Approve"]
    Review --> Draft["Scheme (status = DRAFT) + IngestionRecord (REVIEWED)"]
    Draft --> Publish["Admin Verification & Publish -> sync_scheme_embedding()"]
```

---

## 5. Core Database Schema (ER Diagram)

Defined in `backend/app/models/scheme_data/models.py`, `backend/app/models/ingestion.py`, and `backend/app/models/admin.py`:

```mermaid
erDiagram
    admins ||--o{ schemes : "creates/updates"
    admins ||--o{ audit_logs : "performs"
    admins ||--o{ ingestion_records : "reviews"
    admins ||--o{ scheme_sources : "verifies"

    schemes ||--o{ scheme_benefits : "has"
    schemes ||--o{ eligibility_rules : "has"
    schemes ||--o{ required_documents : "requires"
    schemes ||--o{ application_steps : "defines"
    schemes ||--o{ scheme_sources : "cited_by"
    schemes ||--o| scheme_embeddings : "embedded_in"
    schemes ||--o{ schemes : "parent_scheme_id"
    schemes ||--o{ ingestion_records : "originates_from"

    schemes }o--o{ scheme_categories : "scheme_category_map"
    schemes }o--o{ languages : "scheme_language_map"
    schemes }o--o{ states : "scheme_state_map"

    schemes {
        string id PK
        string name
        enum status "DRAFT|SOURCE_VERIFIED|PUBLISHED|ARCHIVED"
        int version
        json rule_logic
    }
    scheme_embeddings {
        string id PK
        string scheme_id FK
        string model_name
        string content_hash
        vector embedding
    }
    ingestion_records {
        string id PK
        string source_url
        enum source_type
        enum status "PENDING|EXTRACTED|NORMALIZED|REVIEWED|REJECTED"
        json normalized_data
        json ambiguity_flags
    }
    conversation_sessions {
        string id PK
        string session_id
        json profile_data
    }
```
