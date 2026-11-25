# Sahayak AI - Testing Strategy

Testing is critical given the strict requirements against hallucination and incorrect government information.

## 1. Backend Testing (Python / FastAPI)
*   **Framework:** `pytest`
*   **Unit Tests:**
    *   **Eligibility Engine (Critical):** Create massive deterministic test suites for the eligibility engine. Mock various `user_profiles` and ensure the engine accurately outputs `POTENTIALLY_ELIGIBLE`, `NOT_ELIGIBLE`, or `INSUFFICIENT_INFORMATION` according to the rules.
    *   **API Endpoints:** Test CRUD operations for the admin API.
    *   **Authentication:** Test JWT issuing, validation, and unauthorized access rejection.
*   **Integration Tests:**
    *   Test Database transactions and rollback capabilities using a test PostgreSQL database.

## 2. Frontend Testing (Next.js / React)
*   **Frameworks:** `Jest` and `React Testing Library`
*   **Component Tests:** Ensure Voice UI buttons (Start Recording, Stop) trigger correct state changes.
*   **Admin UI Tests:** Ensure form validations prevent submitting schemes without mandatory fields (like Sources).

## 3. AI & RAG Pipeline Testing
*   **Grounding Tests:** Provide the RAG pipeline with a controlled JSON context and verify that the LLM response accurately reflects the context and nothing outside it.
*   **Hallucination Checks:** Introduce adversarial prompts (e.g., "Make up a scheme for flying cars") and verify the safety prompt correctly blocks fabrication.

## 4. CI/CD Integration
*   Automate test execution via GitHub Actions or GitLab CI on every pull request. Code cannot be merged into `main` unless coverage is met and tests pass.
