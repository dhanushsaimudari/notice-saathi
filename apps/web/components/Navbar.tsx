"use client";

import React from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { SupportedLanguage } from "@/lib/i18n";
import { FileText, History, SunMedium, Moon } from "lucide-react";

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
    <header className={`${headerBg} sticky top-0 z-50 px-3 py-2.5 sm:px-6 sm:py-3 transition-colors`}>
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 sm:gap-3">
        {/* Top bar on mobile: Logo + Quick actions (Contrast & History) */}
        <div className="flex items-center justify-between gap-2 w-full sm:w-auto">
          {/* App Title / Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 rounded-md p-1 font-bold text-lg sm:text-2xl tracking-tight min-w-0"
            aria-label={t.appName}
          >
            <div className="bg-emerald-600 text-white p-1.5 sm:p-2 rounded-lg flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <span className="truncate">{t.appName}</span>
          </Link>

          {/* Mobile-visible right actions: High Contrast and History */}
          <div className="flex items-center gap-1.5 sm:hidden shrink-0">
            <button
              onClick={() => setHighContrast(!highContrast)}
              className={`${btnBg} font-bold rounded-lg p-2.5 flex items-center justify-center min-h-[44px] min-w-[44px] focus:ring-4 focus:ring-yellow-400`}
              aria-label={highContrast ? "Disable high contrast" : "Enable high contrast"}
              title={t.contrastHigh}
            >
              {highContrast ? <SunMedium className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            <Link
              href="/history"
              className={`${btnBg} rounded-lg p-2.5 flex items-center justify-center min-h-[44px] min-w-[44px] focus:ring-4 focus:ring-yellow-400 font-medium`}
              aria-label={t.history}
              title={t.history}
            >
              <History className="w-5 h-5" />
            </Link>
          </div>
        </div>

        {/* Accessibility & Language Controls */}
        <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto flex-wrap sm:flex-nowrap">
          {/* Language Selector */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className={`${btnBg} font-medium rounded-lg px-2 sm:px-3 py-2 text-sm sm:text-base min-h-[48px] focus:ring-4 focus:ring-yellow-400 cursor-pointer flex-1 sm:flex-initial min-w-[110px] max-w-[160px] sm:max-w-none truncate`}
            aria-label="Select preferred language"
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code} className="text-black bg-white">
                {l.label}
              </option>
            ))}
          </select>

          {/* Text Size Controls (A / A+ / A++) */}
          <div
            className="flex items-center rounded-lg border border-slate-300 dark:border-zinc-700 overflow-hidden min-h-[48px] shrink-0"
            role="group"
            aria-label="Text size options"
          >
            <button
              onClick={() => setTextSize("normal")}
              className={`px-2.5 sm:px-3 py-2 text-sm font-bold min-h-[48px] min-w-[38px] sm:min-w-[40px] focus:ring-2 focus:ring-yellow-400 transition-colors ${
                textSize === "normal"
                  ? highContrast
                    ? "bg-yellow-400 text-black"
                    : "bg-emerald-600 text-white"
                  : btnBg
              }`}
              title="Normal text (16px base)"
              aria-label="Set normal text size"
              aria-pressed={textSize === "normal"}
            >
              A
            </button>
            <button
              onClick={() => setTextSize("large")}
              className={`px-2.5 sm:px-3 py-2 text-base font-bold min-h-[48px] min-w-[38px] sm:min-w-[40px] border-x border-slate-300 dark:border-zinc-700 focus:ring-2 focus:ring-yellow-400 transition-colors ${
                textSize === "large"
                  ? highContrast
                    ? "bg-yellow-400 text-black"
                    : "bg-emerald-600 text-white"
                  : btnBg
              }`}
              title="Large text (19px base)"
              aria-label="Set large text size"
              aria-pressed={textSize === "large"}
            >
              A+
            </button>
            <button
              onClick={() => setTextSize("extra-large")}
              className={`px-2.5 sm:px-3 py-2 text-lg font-bold min-h-[48px] min-w-[42px] sm:min-w-[44px] focus:ring-2 focus:ring-yellow-400 transition-colors ${
                textSize === "extra-large"
                  ? highContrast
                    ? "bg-yellow-400 text-black"
                    : "bg-emerald-600 text-white"
                  : btnBg
              }`}
              title="Extra large text (22px base)"
              aria-label="Set extra large text size"
              aria-pressed={textSize === "extra-large"}
            >
              A++
            </button>
          </div>

          {/* Desktop-only High Contrast Toggle & History link */}
          <div className="hidden sm:flex items-center gap-2 shrink-0">
            <button
              onClick={() => setHighContrast(!highContrast)}
              className={`${btnBg} font-bold rounded-lg px-3 py-2 flex items-center gap-1.5 min-h-[48px] focus:ring-4 focus:ring-yellow-400`}
              aria-label={highContrast ? "Disable high contrast" : "Enable high contrast"}
              title={t.contrastHigh}
            >
              {highContrast ? <SunMedium className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              <span className="hidden md:inline text-xs sm:text-sm">{highContrast ? "Normal" : "High Contrast"}</span>
            </button>

            <Link
              href="/history"
              className={`${btnBg} rounded-lg px-3 py-2 flex items-center gap-1.5 min-h-[48px] focus:ring-4 focus:ring-yellow-400 font-medium`}
              aria-label={t.history}
            >
              <History className="w-5 h-5" />
              <span className="hidden md:inline text-xs sm:text-sm">{t.history}</span>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
