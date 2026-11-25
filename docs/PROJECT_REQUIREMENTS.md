# Sahayak AI - Project Requirements

## 1. Project Purpose
Build a multilingual, voice-first AI assistant (Sahayak AI) to help underserved and low-literacy citizens in India discover, understand, and navigate Government of India welfare schemes.

## 2. Core User Story
A citizen, potentially elderly or unable to read/write, speaks in an Indian regional language (e.g., Hindi, Tamil). The system understands the intent, securely retrieves verified government schemes, evaluates eligibility using deterministic rules, and verbally explains the scheme, benefits, and application steps in the user's native language.

## 3. Trust & Safety Requirements (Critical)
1. **Never fabricate a government scheme.**
2. **Never fabricate eligibility criteria.**
3. **Never fabricate benefit amounts.**
4. **Never fabricate application URLs.**
5. **Never fabricate required documents.**
6. **Never fabricate deadlines.**
7. Government information must be strictly associated with a verified source.
8. Every scheme must have a verification/last-verified tracking field.
9. If information is unavailable, explicitly state inability to verify.
10. Distinguish between "potentially eligible" and "officially eligible".
11. Attribute final eligibility to the relevant government authority.
12. Do not unnecessarily collect sensitive personal information.

## 4. Language Requirements
*   **Initial Rollout:** English, Hindi.
*   **Future Scalability:** Tamil, Telugu, Marathi, Bengali, Kannada, Malayalam, Gujarati, Punjabi, etc.

## 5. Voice-First UX
*   No typing required for the citizen.
*   Conversational profiling (gathering information incrementally instead of via forms).
*   Maintain short-term context (e.g., age, state, caste, gender) across voice turns.
*   Simple, culturally sensitive language suitable for elderly/low-literacy users.

## 6. Admin Requirements
*   No citizen accounts.
*   Only authenticated administrators can log in.
*   Dashboard to manage: Schemes, descriptions, benefits, eligibility criteria, required documents, application procedures, official URLs, sources, verification status, and supported languages.
