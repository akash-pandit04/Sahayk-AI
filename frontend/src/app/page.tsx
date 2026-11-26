"use client";

import { useState, useEffect, useRef } from "react";
import { Mic, PhoneOff, Volume2, AlertCircle } from "lucide-react";
import { languages, translations } from "@/lib/i18n";
import { useVoicePipeline } from "@/hooks/useVoicePipeline";

const GEMINI_VOICES = [
  { id: "gemini:Kore", label: "Voice: Hindi Woman — Kore (Default)" },
  { id: "gemini:Aoede", label: "Voice: Woman — Aoede" },
  { id: "gemini:Zephyr", label: "Voice: Woman — Zephyr" },
  { id: "gemini:Puck", label: "Voice: Man — Puck" },
  { id: "gemini:Charon", label: "Voice: Man — Charon" },
];

export default function CitizenPage() {
  const [langCode, setLangCode] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("sahayak_lang");
    if (saved) setLangCode(saved);
  }, []);

  const handleLangSelect = (code: string) => {
    localStorage.setItem("sahayak_lang", code);
    setLangCode(code);
  };

  if (!langCode) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gray-50">
        <h1 className="text-2xl font-bold mb-8 text-center">आप किस भाषा में बात करना चाहेंगे?</h1>
        <div className="space-y-4 w-full max-w-xs">
          {languages.map((l) => (
            <button
              key={l.code}
              onClick={() => handleLangSelect(l.code)}
              className="w-full py-4 text-xl font-medium bg-white border border-gray-300 rounded-xl shadow-sm hover:bg-blue-50 focus:ring-2 focus:ring-blue-500 outline-none"
            >
              {l.nativeName}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return <VoiceInterface language={langCode} onChangeLanguage={handleLangSelect} />;
}

function VoiceInterface({
  language,
  onChangeLanguage,
}: {
  language: string;
  onChangeLanguage: (code: string) => void;
}) {
  const t = translations[language as keyof typeof translations] || translations.hi;
  const historyEndRef = useRef<HTMLDivElement | null>(null);
  const [voiceId, setVoiceId] = useState<string>("gemini:Kore");
  const [browserVoices, setBrowserVoices] = useState<Array<{ id: string; label: string }>>([]);

  useEffect(() => {
    const savedVoice = localStorage.getItem("sahayak_voice");
    if (savedVoice) setVoiceId(savedVoice);

    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      const loadVoices = () => {
        const list = window.speechSynthesis
          .getVoices()
          .filter((v) => v.lang.toLowerCase().startsWith("hi") || v.lang.toLowerCase().startsWith("en-in"))
          .map((v) => ({ id: `browser:${v.voiceURI}`, label: `Fast Browser: ${v.name}` }));
        setBrowserVoices(list);
      };
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  const handleVoiceChange = (nextVoice: string) => {
    localStorage.setItem("sahayak_voice", nextVoice);
    setVoiceId(nextVoice);
  };

  const {
    state,
    isLiveCall,
    isUserSpeaking,
    micLevel,
    errorMsg,
    history,
    toggleRecording,
    endLiveCall,
    playTTS,
  } = useVoicePipeline({ language, voiceId });

  const isListening = state === "LISTENING";
  const isProcessing = state === "PROCESSING";
  const isSpeaking = state === "SPEAKING";

  let statusText = t.stateIdle;
  if (isListening) statusText = isUserSpeaking ? t.stateUserSpeaking : t.stateListening;
  if (isProcessing) statusText = t.stateProcessing;
  if (isSpeaking) statusText = t.stateSpeaking;
  if (state === "ERROR") statusText = t.stateError;

  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  const micScale = isListening && isUserSpeaking ? 1 + Math.min(0.22, micLevel / 300) : 1;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 max-w-md mx-auto shadow-xl relative overflow-hidden">
      {/* Header */}
      <header className="px-6 pt-8 pb-3 text-center">
        <div className="flex items-center justify-center gap-2">
          <h1 className="text-3xl font-bold text-blue-900">Sahayak AI</h1>
          {isLiveCall && (
            <span className="px-2 py-0.5 text-xs font-semibold bg-green-100 text-green-800 rounded-full animate-pulse">
              LIVE
            </span>
          )}
        </div>
        <h2 className="text-lg font-medium text-gray-700 mt-1">{t.title}</h2>

        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <select
            value={language}
            onChange={(e) => {
              endLiveCall();
              onChangeLanguage(e.target.value);
            }}
            className="bg-white border border-gray-300 rounded px-3 py-1 text-sm shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Select Language"
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.nativeName}
              </option>
            ))}
          </select>

          <select
            value={voiceId}
            onChange={(e) => handleVoiceChange(e.target.value)}
            className="bg-white border border-gray-300 rounded px-3 py-1 text-sm shadow-sm outline-none focus:ring-2 focus:ring-blue-500 max-w-[210px]"
            aria-label="Select Voice"
          >
            {GEMINI_VOICES.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
            {browserVoices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Main Interaction Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 space-y-6">
        {errorMsg && (
          <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-center w-full max-w-xs shadow-sm">
            <AlertCircle className="w-5 h-5 mr-2 shrink-0" />
            <span className="text-sm font-medium">{errorMsg}</span>
          </div>
        )}

        {/* Live Voice Call Button */}
        <div className="relative flex items-center justify-center">
          {isListening && isUserSpeaking && (
            <div className="absolute inset-0 bg-emerald-400 rounded-full animate-ping opacity-30" />
          )}
          {isSpeaking && (
            <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-25" />
          )}

          <button
            onClick={toggleRecording}
            aria-label={t.micLabel}
            style={{ transform: `scale(${micScale})` }}
            className={`
              relative z-10 w-32 h-32 rounded-full flex items-center justify-center shadow-lg transition-all duration-150
              ${
                isLiveCall
                  ? isSpeaking
                    ? "bg-indigo-600 text-white"
                    : isProcessing
                    ? "bg-amber-500 text-white"
                    : "bg-emerald-600 text-white"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }
              outline-none focus:ring-4 focus:ring-blue-300
            `}
          >
            {isLiveCall ? <PhoneOff className="w-11 h-11" /> : <Mic className="w-12 h-12" />}
          </button>
        </div>

        {/* Status Text */}
        <div className="text-center text-base font-medium text-gray-800 flex items-center justify-center space-x-2 px-4">
          {isListening && (
            <span
              className={`w-3 h-3 rounded-full ${
                isUserSpeaking ? "bg-emerald-500 animate-ping" : "bg-emerald-500 animate-pulse"
              }`}
            />
          )}
          {isProcessing && (
            <span className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
          )}
          {isSpeaking && <Volume2 className="w-5 h-5 text-indigo-600 animate-pulse shrink-0" />}
          <span>{statusText}</span>
        </div>

        {isLiveCall && (
          <button
            onClick={endLiveCall}
            className="px-6 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-full font-medium text-sm transition-colors outline-none"
          >
            {t.stop}
          </button>
        )}
      </main>

      {/* Conversation History */}
      {history.length > 0 && (
        <div className="bg-white p-5 rounded-t-3xl shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.1)] flex-1 overflow-y-auto max-h-[40vh]">
          <div className="space-y-4">
            {history.map((msg, idx) => (
              <div key={idx} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`
                  px-4 py-3 rounded-2xl max-w-[85%] text-base
                  ${
                    msg.role === "user"
                      ? "bg-blue-100 text-blue-900 rounded-br-sm"
                      : "bg-gray-100 text-gray-800 rounded-bl-sm"
                  }
                `}
                >
                  {msg.text}
                </div>

                {msg.role === "assistant" && (
                  <div className="mt-2 flex flex-col space-y-2">
                    <button
                      onClick={() => playTTS(msg.text)}
                      className="text-blue-600 flex items-center text-sm font-medium hover:underline outline-none"
                    >
                      <Volume2 className="w-4 h-4 mr-1" />
                      {t.replay}
                    </button>

                    {msg.sources && msg.sources.length > 0 && (
                      <div className="text-xs text-gray-500 mt-1">
                        <strong>{t.sourceInfo}:</strong>
                        <ul className="list-disc pl-4 mt-1 space-y-1">
                          {msg.sources.map((src, i) => (
                            <li key={i}>
                              <a href={src.url} target="_blank" rel="noreferrer" className="underline">
                                {src.title}
                              </a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={historyEndRef} />
          </div>
        </div>
      )}

      {/* Footer Disclaimer */}
      <footer className="p-4 bg-gray-100 text-xs text-gray-500 text-center border-t border-gray-200">
        {t.disclaimer}
      </footer>
    </div>
  );
}
