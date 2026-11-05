"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, DocumentSummary } from "@/lib/api";
import { Camera, Upload, Shield, Clock, ArrowRight, FileText, CheckCircle2, AlertCircle } from "lucide-react";

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
    <div className="space-y-8 py-4">
      {/* Welcome Banner */}
      <section className={`${cardBg} rounded-3xl p-6 sm:p-10 text-center sm:text-left`}>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3">
          {t.appName}
        </h1>
        <p className="text-lg sm:text-xl opacity-90 max-w-2xl leading-relaxed">
          {t.tagline}
        </p>

        {/* Primary Action Buttons (WCAG 48px+ touch targets) */}
        <div className="mt-8 flex flex-col sm:flex-row gap-4 items-stretch sm:items-center">
          <Link
            href="/upload"
            className={`${primaryBtn} min-h-[56px] px-8 py-4 rounded-2xl flex items-center justify-center gap-3 text-lg sm:text-xl focus:ring-4 focus:ring-yellow-400 transition-all`}
          >
            <Camera className="w-7 h-7" />
            <span>{t.takePhoto}</span>
          </Link>

          <Link
            href="/upload"
            className={`${secondaryBtn} min-h-[56px] px-8 py-4 rounded-2xl flex items-center justify-center gap-3 text-lg sm:text-xl focus:ring-4 focus:ring-yellow-400 transition-all`}
          >
            <Upload className="w-7 h-7 text-emerald-600" />
            <span>{t.uploadDoc}</span>
          </Link>
        </div>
      </section>

      {/* Privacy & Safety Promise Card */}
      <section
        className={`${cardBg} rounded-2xl p-5 flex items-start gap-4 border-l-8 ${
          highContrast ? "border-yellow-400" : "border-emerald-600"
        }`}
      >
        <div className="p-3 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0 mt-0.5">
          <Shield className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold mb-1">మీ గోప్యత & భద్రత (Privacy Guaranteed)</h2>
          <p className="text-base opacity-85 leading-relaxed">{t.privacyNotice}</p>
        </div>
      </section>

      {/* Recent Documents Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Clock className="w-6 h-6" />
            <span>{t.recentDocs}</span>
          </h2>
          {documents.length > 0 && (
            <Link
              href="/history"
              className="text-base font-bold text-emerald-600 hover:underline flex items-center gap-1 focus:ring-2 focus:ring-yellow-400 rounded p-1"
            >
              <span>అన్నీ చూడండి (View All)</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>

        {loading ? (
          <div className="text-center py-10 opacity-75">
            <span className="animate-spin inline-block mr-2">⏳</span>
            {t.processing}
          </div>
        ) : documents.length === 0 ? (
          <div className={`${cardBg} rounded-2xl p-8 text-center opacity-80`}>
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg">{t.noRecentDocs}</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {documents.slice(0, 4).map((doc) => (
              <Link
                key={doc.document_id}
                href={`/documents/${doc.document_id}`}
                className={`${cardBg} p-5 rounded-2xl flex items-center justify-between hover:scale-[1.01] transition-all focus:ring-4 focus:ring-yellow-400`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-emerald-100 dark:bg-emerald-950 text-emerald-600 rounded-xl">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg line-clamp-1">{doc.original_filename}</h3>
                    <div className="flex items-center gap-2 text-xs opacity-75 mt-1 font-mono">
                      <span>{doc.page_count} page(s)</span>
                      <span>•</span>
                      <span className="capitalize">{doc.state.toLowerCase()}</span>
                    </div>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 shrink-0 opacity-70" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
