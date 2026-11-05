"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, DocumentSummary } from "@/lib/api";
import { ArrowLeft, Trash2, FileText, ArrowRight, Settings, ShieldCheck } from "lucide-react";

export default function HistoryPage() {
  const { t, language, setLanguage, textSize, setTextSize, highContrast, setHighContrast } = useAccessibility();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Deletion modal
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  useEffect(() => {
    loadDocs();
  }, []);

  async function loadDocs() {
    try {
      setLoading(true);
      const docs = await api.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to load documents", err);
    } finally {
      setLoading(false);
    }
  }

  const handleDelete = async () => {
    if (!deleteTargetId) return;
    try {
      setIsDeleting(true);
      await api.deleteDocument(deleteTargetId);
      setDeleteTargetId(null);
      await loadDocs();
    } catch (err) {
      console.error("Deletion failed", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-sm";

  return (
    <div className="space-y-8 py-4 max-w-3xl mx-auto">
      {/* Back button */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px]"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>{t.home}</span>
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold">{t.history}</h1>
        <p className="opacity-80 text-base mt-1">
          మీ ఇటీవలి పత్రాలు మరియు గోప్యతా సెట్టింగ్‌లు (Manage your documents and privacy).
        </p>
      </div>

      {/* Document History List */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <FileText className="w-5 h-5" />
          <span>{t.recentDocs}</span>
        </h2>

        {loading ? (
          <div className="py-8 text-center opacity-75">
            <span className="animate-spin inline-block mr-2">⏳</span> Loading...
          </div>
        ) : documents.length === 0 ? (
          <div className={`${cardBg} rounded-2xl p-8 text-center opacity-80`}>
            <p className="text-lg">{t.noRecentDocs}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.document_id}
                className={`${cardBg} p-4 sm:p-5 rounded-2xl flex items-center justify-between gap-4`}
              >
                <Link
                  href={`/documents/${doc.document_id}`}
                  className="flex items-center gap-3 flex-1 focus:ring-2 focus:ring-yellow-400 rounded-lg p-1"
                >
                  <div className="p-3 bg-emerald-600/10 text-emerald-600 rounded-xl shrink-0">
                    <FileText className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg line-clamp-1">{doc.original_filename}</h3>
                    <div className="flex items-center gap-2 text-xs opacity-75 font-mono mt-0.5">
                      <span>{doc.page_count} page(s)</span>
                      <span>•</span>
                      <span className="capitalize">{doc.state.toLowerCase()}</span>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/documents/${doc.document_id}`}
                    className="p-2.5 min-h-[48px] min-w-[48px] rounded-xl hover:bg-slate-100 flex items-center justify-center focus:ring-2 focus:ring-yellow-400"
                    aria-label="View document"
                  >
                    <ArrowRight className="w-5 h-5" />
                  </Link>

                  <button
                    onClick={() => setDeleteTargetId(doc.document_id)}
                    className="p-2.5 min-h-[48px] min-w-[48px] rounded-xl text-rose-500 hover:bg-rose-500/10 flex items-center justify-center focus:ring-2 focus:ring-yellow-400"
                    aria-label={`Delete ${doc.original_filename}`}
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Accessibility & Privacy Preferences Card */}
      <section className={`${cardBg} rounded-3xl p-6 sm:p-7 space-y-6`}>
        <div className="flex items-center gap-2 font-bold text-xl pb-2 border-b border-slate-200/50">
          <Settings className="w-6 h-6" />
          <span>{t.settings} & Accessibility</span>
        </div>

        {/* Text Size Setting */}
        <div>
          <label className="block font-bold mb-2">{t.textLarge}:</label>
          <div className="flex flex-wrap gap-2">
            {[
              { id: "normal", label: "Normal (సాధారణం)" },
              { id: "large", label: "Large (పెద్దది)" },
              { id: "extra-large", label: "Extra Large (చాలా పెద్దది)" },
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => setTextSize(opt.id as any)}
                className={`min-h-[48px] px-4 py-2 rounded-xl font-bold border focus:ring-4 focus:ring-yellow-400 ${
                  textSize === opt.id
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-800 border-slate-300"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* High Contrast Setting */}
        <div>
          <label className="block font-bold mb-2">{t.contrastHigh}:</label>
          <button
            onClick={() => setHighContrast(!highContrast)}
            className={`min-h-[48px] px-5 py-2.5 rounded-xl font-bold border focus:ring-4 focus:ring-yellow-400 ${
              highContrast
                ? "bg-yellow-400 text-black border-yellow-400"
                : "bg-slate-100 text-slate-800 border-slate-300"
            }`}
          >
            {highContrast ? "High Contrast Enabled" : "High Contrast Disabled"}
          </button>
        </div>

        {/* Retention Policy Statement */}
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-sm opacity-85">
          <div className="font-bold mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Data Retention Policy</span>
          </div>
          Uploaded files and derived action cards are stored privately with end-to-end user isolation. You can permanently delete any document at any time using the delete button, which purges the original file, text blocks, and cached audio.
        </div>
      </section>

      {/* Delete Confirmation Modal */}
      {deleteTargetId && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className={`${cardBg} rounded-2xl max-w-md w-full p-6 space-y-4`}>
            <div className="flex items-center gap-3 text-rose-500">
              <Trash2 className="w-7 h-7" />
              <h2 className="text-xl font-bold">{t.deleteDoc}</h2>
            </div>
            <p className="text-base leading-relaxed">{t.deleteConfirm}</p>

            <div className="flex items-center justify-end gap-3 pt-3">
              <button
                onClick={() => setDeleteTargetId(null)}
                className="min-h-[48px] px-4 py-2 rounded-xl font-bold border border-slate-300 hover:bg-slate-100"
              >
                {t.cancel}
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="min-h-[48px] px-5 py-2 rounded-xl font-bold bg-rose-600 hover:bg-rose-700 text-white focus:ring-4 focus:ring-yellow-400"
              >
                {isDeleting ? "Deleting..." : t.confirmDelete}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

