"use client";

import React, { useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, AnswerResponse } from "@/lib/api";
import ProofModal from "@/components/ProofModal";
import { ArrowLeft, Mic, MicOff, Send, Volume2, VolumeX, AlertTriangle, CheckCircle, ShieldCheck } from "lucide-react";

export default function AskQuestionPage() {
  const params = useParams();
  const documentId = params.id as string;
  const { language, t, highContrast } = useAccessibility();

  const [questionText, setQuestionText] = useState<string>("");
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [cloudConsent, setCloudConsent] = useState<boolean>(false);

  // Audio synthesis state
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Proof Modal
  const [isProofOpen, setIsProofOpen] = useState<boolean>(false);
  const [selectedProofRefs, setSelectedProofRefs] = useState<any[]>([]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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

  const startVoiceRecording = async () => {
    if (isRecording) {
      // Stop recording
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    try {
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
          const turnRes = await api.submitVoiceTurn(documentId, audioBlob, language);
          if (turnRes.transcript) {
            setQuestionText(turnRes.transcript);
            if (turnRes.answer) {
              setAnswer(turnRes.answer);
            } else {
              await handleAsk(turnRes.transcript);
            }
          }
        } catch (err) {
          console.error("Voice turn failed", err);
        } finally {
          setIsLoading(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.warn("Microphone access unavailable or denied:", err);
      // Fallback: populate simulated question for user
      setQuestionText("ఈ పత్రంలో పేర్కొన్న విచారణ తేదీ ఏమిటి?");
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
    <div className="space-y-6 py-4 max-w-3xl mx-auto">
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
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px]"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>పత్రం వివరాలకు తిరిగి వెళ్లండి (Back)</span>
      </Link>

      <div className={`${cardBg} rounded-3xl p-6 sm:p-8 space-y-6`}>
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold">{t.askQuestion}</h1>
          <p className="opacity-80 text-base mt-1">
            మాట్లాడి లేదా టైప్ చేసి అడగండి. పత్రం ఆధారంగా మాత్రమే సమాధానం లభిస్తుంది.
          </p>
        </div>

        {/* Preset Question Buttons */}
        <div>
          <h2 className="text-xs uppercase font-bold tracking-wider opacity-75 mb-2">
            సులభమైన ప్రశ్నలు (Quick Questions):
          </h2>
          <div className="flex flex-wrap gap-2">
            {presetQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestionText(q);
                  handleAsk(q);
                }}
                className={`min-h-[48px] px-4 py-2 rounded-xl text-base font-medium border focus:ring-4 focus:ring-yellow-400 text-left ${
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
        <div className="space-y-4 pt-2">
          {/* Big Voice Microphone Button */}
          <button
            onClick={startVoiceRecording}
            className={`w-full min-h-[60px] px-6 py-3 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 focus:ring-4 focus:ring-yellow-400 transition-all ${
              isRecording
                ? "bg-rose-600 text-white animate-pulse"
                : highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-md"
            }`}
            aria-label={isRecording ? t.listening : t.speakQuestion}
          >
            {isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
            <span>{isRecording ? t.listening : t.speakQuestion}</span>
          </button>

          {/* Text Input Row */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(questionText);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder={t.typeQuestionPlaceholder}
              className={`flex-1 min-h-[50px] px-4 py-3 rounded-xl border text-base focus:ring-4 focus:ring-yellow-400 ${
                highContrast
                  ? "bg-zinc-900 border-yellow-400 text-white placeholder-zinc-500"
                  : "bg-white border-slate-300 text-slate-900"
              }`}
            />
            <button
              type="submit"
              disabled={isLoading || !questionText.trim()}
              className={`min-h-[50px] px-5 py-3 rounded-xl font-bold flex items-center justify-center focus:ring-4 focus:ring-yellow-400 ${
                highContrast
                  ? "bg-yellow-400 text-black"
                  : "bg-slate-800 hover:bg-slate-900 text-white"
              }`}
              aria-label={t.send}
            >
              <Send className="w-5 h-5" />
            </button>
          </form>

          {/* Cloud Translation Consent Toggle */}
          <div className="flex items-start gap-3 p-3.5 rounded-xl border border-dashed border-slate-300 dark:border-zinc-700 bg-slate-50/70 dark:bg-zinc-900/50">
            <input
              id="cloud-consent-checkbox"
              type="checkbox"
              checked={cloudConsent}
              onChange={(e) => setCloudConsent(e.target.checked)}
              className="mt-1 h-5 w-5 rounded border-slate-300 text-emerald-600 focus:ring-4 focus:ring-yellow-400 cursor-pointer"
            />
            <label htmlFor="cloud-consent-checkbox" className="text-xs sm:text-sm opacity-90 cursor-pointer select-none">
              <strong>క్లౌడ్ అనువాదం సమ్మతి (Optional Cloud Translation):</strong> క్లౌడ్ అనువాద సేవలకు సులభమైన వివరణ వాక్యాలను మాత్రమే పంపడానికి అనుమతించండి. అసలు పత్రం చిత్రాలు లేదా సున్నితమైన వ్యక్తిగత వివరాలు ఎప్పటికీ క్లౌడ్‌కు పంపబడవు. నిలిపివేస్తే స్థానిక ధ్రువీకరించబడిన వివరణ ఇంజిన్ మాత్రమే ఉపయోగించబడుతుంది.
            </label>
          </div>
        </div>

        {/* Loading Spinner */}
        {isLoading && (
          <div className="py-8 text-center opacity-80">
            <span className="animate-spin inline-block text-2xl mr-2">⏳</span>
            <span className="text-lg font-bold">{t.verifyingEvidence}</span>
          </div>
        )}

        {/* Answer Display */}
        {answer && (
          <div
            className={`p-6 rounded-2xl border-2 ${
              highContrast
                ? "bg-zinc-900 border-yellow-400 text-yellow-300"
                : "bg-emerald-50/50 border-emerald-500/40 text-slate-900"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <span className="font-mono text-xs uppercase font-bold px-2.5 py-1 rounded-full bg-emerald-600 text-white">
                {answer.answer_status === "supported" ? "Verified Grounded Answer" : "Partial / Uncertain"}
              </span>

              {/* Speak Answer Button */}
              <button
                onClick={playAnswerAudio}
                className={`min-h-[44px] px-3.5 py-1.5 rounded-lg text-sm font-bold flex items-center gap-1.5 focus:ring-2 focus:ring-yellow-400 ${
                  highContrast
                    ? "bg-yellow-400 text-black"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                {isPlayingAudio ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                <span>{isPlayingAudio ? t.stop : t.listen}</span>
              </button>
            </div>

            <p className="text-lg sm:text-xl font-medium leading-relaxed mb-4">
              {answer.summary_text}
            </p>

            {/* Legal Out-of-bounds advice message */}
            {answer.action_advice && (
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500 text-amber-600 dark:text-amber-400 text-sm mb-4">
                <strong>గమనిక (Important Notice): </strong> {answer.action_advice}
              </div>
            )}

            {/* Evidence Claims */}
            {answer.claims && answer.claims.length > 0 && (
              <div className="space-y-3 pt-3 border-t border-slate-200/50">
                <h3 className="text-xs font-bold uppercase opacity-75">ఆధారాలు (Supporting Claims):</h3>
                {answer.claims.map((claim, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm sm:text-base">
                    <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-1" />
                    <span>{claim.claim_text}</span>
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

