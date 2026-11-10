"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, DocumentSummary } from "@/lib/api";
import { Camera, Upload, Shield, Clock, ArrowRight, FileText } from "lucide-react";

export default function HomePage() {
  const { t, highContrast } = useAccessibility();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await api.listDocuments();
        setDocuments(docs);
      } catch (err) {
        console.error("Failed to load documents", err);
      } finally {
        setLoading(false);
      }
    }
    loadDocs();
  }, []);

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-sm";

  const primaryBtn = highContrast
    ? "bg-yellow-400 text-black hover:bg-yellow-300 border-2 border-yellow-400 font-bold"
    : "bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-md hover:shadow-lg";

  const secondaryBtn = highContrast
    ? "bg-zinc-900 text-yellow-300 hover:bg-zinc-800 border-2 border-yellow-400 font-bold"
    : "bg-white hover:bg-slate-100 text-slate-800 border border-slate-300 font-bold shadow-sm";

  return (
    <div className="space-y-6 sm:space-y-8 py-2 sm:py-4 w-full">
      {/* Welcome Banner */}
      <section className={`${cardBg} rounded-2xl sm:rounded-3xl p-5 sm:p-8 md:p-10 text-center sm:text-left`}>
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight mb-2.5 sm:mb-3 break-words">
          {t.appName}
        </h1>
        <p className="text-base sm:text-lg md:text-xl opacity-90 max-w-2xl leading-relaxed break-words">
          {t.tagline}
        </p>

        {/* Primary Action Buttons (WCAG touch targets: min 56px height, responsive stacking) */}
        <div className="mt-6 sm:mt-8 flex flex-col sm:flex-row gap-3 sm:gap-4 items-stretch sm:items-center">
          <Link
            href="/upload?pick=camera"
            className={`${primaryBtn} min-h-[56px] px-5 sm:px-8 py-3.5 sm:py-4 rounded-xl sm:rounded-2xl flex items-center justify-center gap-3 text-base sm:text-lg md:text-xl focus:ring-4 focus:ring-yellow-400 transition-all text-center`}
          >
            <Camera className="w-6 h-6 sm:w-7 sm:h-7 shrink-0" />
            <span className="break-words">{t.takePhoto}</span>
          </Link>

          <Link
            href="/upload?pick=file"
            className={`${secondaryBtn} min-h-[56px] px-5 sm:px-8 py-3.5 sm:py-4 rounded-xl sm:rounded-2xl flex items-center justify-center gap-3 text-base sm:text-lg md:text-xl focus:ring-4 focus:ring-yellow-400 transition-all text-center`}
          >
            <Upload className="w-6 h-6 sm:w-7 sm:h-7 text-emerald-600 shrink-0" />
            <span className="break-words">{t.uploadDoc}</span>
          </Link>
        </div>
      </section>

      {/* Privacy & Safety Promise Card */}
      <section
        className={`${cardBg} rounded-2xl p-4 sm:p-5 flex items-start gap-3 sm:gap-4 border-l-4 sm:border-l-8 ${
          highContrast ? "border-yellow-400" : "border-emerald-600"
        }`}
      >
        <div className="p-2 sm:p-2.5 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0 mt-0.5">
          <Shield className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-base sm:text-lg font-bold mb-1 break-words">
            మీ గోప్యత & భద్రత (Privacy Guaranteed)
          </h2>
          <p className="text-sm sm:text-base opacity-85 leading-relaxed break-words">
            {t.privacyNotice}
          </p>
        </div>
      </section>

      {/* Recent Documents Section */}
      <section className="space-y-3 sm:space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-2">
            <Clock className="w-5 h-5 sm:w-6 sm:h-6 shrink-0" />
            <span>{t.recentDocs}</span>
          </h2>
          {documents.length > 0 && (
            <Link
              href="/history"
              className="text-sm sm:text-base font-bold text-emerald-600 hover:underline flex items-center gap-1 focus:ring-2 focus:ring-yellow-400 rounded p-1"
            >
              <span>అన్నీ చూడండి (View All)</span>
              <ArrowRight className="w-4 h-4 shrink-0" />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="text-center py-10 opacity-75">
            <span className="animate-spin inline-block mr-2">⏳</span>
            {t.processing}
          </div>
        ) : documents.length === 0 ? (
          <div className={`${cardBg} rounded-2xl p-6 sm:p-8 text-center opacity-80`}>
            <FileText className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 opacity-50" />
            <p className="text-base sm:text-lg">{t.noRecentDocs}</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
            {documents.slice(0, 4).map((doc) => (
              <Link
                key={doc.document_id}
                href={`/documents/${doc.document_id}`}
                className={`${cardBg} p-4 sm:p-5 rounded-2xl flex items-center justify-between gap-3 hover:scale-[1.01] transition-all focus:ring-4 focus:ring-yellow-400 min-w-0`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="p-2.5 sm:p-3 bg-emerald-100 dark:bg-emerald-950 text-emerald-600 rounded-xl shrink-0">
                    <FileText className="w-5 h-5 sm:w-6 sm:h-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-bold text-base sm:text-lg truncate">{doc.original_filename}</h3>
                    <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs opacity-75 mt-0.5 font-mono">
                      <span>{doc.page_count} page(s)</span>
                      <span>•</span>
                      <span className="capitalize">{doc.state.toLowerCase()}</span>
                    </div>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 shrink-0 opacity-70 ml-1" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
