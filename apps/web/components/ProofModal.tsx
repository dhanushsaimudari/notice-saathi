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
      className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="proof-modal-title"
    >
      <div className={`${modalBg} rounded-2xl max-w-2xl w-full p-6 sm:p-7 relative max-h-[90vh] overflow-y-auto`}>
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2.5 min-h-[48px] min-w-[48px] rounded-full hover:bg-slate-200/50 focus:ring-4 focus:ring-yellow-400 flex items-center justify-center"
          aria-label="Close proof viewer"
        >
          <X className="w-6 h-6" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5 pr-10">
          <div className="p-2.5 rounded-xl bg-indigo-600 text-white">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 id="proof-modal-title" className="text-xl sm:text-2xl font-bold">
              Original Document Evidence
            </h2>
            <p className="text-sm opacity-80">
              Verified ground-truth passages extracted from your document
            </p>
          </div>
        </div>

        {/* Evidence List */}
        <div className="space-y-4 mt-4">
          {proofRefs.map((ref, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-xl border ${
                highContrast
                  ? "bg-zinc-900 border-yellow-400"
                  : "bg-slate-50 border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono font-bold mb-2 pb-1 border-b border-slate-200/50">
                <span className="text-emerald-500 flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" /> Block Verified
                </span>
                <span>Page {ref.page_number || 1}</span>
              </div>
              <p className="font-serif italic text-base sm:text-lg leading-relaxed">
                "{ref.text || ref.text_snippet || "Verified document passage"}"
              </p>
              {ref.bbox && (
                <div className="mt-2 text-xs font-mono opacity-60">
                  Coordinates: [{ref.bbox.map((n: number) => n.toFixed(2)).join(", ")}]
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Action Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className={`min-h-[48px] px-6 py-2.5 rounded-xl font-bold focus:ring-4 focus:ring-yellow-400 ${
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

