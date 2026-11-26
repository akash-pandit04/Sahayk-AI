import { useState, useRef, useEffect, useCallback } from 'react';

export type PipelineState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR';

interface UseVoicePipelineProps {
  language: string;
}

const SPEECH_THRESHOLD = 0.02;
const BARGE_IN_THRESHOLD = 0.045;
const SILENCE_PAUSE_MS = 950;
const MIN_SPEECH_MS = 350;
const BARGE_IN_HOLD_MS = 180;
const MAX_UTTERANCE_MS = 18000;
const SILENT_CYCLE_MS = 4000;

export function useVoicePipeline({ language }: UseVoicePipelineProps) {
  const [state, setState] = useState<PipelineState>('IDLE');
  const [isLiveCall, setIsLiveCall] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{ role: 'user' | 'assistant'; text: string; sources?: any[] }>>([]);
  const [errorMsg, setErrorMsg] = useState('');

  const stateRef = useRef<PipelineState>('IDLE');
  const liveCallRef = useRef(false);
  const conversationIdRef = useRef<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const discardOnStopRef = useRef(false);

  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const activeObjectUrlRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const speechActiveRef = useRef(false);
  const speechStartedAtRef = useRef(0);
  const lastSpeechAtRef = useRef(0);
  const recorderStartedAtRef = useRef(0);
  const bargeInStartedAtRef = useRef(0);

  const updateState = useCallback((next: PipelineState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const stopPlayback = useCallback(() => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.onended = null;
      audioPlayerRef.current.onerror = null;
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    if (activeObjectUrlRef.current) {
      URL.revokeObjectURL(activeObjectUrlRef.current);
      activeObjectUrlRef.current = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  const stopActiveRecorder = useCallback((discard: boolean) => {
    discardOnStopRef.current = discard;
    const rec = recorderRef.current;
    if (rec && rec.state !== 'inactive') {
      try {
        rec.stop();
      } catch {
        // ignore recorder already stopped
      }
    }
    recorderRef.current = null;
  }, []);

  const beginListeningTurn = useCallback(
    (preserveSpeechTiming = false) => {
      const stream = streamRef.current;
      if (!stream || !liveCallRef.current) return;

      stopActiveRecorder(true);
      if (!preserveSpeechTiming) {
        speechActiveRef.current = false;
        speechStartedAtRef.current = 0;
        lastSpeechAtRef.current = 0;
        setIsUserSpeaking(false);
      }

      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      audioChunksRef.current = [];
      discardOnStopRef.current = false;
      recorderStartedAtRef.current = Date.now();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const shouldDiscard = discardOnStopRef.current;
        const chunks = audioChunksRef.current;
        audioChunksRef.current = [];
        if (shouldDiscard || !liveCallRef.current || chunks.length === 0) {
          return;
        }
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size < 250) {
          if (liveCallRef.current) beginListeningTurn(false);
          return;
        }
        await sendVoiceTurn(blob);
      };

      recorder.start(200);
      updateState('LISTENING');
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [stopActiveRecorder, updateState]
  );

  const speakWithBrowserFallback = useCallback(
    (text: string) => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        if (liveCallRef.current) beginListeningTurn(false);
        else updateState('IDLE');
        return;
      }
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = language === 'hi' ? 'hi-IN' : language === 'ta' ? 'ta-IN' : language === 'te' ? 'te-IN' : 'en-IN';
      utter.onend = () => {
        if (liveCallRef.current) beginListeningTurn(false);
        else updateState('IDLE');
      };
      utter.onerror = () => {
        if (liveCallRef.current) beginListeningTurn(false);
        else updateState('IDLE');
      };
      updateState('SPEAKING');
      window.speechSynthesis.speak(utter);
    },
    [beginListeningTurn, language, updateState]
  );

  const playAudioBase64 = useCallback(
    async (audioBase64: string | null, mimeType: string | null, fallbackText: string) => {
      if (!audioBase64) {
        speakWithBrowserFallback(fallbackText);
        return;
      }

      try {
        stopPlayback();
        const binary = atob(audioBase64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: mimeType || 'audio/wav' });
        const url = URL.createObjectURL(blob);
        activeObjectUrlRef.current = url;

        const audio = audioPlayerRef.current || new Audio();
        audioPlayerRef.current = audio;
        audio.src = url;

        audio.onended = () => {
          if (activeObjectUrlRef.current) {
            URL.revokeObjectURL(activeObjectUrlRef.current);
            activeObjectUrlRef.current = null;
          }
          if (liveCallRef.current) {
            beginListeningTurn(false);
          } else {
            updateState('IDLE');
          }
        };

        audio.onerror = () => {
          speakWithBrowserFallback(fallbackText);
        };

        updateState('SPEAKING');
        await audio.play();
      } catch {
        speakWithBrowserFallback(fallbackText);
      }
    },
    [beginListeningTurn, speakWithBrowserFallback, stopPlayback, updateState]
  );

  const sendVoiceTurn = async (audioBlob: Blob) => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      updateState('PROCESSING');
      setErrorMsg('');

      const formData = new FormData();
      formData.append('audio', audioBlob, 'utterance.webm');
      formData.append('language', language);
      if (conversationIdRef.current) {
        formData.append('conversation_id', conversationIdRef.current);
      }

      const res = await fetch('/api/voice/turn', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error('Voice turn failed');
      }

      const data = await res.json();
      if (controller.signal.aborted || !liveCallRef.current) return;

      if (data.conversation_id) {
        conversationIdRef.current = data.conversation_id;
        setConversationId(data.conversation_id);
      }

      setHistory((prev) => [
        ...prev,
        { role: 'user', text: data.user_text },
        { role: 'assistant', text: data.response_text, sources: data.sources || [] },
      ]);

      await playAudioBase64(data.audio_base64, data.audio_mime_type, data.response_text);
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return;
      }
      console.error(err);
      setErrorMsg('Connection issue — please speak again.');
      if (liveCallRef.current) {
        beginListeningTurn(false);
      } else {
        updateState('ERROR');
      }
    }
  };

  const playTTS = useCallback(
    async (text: string) => {
      try {
        stopPlayback();
        updateState('PROCESSING');
        const ttsRes = await fetch('/api/voice/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, language }),
        });
        if (!ttsRes.ok) throw new Error('TTS failed');
        const blob = await ttsRes.blob();
        const url = URL.createObjectURL(blob);
        activeObjectUrlRef.current = url;

        const audio = audioPlayerRef.current || new Audio();
        audioPlayerRef.current = audio;
        audio.src = url;
        audio.onended = () => {
          if (activeObjectUrlRef.current) {
            URL.revokeObjectURL(activeObjectUrlRef.current);
            activeObjectUrlRef.current = null;
          }
          if (liveCallRef.current) beginListeningTurn(false);
          else updateState('IDLE');
        };
        audio.onerror = () => speakWithBrowserFallback(text);

        updateState('SPEAKING');
        await audio.play();
      } catch {
        speakWithBrowserFallback(text);
      }
    },
    [beginListeningTurn, language, speakWithBrowserFallback, stopPlayback, updateState]
  );

  const endLiveCall = useCallback(() => {
    liveCallRef.current = false;
    setIsLiveCall(false);
    setIsUserSpeaking(false);
    setMicLevel(0);

    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    if (vadTimerRef.current) {
      clearInterval(vadTimerRef.current);
      vadTimerRef.current = null;
    }

    stopActiveRecorder(true);
    stopPlayback();

    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    updateState('IDLE');
  }, [stopActiveRecorder, stopPlayback, updateState]);

  const startLiveCall = useCallback(async () => {
    setErrorMsg('');
    try {
      // Unlock browser audio autoplay inside user click gesture
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      audioPlayerRef.current.src =
        'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
      audioPlayerRef.current.play().catch(() => {});

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
      }
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      analyserRef.current = analyser;

      liveCallRef.current = true;
      setIsLiveCall(true);
      beginListeningTurn(false);

      const dataArray = new Float32Array(analyser.fftSize);
      vadTimerRef.current = setInterval(() => {
        if (!liveCallRef.current || !analyserRef.current) return;
        analyserRef.current.getFloatTimeDomainData(dataArray);

        let sumSq = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sumSq += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sumSq / dataArray.length);
        setMicLevel(Math.min(100, Math.round(rms * 450)));

        const now = Date.now();
        const curState = stateRef.current;

        if (curState === 'LISTENING') {
          if (rms > SPEECH_THRESHOLD) {
            if (!speechActiveRef.current) {
              speechActiveRef.current = true;
              speechStartedAtRef.current = now;
              setIsUserSpeaking(true);
            }
            lastSpeechAtRef.current = now;
          } else if (speechActiveRef.current) {
            if (now - lastSpeechAtRef.current >= SILENCE_PAUSE_MS) {
              const speechDuration = lastSpeechAtRef.current - speechStartedAtRef.current;
              speechActiveRef.current = false;
              setIsUserSpeaking(false);
              if (speechDuration >= MIN_SPEECH_MS) {
                stopActiveRecorder(false);
              } else {
                beginListeningTurn(false);
              }
            }
          } else if (now - recorderStartedAtRef.current >= SILENT_CYCLE_MS) {
            // Recycle idle lead-in buffer so first word isn't delayed by long silence
            beginListeningTurn(false);
          }

          if (speechActiveRef.current && now - speechStartedAtRef.current >= MAX_UTTERANCE_MS) {
            speechActiveRef.current = false;
            setIsUserSpeaking(false);
            stopActiveRecorder(false);
          }
        } else if (curState === 'SPEAKING' || curState === 'PROCESSING') {
          // Barge-in interruption detection
          if (rms > BARGE_IN_THRESHOLD) {
            if (bargeInStartedAtRef.current === 0) {
              bargeInStartedAtRef.current = now;
            } else if (now - bargeInStartedAtRef.current >= BARGE_IN_HOLD_MS) {
              bargeInStartedAtRef.current = 0;
              abortControllerRef.current?.abort();
              stopPlayback();
              speechActiveRef.current = true;
              speechStartedAtRef.current = now;
              lastSpeechAtRef.current = now;
              setIsUserSpeaking(true);
              beginListeningTurn(true);
            }
          } else {
            bargeInStartedAtRef.current = 0;
          }
        }
      }, 50);
    } catch {
      setErrorMsg('Microphone permission denied or unavailable.');
      updateState('ERROR');
    }
  }, [beginListeningTurn, stopActiveRecorder, stopPlayback, updateState]);

  const toggleRecording = useCallback(() => {
    if (liveCallRef.current) {
      endLiveCall();
    } else {
      startLiveCall();
    }
  }, [endLiveCall, startLiveCall]);

  useEffect(() => {
    return () => {
      endLiveCall();
    };
  }, [endLiveCall]);

  return {
    state,
    isLiveCall,
    isUserSpeaking,
    micLevel,
    conversationId,
    errorMsg,
    history,
    toggleRecording,
    stopPlayback,
    endLiveCall,
    playTTS,
  };
}
