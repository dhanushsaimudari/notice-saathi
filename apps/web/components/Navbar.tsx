"use client";

import React from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { SupportedLanguage } from "@/lib/i18n";
import { Eye, Volume2, ShieldCheck, FileText, Home, History, SunMedium, Moon } from "lucide-react";

export default function Navbar() {
  const { language, setLanguage, textSize, setTextSize, highContrast, setHighContrast, t } = useAccessibility();

  const languages: { code: SupportedLanguage; label: string }[] = [
    { code: "te-IN", label: "తెలుగు (Telugu)" },
    { code: "en-IN", label: "English" },
    { code: "hi-IN", label: "हिन्दी (Hindi)" },
    { code: "ta-IN", label: "தமிழ் (Tamil)" },
    { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)" }
  ];

  const headerBg = highContrast
    ? "bg-black border-b-2 border-yellow-400 text-yellow-300"
    : "bg-white border-b border-slate-200 text-slate-900 shadow-sm";

  const btnBg = highContrast
    ? "bg-zinc-900 border-2 border-yellow-400 text-yellow-300 hover:bg-zinc-800"
    : "bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300";

  return (
    <header className={`${headerBg} sticky top-0 z-50 px-4 py-3 sm:px-6`}>
      <div className="max-w-5xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* App Title / Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 rounded-md p-1 font-bold text-xl sm:text-2xl tracking-tight"
          aria-label={t.appName}
        >
          <div className="bg-emerald-600 text-white p-2 rounded-lg flex items-center justify-center">
            <FileText className="w-6 h-6" />
          </div>
          <span>{t.appName}</span>
        </Link>

        {/* Accessibility & Language Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Language Selector */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className={`${btnBg} font-medium rounded-lg px-3 py-2 text-base min-h-[48px] focus:ring-4 focus:ring-yellow-400 cursor-pointer`}
            aria-label="Select preferred language"
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code} className="text-black bg-white">
                {l.label}
              </option>
            ))}
          </select>

          {/* Text Size Controls */}
          <div className="flex items-center rounded-lg border border-slate-300 overflow-hidden min-h-[48px]">
            <button
              onClick={() => setTextSize("normal")}
              className={`px-3 py-2 text-sm font-bold min-h-[48px] min-w-[40px] focus:ring-2 focus:ring-yellow-400 ${
                textSize === "normal" ? "bg-emerald-600 text-white" : btnBg
              }`}
              title="Normal text"
              aria-label="Set normal text size"
            >
              A
            </button>
            <button
              onClick={() => setTextSize("large")}
              className={`px-3 py-2 text-base font-bold min-h-[48px] min-w-[40px] focus:ring-2 focus:ring-yellow-400 ${
                textSize === "large" ? "bg-emerald-600 text-white" : btnBg
              }`}
              title="Large text"
              aria-label="Set large text size"
            >
              A+
            </button>
            <button
              onClick={() => setTextSize("extra-large")}
              className={`px-3 py-2 text-lg font-bold min-h-[48px] min-w-[44px] focus:ring-2 focus:ring-yellow-400 ${
                textSize === "extra-large" ? "bg-emerald-600 text-white" : btnBg
              }`}
              title="Extra large text"
              aria-label="Set extra large text size"
            >
              A++
            </button>
          </div>

          {/* High Contrast Toggle */}
          <button
            onClick={() => setHighContrast(!highContrast)}
            className={`${btnBg} font-bold rounded-lg px-3 py-2 flex items-center gap-1.5 min-h-[48px] focus:ring-4 focus:ring-yellow-400`}
            aria-label={highContrast ? "Disable high contrast" : "Enable high contrast"}
            title={t.contrastHigh}
          >
            {highContrast ? <SunMedium className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            <span className="hidden sm:inline text-sm">{highContrast ? "Normal" : "High Contrast"}</span>
          </button>

          {/* History Link */}
          <Link
            href="/history"
            className={`${btnBg} rounded-lg px-3 py-2 flex items-center gap-1.5 min-h-[48px] focus:ring-4 focus:ring-yellow-400 font-medium`}
            aria-label={t.history}
          >
            <History className="w-5 h-5" />
            <span className="hidden sm:inline text-sm">{t.history}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}

