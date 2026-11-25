"use client";

import { useState, useEffect } from "react";
import { Mic, Square, Volume2, AlertCircle } from "lucide-react";
import { languages, translations } from "@/lib/i18n";
import { useVoicePipeline } from "@/hooks/useVoicePipeline";

export default function CitizenPage() {
  const [langCode, setLangCode] = useState<string | null>(null);

  // Load saved lang on mount
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
        <h1 className="text-2xl font-bold mb-8">आप किस भाषा में बात करना चाहेंगे?</h1>
        <div className="space-y-4 w-full max-w-xs">
          {languages.map(l => (
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

  return <VoiceInterface language={langCode} onChangeLanguage={() => setLangCode(null)} />;
}

function VoiceInterface({ language, onChangeLanguage }: { language: string, onChangeLanguage: () => void }) {
  const t = translations[language as keyof typeof translations] || translations.hi;
  
  const { state, errorMsg, history, toggleRecording, stopPlayback, playTTS } = useVoicePipeline({ language });

  const isListening = state === 'LISTENING';
  const isProcessing = state === 'PROCESSING';
  const isSpeaking = state === 'SPEAKING';
  
  // Status message mappings
  let statusText = t.stateIdle;
  if (isListening) statusText = t.stateListening;
  if (isProcessing) statusText = t.stateProcessing;
  if (isSpeaking) statusText = t.stateSpeaking;
  if (state === 'ERROR') statusText = t.stateError;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 max-w-md mx-auto shadow-xl relative overflow-hidden">
      
      {/* Header */}
      <header className="px-6 pt-10 pb-4 text-center">
        <h1 className="text-3xl font-bold text-blue-900">Sahayak AI</h1>
        <h2 className="text-xl font-medium text-gray-700 mt-2">{t.title}</h2>
        
        <select 
          value={language} 
          onChange={(e) => {
            localStorage.setItem("sahayak_lang", e.target.value);
            window.location.reload();
          }}
          className="mt-4 bg-white border border-gray-300 rounded px-3 py-1 text-sm shadow-sm outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Select Language"
        >
          {languages.map(l => (
            <option key={l.code} value={l.code}>{l.nativeName}</option>
          ))}
        </select>
      </header>

      {/* Main Interaction Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 space-y-8">
        
        {/* Error Alert */}
        {errorMsg && (
          <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg flex items-center w-full max-w-xs shadow-sm">
            <AlertCircle className="w-5 h-5 mr-2 shrink-0" />
            <span className="text-sm font-medium">{errorMsg}</span>
          </div>
        )}

        {/* Big Mic Button */}
        <div className="relative">
          {/* Pulse animation when listening */}
          {isListening && (
            <div className="absolute inset-0 bg-red-500 rounded-full animate-ping opacity-25"></div>
          )}
          
          <button
            onClick={toggleRecording}
            disabled={isProcessing}
            aria-label={t.micLabel}
            className={`
              relative z-10 w-32 h-32 rounded-full flex items-center justify-center shadow-lg transition-all
              ${isListening ? 'bg-red-500 scale-110 text-white' : 'bg-blue-600 hover:bg-blue-700 text-white'}
              ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}
              outline-none focus:ring-4 focus:ring-blue-300
            `}
          >
            {isListening ? (
              <Square className="w-12 h-12 fill-current" />
            ) : (
              <Mic className="w-12 h-12" />
            )}
          </button>
        </div>

        {/* Status Text */}
        <div className="text-xl font-medium text-gray-800 flex items-center space-x-2">
          {isListening && <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>}
          {isProcessing && <span className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></span>}
          {isSpeaking && <Volume2 className="w-5 h-5 text-blue-600 animate-pulse" />}
          <span>{statusText}</span>
        </div>

        {/* Stop Playback Button */}
        {isSpeaking && (
          <button 
            onClick={stopPlayback}
            className="px-6 py-2 bg-gray-200 hover:bg-gray-300 rounded-full text-gray-800 font-medium transition-colors outline-none focus:ring-2 focus:ring-gray-400"
          >
            {t.stop}
          </button>
        )}
      </main>

      {/* History (Minimal) */}
      {history.length > 0 && (
        <div className="bg-white p-6 rounded-t-3xl shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.1)] flex-1 overflow-y-auto max-h-[40vh]">
          <div className="space-y-4">
            {history.map((msg, idx) => (
              <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`
                  px-4 py-3 rounded-2xl max-w-[85%] text-base
                  ${msg.role === 'user' 
                    ? 'bg-blue-100 text-blue-900 rounded-br-sm' 
                    : 'bg-gray-100 text-gray-800 rounded-bl-sm'}
                `}>
                  {msg.text}
                </div>
                
                {msg.role === 'assistant' && (
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
                              <a href={src.url} target="_blank" rel="noreferrer" className="underline">{src.title}</a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
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
