"use client";

import React from "react";
import Link from "next/link";
import { useAccessibility } from "@/lib/accessibility";
import { FileQuestion, ArrowLeft } from "lucide-react";

export default function NotFound() {
  const { t, highContrast } = useAccessibility();

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-md";

  return (
    <div className="py-12 sm:py-20 max-w-lg mx-auto text-center px-4 w-full">
      <div className={`${cardBg} rounded-3xl p-6 sm:p-10 space-y-5`}>
        <div className="p-3 bg-emerald-600/10 text-emerald-600 rounded-2xl w-fit mx-auto">
          <FileQuestion className="w-12 h-12" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold">పేజీ కనుగొనబడలేదు (Page Not Found)</h1>
        <p className="opacity-80 text-base leading-relaxed">
          The requested page could not be found. Please return to home.
        </p>
        <Link
          href="/"
          className={`inline-flex items-center justify-center gap-2 min-h-[48px] px-6 py-3 rounded-xl font-bold focus:ring-4 focus:ring-yellow-400 ${
            highContrast
              ? "bg-yellow-400 text-black hover:bg-yellow-300"
              : "bg-emerald-600 hover:bg-emerald-700 text-white"
          }`}
        >
          <ArrowLeft className="w-5 h-5" />
          <span>{t.home}</span>
        </Link>
      </div>
    </div>
  );
}

