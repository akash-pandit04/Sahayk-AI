# Sahayak AI - Security & Privacy Strategy

## 1. Admin Authentication & Authorization
*   **Mechanism:** JSON Web Tokens (JWT) for stateless authentication.
*   **Password Storage:** Bcrypt hashing.
*   **Access Control:** Strict API routing. `/api/admin/*` endpoints require a valid admin JWT. 

## 2. Citizen Privacy
*   **No Login/Registration:** Citizens interact completely anonymously.
*   **Ephemeral Sessions:** A random UUID tracks the conversation (`conversation_id`).
*   **Data Minimization:** We only extract necessary attributes (age, location, gender) to evaluate scheme eligibility. We explicitly do not ask for or store PII (Aadhar numbers, full names, phone numbers) in the AI conversation context.
*   **Data Retention:** Conversation logs (`conversation_messages` and `user_profiles`) can be periodically purged or anonymized after X days to ensure privacy.

## 3. API & Infrastructure Security
*   **CORS Configuration:** Strictly limit CORS to the Next.js frontend domain to prevent unauthorized API usage.
*   **Rate Limiting:** Implement rate limiting (e.g., via FastAPI `slowapi`) on the chat endpoints to prevent abuse and API cost overruns.
*   **Secrets Management:** All API keys (LLM, DB credentials, Voice APIs) must be injected via environment variables (`.env`). No secrets committed to source control.

## 4. Auditing
*   **Admin Audit Trail:** The `audit_logs` table records every create, update, or delete action on schemes, eligibility rules, and sources. Includes `admin_id`, `action`, `old_values`, and `new_values`.

## 5. Security Headers
*   Use standard security headers (Helmet in Next.js, Secure headers middleware in FastAPI) to protect against XSS and clickjacking.
