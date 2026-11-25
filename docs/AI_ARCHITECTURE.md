# Sahayak AI - AI Architecture

## 1. System Role & Boundaries
The LLM is strictly positioned as a **linguistic interface**, NOT a knowledge base. It is responsible for:
1. Translating user audio transcripts to an English intent.
2. Extracting structured data from user queries (e.g., Age, Location, Gender).
3. Formulating natural language responses in regional languages using **only** provided context.

## 2. RAG Pipeline (Retrieval-Augmented Generation)
**Flow:**
1. **Query Processing:** User asks, "I am a 65yo widow in MP, what schemes are for me?"
2. **Intent & Entity Extraction (LLM):** Extracts `{age: 65, marital_status: "widow", state: "MP"}`. Updates the session `user_profiles` table JSONB column.
3. **Retrieval (Vector + SQL):**
   * **Pre-filter (SQL):** Query PostgreSQL to exclude mathematically impossible schemes (e.g., exclude "Kerala" if state is "MP").
   * **Semantic Search:** Match remaining schemes against user intent using `pgvector`.
4. **Context Assembly:** Retrieve strict JSON records of matched schemes (Sources, Benefits, Eligibility, Documents).
5. **Generation (LLM):** LLM is prompted: *"You are Sahayak. Using ONLY the provided JSON context, answer the user. If the answer is not in the JSON, say you do not know. Translate the final answer into the user's language."*

## 3. Deterministic Eligibility Engine
To prevent hallucination of eligibility, we bypass the LLM for rule evaluation.
*   **Data Structure:** Rules stored in DB (e.g., `rule_type='age', operator='>=', value='60'`).
*   **Evaluation Logic (Python Backend):**
    * Fetch `user_profile` attributes.
    * For each candidate scheme, Python evaluates rules against known profile attributes.
    * Output mapped to: `POTENTIALLY_ELIGIBLE`, `NOT_ELIGIBLE`, or `INSUFFICIENT_INFORMATION`.
*   **LLM Handoff:** The evaluation result is passed to the LLM to format politely in the regional language (e.g., "Based on your age, you might be eligible... Please note final eligibility is decided by the government").

## 4. Anti-Hallucination Measures
*   **Strict System Prompts:** Zero tolerance for outside knowledge.
*   **Source Citations required:** The prompt forces the LLM to output which DB scheme ID it used. The backend verifies this ID exists in the context before returning the response.
