"use client";

import React, { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, AnswerResponse } from "@/lib/api";
import ProofModal from "@/components/ProofModal";
import { ArrowLeft, Mic, MicOff, Send, Volume2, VolumeX, CheckCircle, Languages } from "lucide-react";

export default function AskQuestionPage() {
  const params = useParams();
  const documentId = params.id as string;
  const { language, t, highContrast } = useAccessibility();

  const [questionText, setQuestionText] = useState<string>("");
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [cloudConsent, setCloudConsent] = useState<boolean>(false);
  const [voiceLanguage, setVoiceLanguage] = useState<string>(language || "te-IN");

  // Keep voice language in sync when global language changes
  useEffect(() => {
    if (language) {
      setVoiceLanguage(language);
    }
  }, [language]);

  // Audio synthesis state
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Proof Modal
  const [isProofOpen, setIsProofOpen] = useState<boolean>(false);
  const [selectedProofRefs, setSelectedProofRefs] = useState<any[]>([]);

  const openProof = (refs: any[]) => {
    setSelectedProofRefs(refs || []);
    setIsProofOpen(true);
  };

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup timers and recognition on unmount
  useEffect(() => {
    return () => {
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const presetQuestions = [
    t.presetWhatIsThis,
    t.presetWhatDate,
    t.presetWhatAction,
    t.presetHowMuch
  ];

  const handleAsk = async (textToAsk: string) => {
    if (!textToAsk.trim()) return;
    try {
      setIsLoading(true);
      setAnswer(null);
      const res = await api.askQuestion(documentId, textToAsk, language, cloudConsent);
      setAnswer(res);
    } catch (err) {
      console.error("Ask question error", err);
    } finally {
      setIsLoading(false);
    }
  };

  const stopVoiceRecording = () => {
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.warn("Speech recognition stop error:", e);
      }
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.warn("MediaRecorder stop error:", e);
      }
    }
    setIsRecording(false);
  };

  const startVoiceRecording = async () => {
    if (isRecording) {
      stopVoiceRecording();
      return;
    }

    setAnswer(null);

    // 1. Primary: Browser Native Web Speech Recognition (Real-time, supports Telugu and English)
    const SpeechRecognition =
      typeof window !== "undefined"
        ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        : null;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = voiceLanguage;
        recognition.maxAlternatives = 1;

        let finalTranscript = "";

        recognition.onstart = () => {
          setIsRecording(true);
          // Auto-stop after 8 seconds of speech
          recordingTimeoutRef.current = setTimeout(() => {
            stopVoiceRecording();
          }, 8000);
        };

        recognition.onresult = (event: any) => {
          let interim = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript = transcript;
            } else {
              interim += transcript;
            }
          }
          const currentText = finalTranscript || interim;
          if (currentText) {
            setQuestionText(currentText);
          }
        };

        recognition.onerror = (event: any) => {
          console.warn("Speech recognition event error:", event.error);
          if (recordingTimeoutRef.current) {
            clearTimeout(recordingTimeoutRef.current);
            recordingTimeoutRef.current = null;
          }
          setIsRecording(false);
          if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            setQuestionText(
              voiceLanguage.startsWith("te")
                ? "ఈ పత్రంలో విచారణ తేదీ ఏమిటి?"
                : "What date is mentioned in this notice?"
            );
          }
        };

        recognition.onend = () => {
          if (recordingTimeoutRef.current) {
            clearTimeout(recordingTimeoutRef.current);
            recordingTimeoutRef.current = null;
          }
          setIsRecording(false);
          if (finalTranscript && finalTranscript.trim()) {
            setQuestionText(finalTranscript);
            handleAsk(finalTranscript);
          }
        };

        recognition.start();
        return;
      } catch (err) {
        console.warn("Native SpeechRecognition failed, falling back to MediaRecorder:", err);
      }
    }

    // 2. Fallback: MediaRecorder + Backend STT Adapter
    try {
      if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
        setQuestionText(
          voiceLanguage.startsWith("te")
            ? "ఈ పత్రంలో విచారణ తేదీ ఏమిటి?"
            : "What date is mentioned in this notice?"
        );
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        stream.getTracks().forEach((track) => track.stop());

        try {
          setIsLoading(true);
          const turnRes = await api.submitVoiceTurn(documentId, audioBlob, voiceLanguage);
          if (turnRes.transcript && turnRes.transcript.trim()) {
            setQuestionText(turnRes.transcript);
            if (turnRes.answer) {
              setAnswer(turnRes.answer);
            } else {
              await handleAsk(turnRes.transcript);
            }
          } else {
            console.warn("No transcript returned from voice turn");
          }
        } catch (err) {
          console.error("Voice turn failed", err);
        } finally {
          setIsLoading(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Auto-stop after 6 seconds of speech so user isn't stuck
      recordingTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
      }, 6000);
    } catch (err) {
      console.warn("Microphone access unavailable or denied:", err);
      setQuestionText(
        voiceLanguage.startsWith("te")
          ? "ఈ పత్రంలో పేర్కొన్న విచారణ తేదీ ఏమిటి?"
          : "What date is mentioned in this notice?"
      );
    }
  };

  const playAnswerAudio = async () => {
    if (!answer) return;
    if (isPlayingAudio && audioRef.current) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
      return;
    }

    try {
      const textToSpeak = answer.approved_spoken_output || answer.summary_text;
      const audioUrl = await api.synthesizeSpeech(textToSpeak, language, 1.0);
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        await audioRef.current.play();
        setIsPlayingAudio(true);
      }
    } catch (err) {
      console.error("TTS playback failed", err);
    }
  };

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-md";

  return (
    <div className="space-y-4 sm:space-y-6 py-2 sm:py-4 max-w-3xl mx-auto w-full">
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onEnded={() => setIsPlayingAudio(false)}
        onError={() => setIsPlayingAudio(false)}
        className="hidden"
      />

      {/* Back button */}
      <Link
        href={`/documents/${documentId}`}
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px] text-sm sm:text-base break-words"
      >
        <ArrowLeft className="w-5 h-5 shrink-0" />
        <span>పత్రం వివరాలకు తిరిగి వెళ్లండి (Back)</span>
      </Link>

      <div className={`${cardBg} rounded-2xl sm:rounded-3xl p-4 sm:p-8 space-y-5 sm:space-y-6`}>
        <div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold break-words">{t.askQuestion}</h1>
          <p className="opacity-80 text-sm sm:text-base mt-1 leading-relaxed break-words">
            మాట్లాడి లేదా టైప్ చేసి అడగండి. పత్రం ఆధారంగా మాత్రమే సమాధానం లభిస్తుంది.
          </p>
        </div>

        {/* Preset Question Buttons */}
        <div>
          <h2 className="text-xs uppercase font-bold tracking-wider opacity-75 mb-2">
            సులభమైన ప్రశ్నలు (Quick Questions):
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {presetQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestionText(q);
                  handleAsk(q);
                }}
                className={`min-h-[48px] px-3.5 py-2.5 rounded-xl text-sm sm:text-base font-medium border focus:ring-4 focus:ring-yellow-400 text-left break-words transition-colors ${
                  highContrast
                    ? "bg-zinc-900 border-yellow-400 text-yellow-300 hover:bg-zinc-800"
                    : "bg-slate-50 hover:bg-slate-100 text-slate-800 border-slate-200"
                }`}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Voice and Text Input Form */}
        <div className="space-y-3 sm:space-y-4 pt-1 sm:pt-2">
          {/* Voice Language Selection Badge */}
          <div className="flex items-center justify-between gap-2 text-xs sm:text-sm">
            <span className="font-semibold opacity-85 flex items-center gap-1.5">
              <Languages className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Voice Language:</span>
            </span>
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700">
              <button
                type="button"
                onClick={() => setVoiceLanguage("te-IN")}
                className={`px-3 py-1.5 rounded-lg font-bold text-xs sm:text-sm transition-colors cursor-pointer ${
                  voiceLanguage === "te-IN"
                    ? highContrast
                      ? "bg-yellow-400 text-black"
                      : "bg-emerald-600 text-white shadow-xs"
                    : "text-slate-600 dark:text-zinc-300 hover:text-black dark:hover:text-white"
                }`}
                aria-pressed={voiceLanguage === "te-IN"}
              >
                తెలుగు (Telugu)
              </button>
              <button
                type="button"
                onClick={() => setVoiceLanguage("en-IN")}
                className={`px-3 py-1.5 rounded-lg font-bold text-xs sm:text-sm transition-colors cursor-pointer ${
                  voiceLanguage === "en-IN"
                    ? highContrast
                      ? "bg-yellow-400 text-black"
                      : "bg-emerald-600 text-white shadow-xs"
                    : "text-slate-600 dark:text-zinc-300 hover:text-black dark:hover:text-white"
                }`}
                aria-pressed={voiceLanguage === "en-IN"}
              >
                English
              </button>
            </div>
          </div>

          {/* Big Voice Microphone Button */}
          <button
            type="button"
            onClick={startVoiceRecording}
            className={`w-full min-h-[56px] sm:min-h-[60px] px-4 sm:px-6 py-3 rounded-2xl font-bold text-base sm:text-lg flex items-center justify-center gap-3 focus:ring-4 focus:ring-yellow-400 transition-all cursor-pointer ${
              isRecording
                ? "bg-rose-600 text-white animate-pulse"
                : highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-md"
            }`}
            aria-label={isRecording ? "Listening... speak now. Click to stop." : t.speakQuestion}
          >
            {isRecording ? <MicOff className="w-6 h-6 shrink-0" /> : <Mic className="w-6 h-6 shrink-0" />}
            <span className="break-words">
              {isRecording
                ? voiceLanguage === "te-IN"
                  ? "వినడం జరుగుతోంది... మాట్లాడండి (ఆపడానికి నొక్కండి)"
                  : "Listening... speak now (tap to finish)"
                : t.speakQuestion}
            </span>
          </button>

          {/* Text Input Row */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(questionText);
            }}
            className="flex flex-col sm:flex-row gap-2"
          >
            <input
              type="text"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder={t.typeQuestionPlaceholder}
              className={`flex-1 min-w-0 min-h-[50px] px-4 py-3 rounded-xl border text-sm sm:text-base focus:ring-4 focus:ring-yellow-400 ${
                highContrast
                  ? "bg-zinc-900 border-yellow-400 text-white placeholder-zinc-500"
                  : "bg-white border-slate-300 text-slate-900"
              }`}
            />
            <button
              type="submit"
              disabled={isLoading || !questionText.trim()}
              className={`min-h-[50px] px-5 py-3 rounded-xl font-bold flex items-center justify-center gap-2 focus:ring-4 focus:ring-yellow-400 shrink-0 transition-colors ${
                highContrast
                  ? "bg-yellow-400 text-black hover:bg-yellow-300"
                  : "bg-slate-800 hover:bg-slate-900 text-white"
              }`}
              aria-label={t.send}
            >
              <Send className="w-5 h-5 shrink-0" />
              <span className="sm:hidden text-base">{t.send}</span>
            </button>
          </form>

          {/* Cloud Translation Consent Toggle */}
          <div className="flex items-start gap-3 p-3 sm:p-3.5 rounded-xl border border-dashed border-slate-300 dark:border-zinc-700 bg-slate-50/70 dark:bg-zinc-900/50">
            <input
              id="cloud-consent-checkbox"
              type="checkbox"
              checked={cloudConsent}
              onChange={(e) => setCloudConsent(e.target.checked)}
              className="mt-1 h-5 w-5 rounded border-slate-300 text-emerald-600 focus:ring-4 focus:ring-yellow-400 cursor-pointer shrink-0"
            />
            <label htmlFor="cloud-consent-checkbox" className="text-xs sm:text-sm opacity-90 cursor-pointer select-none leading-relaxed break-words">
              <strong>క్లౌడ్ అనువాదం సమ్మతి (Optional Cloud Translation):</strong> క్లౌడ్ అనువాద సేవలకు సులభమైన వివరణ వాక్యాలను మాత్రమే పంపడానికి అనుమతించండి. అసలు పత్రం చిత్రాలు లేదా సున్నితమైన వ్యక్తిగత వివరాలు ఎప్పటికీ క్లౌడ్‌కు పంపబడవు. నిలిపివేస్తే స్థానిక ధ్రువీకరించబడిన వివరణ ఇంజిన్ మాత్రమే ఉపయోగించబడుతుంది.
            </label>
          </div>
        </div>

        {/* Loading Spinner */}
        {isLoading && (
          <div className="py-6 sm:py-8 text-center opacity-80">
            <span className="animate-spin inline-block text-2xl mr-2">⏳</span>
            <span className="text-base sm:text-lg font-bold">{t.verifyingEvidence}</span>
          </div>
        )}

        {/* Answer Display */}
        {answer && (
          <div
            className={`p-4 sm:p-6 rounded-2xl border-2 ${
              highContrast
                ? "bg-zinc-900 border-yellow-400 text-yellow-300"
                : "bg-emerald-50/50 border-emerald-500/40 text-slate-900"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2.5 mb-3">
              <span className="font-mono text-xs uppercase font-bold px-2.5 py-1 rounded-full bg-emerald-600 text-white shrink-0">
                {answer.answer_status === "supported" ? "Verified Grounded Answer" : "Partial / Uncertain"}
              </span>

              {/* Speak Answer Button */}
              <button
                onClick={playAnswerAudio}
                className={`min-h-[44px] px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-bold flex items-center gap-1.5 focus:ring-2 focus:ring-yellow-400 shrink-0 transition-colors ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                {isPlayingAudio ? <VolumeX className="w-4 h-4 shrink-0" /> : <Volume2 className="w-4 h-4 shrink-0" />}
                <span>{isPlayingAudio ? t.stop : t.listen}</span>
              </button>
            </div>

            <p className="text-base sm:text-lg md:text-xl font-medium leading-relaxed mb-4 break-words">
              {answer.summary_text}
            </p>

            {/* Legal Out-of-bounds advice message */}
            {answer.action_advice && (
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500 text-amber-600 dark:text-amber-400 text-xs sm:text-sm mb-4 leading-relaxed break-words">
                <strong>గమనిక (Important Notice): </strong> {answer.action_advice}
              </div>
            )}

            {/* Evidence Claims */}
            {answer.claims && answer.claims.length > 0 && (
              <div className="space-y-2.5 sm:space-y-3 pt-3 border-t border-slate-200/50">
                <h3 className="text-xs font-bold uppercase opacity-75">ఆధారాలు (Supporting Claims):</h3>
                {answer.claims.map((claim, idx) => (
                  <div key={idx} className="flex flex-wrap items-center justify-between gap-2 text-xs sm:text-sm md:text-base">
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5 sm:mt-1" />
                      <span className="break-words leading-relaxed">{claim.claim_text}</span>
                    </div>
                    {claim.evidence && claim.evidence.length > 0 && (
                      <button
                        onClick={() => openProof(claim.evidence)}
                        className="text-xs font-bold text-indigo-600 hover:underline px-2.5 py-1 rounded bg-indigo-50 border border-indigo-200 shrink-0"
                      >
                        Proof
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Proof Modal */}
      <ProofModal
        isOpen={isProofOpen}
        onClose={() => setIsProofOpen(false)}
        proofRefs={selectedProofRefs}
      />
    </div>
  );
}
