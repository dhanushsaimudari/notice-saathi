"use client";

import React from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { Clock, HardDrive, Volume2, ArrowLeft, CheckCircle2, Lock } from "lucide-react";

export default function PrivacyPolicyPage() {
  const { highContrast, t } = useAccessibility();

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-sm";

  return (
    <div className="space-y-6 sm:space-y-8 py-2 sm:py-4 max-w-3xl mx-auto w-full">
      {/* Breadcrumbs */}
      <nav aria-label="Breadcrumb" className="text-sm font-medium opacity-80">
        <ol className="flex items-center gap-2 list-none p-0 m-0">
          <li>
            <Link href="/" className="hover:underline text-emerald-600 dark:text-emerald-400">
              {t.home}
            </Link>
          </li>
          <li>/</li>
          <li aria-current="page" className="font-bold">
            గోప్యతా విధానం (Privacy Policy)
          </li>
        </ol>
      </nav>

      {/* Back button */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px] text-base"
      >
        <ArrowLeft className="w-5 h-5 shrink-0" />
        <span>{t.home}</span>
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight break-words">
          గోప్యతా విధానం & డేటా రక్షణ (Privacy Policy & Data Protection)
        </h1>
        <p className="opacity-80 text-sm sm:text-base mt-2 leading-relaxed break-words">
          Designed in accordance with India&apos;s Digital Personal Data Protection (DPDP) Act, 2023 principles. NoticeSaathi adheres strictly to the principles of purpose limitation, data minimization, and evidence-first transparency.
        </p>
      </div>

      {/* Summary Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        <div className={`${cardBg} rounded-2xl p-4 sm:p-5 flex items-start gap-3`}>
          <div className="p-2.5 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold">Configurable Retention</h2>
            <p className="text-xs sm:text-sm opacity-80 mt-1">
              Production deployments feature automated retention workers configured to permanently purge notices, OCR extracts, and cached audio files.
            </p>
          </div>
        </div>

        <div className={`${cardBg} rounded-2xl p-4 sm:p-5 flex items-start gap-3`}>
          <div className="p-2.5 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold">Local OCR Processing</h2>
            <p className="text-xs sm:text-sm opacity-80 mt-1">
              Document image extraction and text parsing run strictly on local NoticeSaathi infrastructure. Your legal documents are never sent to third-party LLMs.
            </p>
          </div>
        </div>

        <div className={`${cardBg} rounded-2xl p-4 sm:p-5 flex items-start gap-3`}>
          <div className="p-2.5 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0">
            <Volume2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold">Explicit Voice Consent</h2>
            <p className="text-xs sm:text-sm opacity-80 mt-1">
              Microphone audio and speech playback interact with Gnani AI services only after you provide explicit affirmative consent.
            </p>
          </div>
        </div>

        <div className={`${cardBg} rounded-2xl p-4 sm:p-5 flex items-start gap-3`}>
          <div className="p-2.5 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold">Zero-PII Audit Ledger</h2>
            <p className="text-xs sm:text-sm opacity-80 mt-1">
              When documents are purged, all personal details and document pages are deleted. Only an anonymous cryptographic timestamp is retained for audit.
            </p>
          </div>
        </div>
      </div>

      {/* Detailed Policy Sections */}
      <div className={`${cardBg} rounded-2xl sm:rounded-3xl p-5 sm:p-8 space-y-6 sm:space-y-8`}>
        {/* Section 1 */}
        <section className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>1. Data We Collect and Why (సేకరించే సమాచారం)</span>
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed">
            NoticeSaathi collects only the documents you choose to upload (Property Tax notices, court summons, utility bills) and, optionally, your voice questions. This data is collected solely for the purpose of identifying key dates, required payments, actions, and consequences stated on the face of the document.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>2. Local Processing Boundary (స్థానిక ప్రాసెసింగ్ పరిమితి)</span>
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed">
            All Optical Character Recognition (OCR), entity normalization, and fact verification are executed entirely on our secured local backend. We do not transmit notice images or extracted full-text documents to general-purpose cloud AI APIs.
          </p>
        </section>

        {/* Section 3 */}
        <section className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>3. Third-Party Voice Processing (Gnani AI STT &amp; TTS)</span>
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed">
            If you enable voice features, NoticeSaathi connects to Gnani.ai for Speech-to-Text (Prisma) and Text-to-Speech (Timbre). This occurs only after you check the affirmative consent box. Audio recordings are transmitted via secure HTTPS and are not retained by NoticeSaathi beyond the active session.
          </p>
        </section>

        {/* Section 4 */}
        <section className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>4. Automated Retention &amp; Deletion (డేటా తొలగింపు)</span>
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed">
            In production deployments, NoticeSaathi includes a containerized background retention worker configured to purge documents, OCR extracts, and cached audio files past the configured retention window (default 48 hours). In addition, on-demand physical purging is supported immediately via the user interface.
          </p>
        </section>

        {/* Section 5 */}
        <section className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>5. Your Rights as a Data Principal (మీ హక్కులు)</span>
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed">
            You retain full ownership of your data at all times. You have the right to immediately delete any document at any moment using the red &ldquo;Delete Document&rdquo; button on the document screen. This triggers an immediate, synchronous purge of all related assets.
          </p>
        </section>
      </div>
    </div>
  );
}
