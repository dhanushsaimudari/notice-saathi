"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { api, ActionCardData } from "@/lib/api";
import ActionCardComponent from "@/components/ActionCardComponent";
import ProofModal from "@/components/ProofModal";
import { ArrowLeft, MessageSquare, Trash2, AlertTriangle, ShieldAlert } from "lucide-react";

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
    <div className="space-y-6 py-4">
      {/* Top Navigation & Action Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px]"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>{t.home}</span>
        </Link>

        <div className="flex items-center gap-2">
          {/* Ask Question Button */}
          <Link
            href={`/documents/${documentId}/ask`}
            className={`min-h-[48px] px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 focus:ring-4 focus:ring-yellow-400 ${
              highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
            }`}
          >
            <MessageSquare className="w-5 h-5" />
            <span>{t.askQuestion}</span>
          </Link>

          {/* Delete Button */}
          <button
            onClick={() => setIsDeleteOpen(true)}
            className="min-h-[48px] px-4 py-2.5 rounded-xl font-bold border-2 border-rose-500/40 text-rose-500 hover:bg-rose-500/10 flex items-center gap-2 focus:ring-4 focus:ring-yellow-400"
            aria-label={t.deleteDoc}
          >
            <Trash2 className="w-5 h-5" />
            <span className="hidden sm:inline">{t.deleteDoc}</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="py-20 text-center opacity-75">
          <span className="animate-spin inline-block mr-2 text-2xl">⏳</span>
          <p className="text-lg font-bold mt-2">{t.processing}</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border-2 border-rose-500 text-rose-500 space-y-3">
          <p className="text-lg font-bold">{error}</p>
          <Link href="/" className="inline-block underline font-bold">
            Back to Home
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200/50">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold">{t.actionCardsTitle}</h1>
              <p className="text-sm opacity-75 mt-1">
                Every statement below is grounded in actual text extracted from your document.
              </p>
            </div>
          </div>

          {/* Action Cards List */}
          <div className="space-y-6">
            {cards.map((card) => (
              <ActionCardComponent key={card.card_id} card={card} onViewProof={openProof} />
            ))}
          </div>

          {/* Follow-up question banner */}
          <div className={`${cardBg} rounded-2xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4`}>
            <div>
              <h2 className="text-xl font-bold">ఈ పత్రం గురించి మరింత సమాచారం కావాలా?</h2>
              <p className="text-sm opacity-80 mt-1">
                మీరు మాట్లాడి లేదా టైప్ చేసి ఏ ప్రశ్నించినా, పత్రం ఆధారంగా సమాధానం ఇస్తాము.
              </p>
            </div>
            <Link
              href={`/documents/${documentId}/ask`}
              className={`min-h-[50px] px-6 py-3 rounded-xl font-bold flex items-center gap-2 whitespace-nowrap focus:ring-4 focus:ring-yellow-400 ${
                highContrast
                  ? "bg-yellow-400 text-black hover:bg-yellow-300"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
              }`}
            >
              <MessageSquare className="w-5 h-5" />
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
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className={`${cardBg} rounded-2xl max-w-md w-full p-6 space-y-4`}>
            <div className="flex items-center gap-3 text-rose-500">
              <ShieldAlert className="w-7 h-7" />
              <h2 className="text-xl font-bold">{t.deleteDoc}</h2>
            </div>
            <p className="text-base leading-relaxed">{t.deleteConfirm}</p>
            <p className="text-xs opacity-75">
              The original file, extracted text blocks, facts, and audio caches will be permanently erased.
            </p>

            <div className="flex items-center justify-end gap-3 pt-3">
              <button
                onClick={() => setIsDeleteOpen(false)}
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

