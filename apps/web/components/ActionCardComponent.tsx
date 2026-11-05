"use client";

import React, { useState, useRef } from "react";
import { ActionCardData, api } from "@/lib/api";
import { useAccessibility } from "@/lib/accessibility";
import { Volume2, VolumeX, RotateCcw, AlertTriangle, CheckCircle2, FileSearch, HelpCircle } from "lucide-react";

interface ActionCardProps {
  card: ActionCardData;
  onViewProof?: (refs: any[]) => void;
}

export default function ActionCardComponent({ card, onViewProof }: ActionCardProps) {
  const { language, highContrast, t } = useAccessibility();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isConflicting = card.status === "conflicting" || card.status === "conflicting_action";
  const isPageUnreadable = card.status === "relevant_page_unreadable" || card.status === "partially_unreadable";
  const isNoAction = card.status === "no_action_found" || card.status === "action_not_identified_in_readable_text";
  const isUncertain = card.status === "uncertain" || Boolean(card.uncertainty && !isConflicting && !isPageUnreadable);
  const isSuccess = (card.status === "action_identified" || card.status === "supported") && !card.uncertainty && !isConflicting && !isPageUnreadable;

  const cardBorder = isConflicting
    ? "border-rose-500"
    : isPageUnreadable || isUncertain
    ? "border-amber-500"
    : isNoAction
    ? "border-slate-400"
    : "border-slate-200";

  const cardStyle = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : `bg-white border-2 ${cardBorder} text-slate-900 shadow-md`;

  const excerptStyle = highContrast
    ? "bg-zinc-900 border-l-4 border-yellow-400 text-white"
    : "bg-slate-50 border-l-4 border-indigo-600 text-slate-800";

  const meansStyle = highContrast
    ? "bg-zinc-900 border-l-4 border-emerald-400 text-emerald-200"
    : "bg-emerald-50 border-l-4 border-emerald-600 text-emerald-950";

  const actionStyle = highContrast
    ? "bg-zinc-900 border-l-4 border-blue-400 text-blue-200"
    : "bg-blue-50 border-l-4 border-blue-600 text-blue-950";

  const uncertainStyle = highContrast
    ? "bg-zinc-900 border-l-4 border-amber-400 text-amber-300"
    : isConflicting
    ? "bg-rose-50 border-l-4 border-rose-600 text-rose-950"
    : "bg-amber-50 border-l-4 border-amber-600 text-amber-950";

  const playSpeech = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }

    try {
      setIsLoadingAudio(true);
      let url = audioUrl;
      if (!url) {
        // Synthesize text: Use approved spoken output if present, else combined means + action
        const spokenText = card.approved_spoken_output || `${card.what_means} ${card.what_action}`;
        url = await api.synthesizeSpeech(spokenText, language, speechSpeed);
        setAudioUrl(url);
      }

      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.playbackRate = speechSpeed;
        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (err) {
      console.error("Audio playback error:", err);
    } finally {
      setIsLoadingAudio(false);
    }
  };

  const handleSpeedChange = (speed: number) => {
    setSpeechSpeed(speed);
    if (audioRef.current) {
      audioRef.current.playbackRate = speed;
    }
  };

  return (
    <div className={`${cardStyle} rounded-2xl p-6 sm:p-7 mb-6 transition-all`} role="region" aria-label={card.title}>
      {/* Hidden HTML5 Audio Element */}
      <audio
        ref={audioRef}
        onEnded={() => setIsPlaying(false)}
        onError={() => setIsPlaying(false)}
        className="hidden"
      />

      {/* Header and Voice Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200/50">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl text-white flex items-center justify-center ${
            isConflicting
              ? "bg-rose-600"
              : isPageUnreadable || isUncertain
              ? "bg-amber-600"
              : isNoAction
              ? "bg-slate-600"
              : "bg-emerald-600"
          }`}>
            {isSuccess ? <CheckCircle2 className="w-6 h-6" /> : isNoAction ? <HelpCircle className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight">{card.title}</h2>
            <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-md mt-1 ${
              isConflicting
                ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                : isPageUnreadable
                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                : isUncertain
                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                : isNoAction
                ? "bg-slate-100 text-slate-800 dark:bg-zinc-800 dark:text-zinc-300"
                : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
            }`}>
              {isConflicting
                ? "Conflicting Action / పరస్పర విరుద్ధం"
                : isPageUnreadable
                ? "Page Unreadable / పేజీ అస్పష్టంగా ఉంది"
                : isUncertain
                ? "Uncertain Action / అస్పష్టం"
                : isNoAction
                ? "No Action Found / నిర్దిష్ట చర్య లేదు"
                : "Verified Action / ధ్రువీకరించబడిన సమాచారం"}
            </span>
          </div>
        </div>

        {/* Audio Controls */}
        <div className="flex items-center flex-wrap gap-2">
          <button
            onClick={playSpeech}
            disabled={isLoadingAudio}
            className={`min-h-[48px] px-4 py-2.5 rounded-xl font-bold flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 transition-all ${
              highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-emerald-600 hover:bg-emerald-700 text-white"
            }`}
            aria-label={isPlaying ? t.stop : t.listen}
          >
            {isLoadingAudio ? (
              <span className="animate-spin">⏳</span>
            ) : isPlaying ? (
              <VolumeX className="w-5 h-5" />
            ) : (
              <Volume2 className="w-5 h-5" />
            )}
            <span>{isLoadingAudio ? "Loading..." : isPlaying ? t.stop : t.listen}</span>
          </button>

          {/* Speed Selector */}
          <div className="flex items-center rounded-lg border border-slate-300 overflow-hidden min-h-[48px] text-xs font-bold">
            {[0.85, 1.0, 1.15].map((s) => (
              <button
                key={s}
                onClick={() => handleSpeedChange(s)}
                className={`px-2.5 py-2 min-h-[48px] focus:ring-2 focus:ring-yellow-400 ${
                  speechSpeed === s
                    ? highContrast
                      ? "bg-yellow-400 text-black"
                      : "bg-slate-800 text-white"
                    : highContrast
                    ? "bg-zinc-900 text-yellow-300"
                    : "bg-slate-100 text-slate-700"
                }`}
                title={`Speed ${s}x`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Section 1: What it says (Exact original excerpt) */}
      <div className="mt-5">
        <h3 className="text-sm sm:text-base font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5 opacity-90">
          <span>{t.whatItSays}</span>
        </h3>
        <div className={`${excerptStyle} p-4 rounded-xl text-base sm:text-lg font-serif italic`}>
          "{card.what_says}"
        </div>
      </div>

      {/* Section 2: What it means (Simple explanation) */}
      <div className="mt-5">
        <h3 className="text-sm sm:text-base font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5 opacity-90">
          <span>{t.whatItMeans}</span>
        </h3>
        <div className={`${meansStyle} p-4 rounded-xl text-base sm:text-lg font-medium leading-relaxed`}>
          {card.what_means}
        </div>
      </div>

      {/* Section 3: What to do next (Explicit action only) */}
      <div className="mt-5">
        <h3 className="text-sm sm:text-base font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5 opacity-90">
          <span>{t.whatToDo}</span>
        </h3>
        <div className={`${actionStyle} p-4 rounded-xl text-base sm:text-lg font-bold leading-relaxed`}>
          {card.what_action}
        </div>
      </div>

      {/* Section 4: What is uncertain (if any) */}
      {card.uncertainty && (
        <div className="mt-5">
          <h3 className="text-sm sm:text-base font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5 text-amber-500">
            <AlertTriangle className="w-5 h-5" />
            <span>{t.whatIsUncertain}</span>
          </h3>
          <div className={`${uncertainStyle} p-4 rounded-xl text-base sm:text-lg font-medium`}>
            {card.uncertainty}
          </div>
        </div>
      )}

      {/* Section 5: Proof Link / Button */}
      {card.proof_refs && card.proof_refs.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-200/50 flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={() => onViewProof && onViewProof(card.proof_refs)}
            className={`min-h-[48px] px-4 py-2.5 rounded-xl font-bold flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 ${
              highContrast
                ? "bg-zinc-900 border-2 border-yellow-400 text-yellow-300 hover:bg-zinc-800"
                : "bg-indigo-50 hover:bg-indigo-100 text-indigo-900 border border-indigo-200"
            }`}
          >
            <FileSearch className="w-5 h-5 text-indigo-600" />
            <span>{t.viewProof}</span>
          </button>

          <span className="text-xs sm:text-sm opacity-75 font-mono">
            {card.proof_refs.length} verified evidence block(s)
          </span>
        </div>
      )}
    </div>
  );
}

