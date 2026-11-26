import { useState, useRef, useEffect, useCallback } from 'react';

export type PipelineState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR';

interface UseVoicePipelineProps {
  language: string;
}

const MIN_SPEECH_THRESHOLD = 0.025;
const BARGE_IN_MULTIPLIER = 2.6;
const SILENCE_PAUSE_MS = 900;
const MIN_SPEECH_MS = 350;
const BARGE_IN_HOLD_MS = 200;
const MAX_UTTERANCE_MS = 16000;
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
  const isSendingRef = useRef(false);

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const recorderTokenRef = useRef(0);

  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const activeObjectUrlRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const noiseFloorRef = useRef(0.01);
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
    if (discard) {
      // Invalidate previous recorder token so its async onstop callback cannot fire sendVoiceTurn
      recorderTokenRef.current += 1;
    }
    const rec = recorderRef.current;
    if (rec && rec.state !== 'inactive') {
      try {
        rec.stop();
      } catch {
        // ignore if already stopped
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

      const token = ++recorderTokenRef.current;
      const chunks: Blob[] = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorderStartedAtRef.current = Date.now();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && recorderTokenRef.current === token) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        // Only the active, non-discarded recorder may submit a turn
        if (recorderTokenRef.current !== token || !liveCallRef.current || chunks.length === 0) {
          return;
        }
        if (isSendingRef.current) {
          return;
        }
        const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size < 300) {
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

  const selectHindiFemaleVoice = useCallback((): SpeechSynthesisVoice | null => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      return null;
    }
    const voices = window.speechSynthesis.getVoices();
    const hindiVoices = voices.filter((v) => v.lang.toLowerCase().startsWith('hi'));
    if (hindiVoices.length === 0) {
      return null;
    }

    const femaleHints = ['swara', 'kalpana', 'heera', 'lekha', 'google हिन्दी', 'hindi', 'female', 'woman'];
    const maleHints = ['madhur', 'hemant', 'prabhat', 'male', 'man'];

    const preferredFemale = hindiVoices.find((v) => {
      const name = v.name.toLowerCase();
      return femaleHints.some((h) => name.includes(h)) && !maleHints.some((m) => name.includes(m));
    });
    if (preferredFemale) return preferredFemale;

    const nonMale = hindiVoices.find((v) => !maleHints.some((m) => v.name.toLowerCase().includes(m)));
    return nonMale || hindiVoices[0];
  }, []);

  const speakFast = useCallback(
    (text: string): boolean => {
      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        return false;
      }
      const hindiFemaleVoice = selectHindiFemaleVoice();
      // Only use instant browser speech if a Hindi voice is available so voice stays consistent everywhere
      if (!hindiFemaleVoice) {
        return false;
      }

      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.voice = hindiFemaleVoice;
      utter.lang = hindiFemaleVoice.lang || 'hi-IN';
      utter.rate = 1.02;

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
      return true;
    },
    [beginListeningTurn, selectHindiFemaleVoice, updateState]
  );

  const playServerAudioOrFallback = useCallback(
    async (text: string, audioBase64?: string | null, mimeType?: string | null) => {
      try {
        stopPlayback();
        let blobUrl: string;
        if (audioBase64) {
          const binary = atob(audioBase64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          blobUrl = URL.createObjectURL(new Blob([bytes], { type: mimeType || 'audio/wav' }));
        } else {
          const ttsRes = await fetch('/api/voice/synthesize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, language }),
          });
          if (!ttsRes.ok) throw new Error('TTS failed');
          blobUrl = URL.createObjectURL(await ttsRes.blob());
        }

        activeObjectUrlRef.current = blobUrl;
        const audio = audioPlayerRef.current || new Audio();
        audioPlayerRef.current = audio;
        audio.src = blobUrl;
        audio.onended = () => {
          if (activeObjectUrlRef.current) {
            URL.revokeObjectURL(activeObjectUrlRef.current);
            activeObjectUrlRef.current = null;
          }
          if (liveCallRef.current) beginListeningTurn(false);
          else updateState('IDLE');
        };
        audio.onerror = () => {
          if (!speakFast(text) && liveCallRef.current) beginListeningTurn(false);
        };

        updateState('SPEAKING');
        await audio.play();
      } catch {
        if (!speakFast(text)) {
          if (liveCallRef.current) beginListeningTurn(false);
          else updateState('IDLE');
        }
      }
    },
    [beginListeningTurn, language, speakFast, stopPlayback, updateState]
  );

  const sendVoiceTurn = async (audioBlob: Blob) => {
    if (isSendingRef.current) return;
    isSendingRef.current = true;

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Use instant browser Hindi female voice when available; otherwise use Gemini TTS (Kore)
    const hasInstantVoice = Boolean(selectHindiFemaleVoice());

    try {
      updateState('PROCESSING');
      setErrorMsg('');

      const formData = new FormData();
      formData.append('audio', audioBlob, 'utterance.webm');
      formData.append('language', language);
      formData.append('include_audio', hasInstantVoice ? 'false' : 'true');
      if (conversationIdRef.current) {
        formData.append('conversation_id', conversationIdRef.current);
      }

      const res = await fetch('/api/voice/turn', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${res.status})`);
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

      isSendingRef.current = false;
      if (hasInstantVoice && speakFast(data.response_text)) {
        return;
      }
      await playServerAudioOrFallback(data.response_text, data.audio_base64, data.audio_mime_type);
    } catch (err: any) {
      isSendingRef.current = false;
      if (err?.name === 'AbortError') {
        return;
      }
      console.error(err);
      setErrorMsg(err?.message || 'Connection issue — retrying listening.');
      if (liveCallRef.current) {
        // Back off 1.5s on error so we never flood the API
        setTimeout(() => {
          if (liveCallRef.current && stateRef.current !== 'LISTENING') {
            beginListeningTurn(false);
          }
        }, 1500);
      } else {
        updateState('ERROR');
      }
    } finally {
      isSendingRef.current = false;
    }
  };

  const playTTS = useCallback(
    async (text: string) => {
      await playServerAudioOrFallback(text, null, null);
    },
    [playServerAudioOrFallback]
  );

  const endLiveCall = useCallback(() => {
    liveCallRef.current = false;
    isSendingRef.current = false;
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
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      audioPlayerRef.current.src =
        'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
      audioPlayerRef.current.play().catch(() => {});

      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
      }

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

      noiseFloorRef.current = 0.01;
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
          if (!speechActiveRef.current) {
            // Smooth ambient noise floor adaptation when user is silent
            noiseFloorRef.current = noiseFloorRef.current * 0.92 + rms * 0.08;
          }
          const dynamicSpeechThreshold = Math.max(MIN_SPEECH_THRESHOLD, noiseFloorRef.current * 2.4);

          if (rms > dynamicSpeechThreshold) {
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
            beginListeningTurn(false);
          }

          if (speechActiveRef.current && now - speechStartedAtRef.current >= MAX_UTTERANCE_MS) {
            speechActiveRef.current = false;
            setIsUserSpeaking(false);
            stopActiveRecorder(false);
          }
        } else if (curState === 'SPEAKING' || curState === 'PROCESSING') {
          const bargeInThreshold = Math.max(0.055, noiseFloorRef.current * BARGE_IN_MULTIPLIER);
          if (rms > bargeInThreshold) {
            if (bargeInStartedAtRef.current === 0) {
              bargeInStartedAtRef.current = now;
            } else if (now - bargeInStartedAtRef.current >= BARGE_IN_HOLD_MS) {
              bargeInStartedAtRef.current = 0;
              isSendingRef.current = false;
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
