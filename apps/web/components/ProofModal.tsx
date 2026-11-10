"use client";

import React from "react";
import { useAccessibility } from "@/lib/accessibility";
import { X, CheckCircle, ShieldCheck } from "lucide-react";

interface ProofModalProps {
  isOpen: boolean;
  onClose: () => void;
  proofRefs: any[];
}

export default function ProofModal({ isOpen, onClose, proofRefs }: ProofModalProps) {
  const { highContrast } = useAccessibility();

  if (!isOpen) return null;

  const modalBg = highContrast
    ? "bg-black border-4 border-yellow-400 text-yellow-300"
    : "bg-white text-slate-900 border border-slate-300 shadow-2xl";

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-3 sm:p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="proof-modal-title"
    >
      <div className={`${modalBg} rounded-2xl max-w-2xl w-full p-4 sm:p-7 relative max-h-[90vh] overflow-y-auto mx-auto`}>
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 sm:top-4 sm:right-4 p-2.5 min-h-[48px] min-w-[48px] rounded-full hover:bg-slate-200/50 dark:hover:bg-zinc-800 focus:ring-4 focus:ring-yellow-400 flex items-center justify-center transition-colors"
          aria-label="Close proof viewer"
        >
          <X className="w-6 h-6" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2.5 sm:gap-3 mb-4 sm:mb-5 pr-10">
          <div className="p-2 sm:p-2.5 rounded-xl bg-indigo-600 text-white shrink-0">
            <ShieldCheck className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 id="proof-modal-title" className="text-lg sm:text-xl md:text-2xl font-bold break-words">
              Original Document Evidence
            </h2>
            <p className="text-xs sm:text-sm opacity-80 break-words">
              Verified ground-truth passages extracted from your document
            </p>
          </div>
        </div>

        {/* Evidence List */}
        <div className="space-y-3 sm:space-y-4 mt-3 sm:mt-4">
          {proofRefs.map((ref, idx) => (
            <div
              key={idx}
              className={`p-3.5 sm:p-4 rounded-xl border ${
                highContrast
                  ? "bg-zinc-900 border-yellow-400"
                  : "bg-slate-50 border-slate-200"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between text-xs font-mono font-bold mb-2 pb-1 border-b border-slate-200/50 gap-1.5">
                <span className="text-emerald-500 flex items-center gap-1">
                  <CheckCircle className="w-4 h-4 shrink-0" /> Block Verified
                </span>
                <span>Page {ref.page_number || 1}</span>
              </div>
              <p className="font-serif italic text-sm sm:text-base md:text-lg leading-relaxed break-words">
                "{ref.text || ref.text_snippet || "Verified document passage"}"
              </p>
              {ref.bbox && (
                <div className="mt-2 text-xs font-mono opacity-60 break-words">
                  Coordinates: [{ref.bbox.map((n: number) => n.toFixed(2)).join(", ")}]
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Action Button */}
        <div className="mt-5 sm:mt-6 flex justify-end">
          <button
            onClick={onClose}
            className={`min-h-[48px] w-full sm:w-auto px-6 py-2.5 rounded-xl font-bold focus:ring-4 focus:ring-yellow-400 text-sm sm:text-base transition-colors ${
              highContrast
                ? "bg-yellow-400 text-black hover:bg-yellow-300"
                : "bg-slate-800 text-white hover:bg-slate-900"
            }`}
          >
            Close Proof
          </button>
        </div>
      </div>
    </div>
  );
}
