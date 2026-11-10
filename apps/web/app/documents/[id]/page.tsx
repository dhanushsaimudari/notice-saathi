"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, ActionCardData } from "@/lib/api";
import ActionCardComponent from "@/components/ActionCardComponent";
import ProofModal from "@/components/ProofModal";
import { ArrowLeft, MessageSquare, Trash2, ShieldAlert } from "lucide-react";

export default function DocumentDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;
  const { t, highContrast } = useAccessibility();

  const [cards, setCards] = useState<ActionCardData[]>([]);
  const [docState, setDocState] = useState<string>("LOADING");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Proof Modal state
  const [isProofOpen, setIsProofOpen] = useState<boolean>(false);
  const [selectedProofRefs, setSelectedProofRefs] = useState<any[]>([]);

  // Delete modal state
  const [isDeleteOpen, setIsDeleteOpen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  useEffect(() => {
    async function loadCards() {
      try {
        const res = await api.getActionCards(documentId);
        setCards(res.cards || []);
        setDocState(res.document_state);
      } catch (err: any) {
        setError(err.message || "Failed to load document analysis.");
      } finally {
        setLoading(false);
      }
    }
    loadCards();
  }, [documentId]);

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      await api.deleteDocument(documentId);
      router.push("/");
    } catch (err) {
      console.error("Deletion failed", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const openProof = (refs: any[]) => {
    setSelectedProofRefs(refs);
    setIsProofOpen(true);
  };

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-sm";

  return (
    <div className="space-y-5 sm:space-y-6 py-2 sm:py-4 w-full">
      {/* Top Navigation & Action Row */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 sm:gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px] text-base"
        >
          <ArrowLeft className="w-5 h-5 shrink-0" />
          <span>{t.home}</span>
        </Link>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Ask Question Button */}
          <Link
            href={`/documents/${documentId}/ask`}
            className={`min-h-[48px] px-4 sm:px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 text-sm sm:text-base transition-colors ${
              highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
            }`}
          >
            <MessageSquare className="w-5 h-5 shrink-0" />
            <span>{t.askQuestion}</span>
          </Link>

          {/* Delete Button */}
          <button
            onClick={() => setIsDeleteOpen(true)}
            className="min-h-[48px] px-3.5 sm:px-4 py-2.5 rounded-xl font-bold border-2 border-rose-500/40 text-rose-500 hover:bg-rose-500/10 flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 text-sm sm:text-base transition-colors"
            aria-label={t.deleteDoc}
          >
            <Trash2 className="w-5 h-5 shrink-0" />
            <span className="hidden sm:inline">{t.deleteDoc}</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="py-16 sm:py-20 text-center opacity-75">
          <span className="animate-spin inline-block mr-2 text-2xl">⏳</span>
          <p className="text-base sm:text-lg font-bold mt-2">{t.processing}</p>
        </div>
      ) : error ? (
        <div className="p-5 sm:p-6 rounded-2xl bg-rose-500/10 border-2 border-rose-500 text-rose-500 space-y-3">
          <p className="text-base sm:text-lg font-bold break-words">{error}</p>
          <Link href="/" className="inline-block underline font-bold">
            Back to Home
          </Link>
        </div>
      ) : (
        <div className="space-y-5 sm:space-y-6">
          <div className="pb-2 border-b border-slate-200/50 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold break-words">{t.actionCardsTitle}</h1>
              <p className="text-xs sm:text-sm opacity-75 mt-1 leading-relaxed break-words">
                Every statement below is grounded in actual text extracted from your document.
              </p>
            </div>
            {docState && docState !== "LOADING" && (
              <span className="font-mono text-xs uppercase font-bold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300">
                {docState}
              </span>
            )}
          </div>

          {/* Action Cards List */}
          <div className="space-y-4 sm:space-y-6">
            {cards.map((card) => (
              <ActionCardComponent key={card.card_id} card={card} onViewProof={openProof} />
            ))}
          </div>

          {/* Follow-up question banner */}
          <div className={`${cardBg} rounded-2xl p-4 sm:p-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4`}>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg sm:text-xl font-bold break-words">ఈ పత్రం గురించి మరింత సమాచారం కావాలా?</h2>
              <p className="text-xs sm:text-sm opacity-80 mt-1 leading-relaxed break-words">
                మీరు మాట్లాడి లేదా టైప్ చేసి ఏ ప్రశ్నించినా, పత్రం ఆధారంగా సమాధానం ఇస్తాము.
              </p>
            </div>
            <Link
              href={`/documents/${documentId}/ask`}
              className={`min-h-[48px] sm:min-h-[50px] px-5 sm:px-6 py-2.5 sm:py-3 rounded-xl font-bold flex items-center justify-center gap-2 shrink-0 focus:ring-4 focus:ring-yellow-400 text-center transition-colors ${
                highContrast
                  ? "bg-yellow-400 text-black hover:bg-yellow-300"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
              }`}
            >
              <MessageSquare className="w-5 h-5 shrink-0" />
              <span>{t.askQuestion}</span>
            </Link>
          </div>
        </div>
      )}

      {/* Proof Viewer Modal */}
      <ProofModal
        isOpen={isProofOpen}
        onClose={() => setIsProofOpen(false)}
        proofRefs={selectedProofRefs}
      />

      {/* Deletion Confirmation Dialogue */}
      {isDeleteOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
          <div className={`${cardBg} rounded-2xl max-w-md w-full p-5 sm:p-6 space-y-4 mx-auto`}>
            <div className="flex items-center gap-3 text-rose-500">
              <ShieldAlert className="w-6 h-6 sm:w-7 sm:h-7 shrink-0" />
              <h2 className="text-lg sm:text-xl font-bold">{t.deleteDoc}</h2>
            </div>
            <p className="text-sm sm:text-base leading-relaxed break-words">{t.deleteConfirm}</p>
            <p className="text-xs opacity-75 leading-relaxed">
              The original file, extracted text blocks, facts, and audio caches will be permanently erased.
            </p>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5 sm:gap-3 pt-3">
              <button
                onClick={() => setIsDeleteOpen(false)}
                className="min-h-[48px] px-4 py-2.5 rounded-xl font-bold border border-slate-300 hover:bg-slate-100 dark:hover:bg-zinc-800 text-sm sm:text-base"
              >
                {t.cancel}
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="min-h-[48px] px-5 py-2.5 rounded-xl font-bold bg-rose-600 hover:bg-rose-700 text-white focus:ring-4 focus:ring-yellow-400 text-sm sm:text-base"
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
