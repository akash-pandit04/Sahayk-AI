# Sahayak AI - Voice Architecture & Multilingual Support

## 1. Core Principles
*   **Voice-First UX:** Typing is a fallback, not the primary input. The UI should have a dominant microphone interaction model.
*   **Language Agnostic Backend:** The core backend business logic, RAG, and schema operate primarily in English to ensure search accuracy and consistent logic evaluation. STT and TTS handle the translation layer.

## 2. Voice Pipeline Flow
1. **Microphone (Next.js):** Records user voice via the Web Audio/MediaRecorder API.
2. **Speech-to-Text (STT):**
   * Receives audio chunk.
   * **Language Detection:** Identifies the spoken language (e.g., Hindi).
   * **Transcription:** Converts audio to native script text.
3. **Translation to English:** STT service or LLM translates the native text to English for uniform backend processing.
4. **Processing (Backend):** English text processed through AI & Eligibility pipelines. Generates English text response.
5. **Translation to Native:** The LLM translates the final response back to the user's detected language.
6. **Text-to-Speech (TTS):**
   * TTS API converts the regional text into a natural-sounding audio stream.
7. **Playback:** Next.js client receives audio and auto-plays.

## 3. Technology Choices
*   **STT (Speech-to-Text):** 
    * *Primary Option:* Bhashini APIs (Govt of India, specifically tuned for Indian languages).
    * *Alternative Option:* OpenAI Whisper API (high accuracy, broad language support).
*   **TTS (Text-to-Speech):**
    * *Primary Option:* Bhashini TTS or Google Cloud TTS.
    * *Alternative Option:* ElevenLabs (for maximum realism) or Azure Cognitive Services.
    * The architecture will feature an abstract `VoiceService` class to easily swap providers.

## 4. Latency Mitigation
*   **Streaming TTS:** Stream TTS audio bytes to the frontend as they are generated to reduce time-to-first-byte (TTFB).
*   **Conversational Fillers:** Play a localized, pre-recorded audio cue (e.g., "जी, मैं जानकारी ढूंढ़ रही हूँ..." / "I am looking for the information...") immediately after the user stops speaking, bridging the processing gap.
