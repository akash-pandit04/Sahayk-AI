import { useState, useRef, useEffect, useCallback } from 'react';

export type PipelineState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR';

interface UseVoicePipelineProps {
  language: string;
}

export function useVoicePipeline({ language }: UseVoicePipelineProps) {
  const [state, setState] = useState<PipelineState>('IDLE');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{ role: 'user' | 'assistant', text: string, sources?: any[] }>>([]);
  const [errorMsg, setErrorMsg] = useState('');
  
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const currentAudio = useRef<HTMLAudioElement | null>(null);

  const stopPlayback = useCallback(() => {
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current.currentTime = 0;
      currentAudio.current = null;
    }
    if (state === 'SPEAKING') {
      setState('IDLE');
    }
  }, [state]);

  const startListening = async () => {
    stopPlayback(); // stop any current speech
    setErrorMsg('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorder.current = recorder;
      audioChunks.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        const audioBlob = new Blob(audioChunks.current, { type: recorder.mimeType });
        await processAudio(audioBlob);
      };

      recorder.start();
      setState('LISTENING');
    } catch (err: any) {
      setErrorMsg("Microphone permission denied or unavailable.");
      setState('ERROR');
    }
  };

  const stopListening = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
      mediaRecorder.current.stop();
      setState('PROCESSING');
    }
  };

  const processAudio = async (audioBlob: Blob) => {
    try {
      setState('PROCESSING');
      
      // 1. Transcribe
      const formData = new FormData();
      formData.append('audio', audioBlob);
      formData.append('language', language);
      if (conversationId) formData.append('conversation_id', conversationId);

      const sttRes = await fetch(process.env.NEXT_PUBLIC_API_URL + '/voice/transcribe', {
        method: 'POST',
        body: formData
      });
      if (!sttRes.ok) throw new Error("STT failed");
      const sttData = await sttRes.json();
      
      const userText = sttData.text;
      const cId = sttData.conversation_id;
      
      setHistory(prev => [...prev, { role: 'user', text: userText }]);

      // 2. Assistant API
      const aiRes = await fetch(process.env.NEXT_PUBLIC_API_URL + '/assistant/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          language: language,
          conversation_id: cId
        })
      });
      if (!aiRes.ok) throw new Error("Assistant failed");
      const aiData = await aiRes.json();
      
      setConversationId(aiData.conversation_id);
      
      const aiResponseText = aiData.needs_more_information && aiData.missing_fields.length > 0
        ? aiData.response_text // The backend should generate a localized question for the missing info
        : aiData.response_text;

      setHistory(prev => [...prev, { role: 'assistant', text: aiResponseText, sources: aiData.sources }]);

      // 3. TTS
      await playTTS(aiResponseText);
      
    } catch (err: any) {
      console.error(err);
      setErrorMsg("Network or processing error.");
      setState('ERROR');
    }
  };

  const playTTS = async (text: string) => {
    try {
      setState('PROCESSING');
      const ttsRes = await fetch(process.env.NEXT_PUBLIC_API_URL + '/voice/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language })
      });
      if (!ttsRes.ok) throw new Error("TTS failed");
      
      const blob = await ttsRes.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setState('IDLE');
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        setState('ERROR');
      };
      
      currentAudio.current = audio;
      audio.play();
      setState('SPEAKING');
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to play audio.");
      setState('ERROR');
    }
  };

  const toggleRecording = () => {
    if (state === 'LISTENING') {
      stopListening();
    } else {
      startListening();
    }
  };

  return {
    state,
    errorMsg,
    history,
    toggleRecording,
    stopPlayback,
    playTTS
  };
}
