# Sahayak AI - Database Design

We will use PostgreSQL. The schema is highly normalized to ensure data integrity for government schemes.

## 1. Tables & Relationships

### Identity & Access
*   **`admins`**: `id`, `email`, `password_hash`, `name`, `created_at`, `updated_at`, `last_login`.

### Core Scheme Data
*   **`schemes`**: `id`, `name`, `slug`, `department`, `description`, `status` (active/draft/archived), `verification_status` (verified/unverified), `last_verified_at`, `created_at`, `updated_at`.
*   **`scheme_categories`**: `id`, `name` (e.g., Pension, Education, Health).
*   **`scheme_category_map`**: Join table between `schemes` and `scheme_categories`.
*   **`scheme_states`**: Join table mapping schemes to applicable states (or 'All India').
*   **`scheme_benefits`**: `id`, `scheme_id`, `benefit_type` (financial, material, service), `amount_value`, `description`.

### Trust & Verification
*   **`scheme_sources`**: `id`, `scheme_id`, `url`, `source_title`, `source_type` (official_website, pdf_guideline), `notes`, `verified_at`.

### Application Process
*   **`required_documents`**: `id`, `scheme_id`, `document_name`, `is_mandatory`, `description`.
*   **`application_steps`**: `id`, `scheme_id`, `step_number`, `action`, `mode` (online/offline), `url_reference`.

### AI & Eligibility
*   **`eligibility_rules`**: `id`, `scheme_id`, `rule_type` (age, income, gender, caste, location, occupation), `operator` (>=, <=, ==, IN), `value`, `is_mandatory`.
*   **`scheme_embeddings`**: `id`, `scheme_id`, `embedding` (vector type via pgvector), `chunk_text`.

### Conversations & Sessions
*   **`conversations`**: `id`, `session_id` (anonymous tracking id), `started_at`, `last_activity_at`.
*   **`user_profiles`**: `id`, `conversation_id`, `extracted_attributes` (JSONB - e.g., `{"age": 65, "state": "MP"}`).
*   **`conversation_messages`**: `id`, `conversation_id`, `role` (user/assistant/system), `content`, `timestamp`.

### Auditing
*   **`audit_logs`**: `id`, `admin_id`, `action`, `table_name`, `record_id`, `old_values` (JSONB), `new_values` (JSONB), `timestamp`.
