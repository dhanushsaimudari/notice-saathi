"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAccessibility } from "@/lib/accessibility";
import { api } from "@/lib/api";
import { Camera, Upload, AlertCircle, RefreshCw, CheckCircle2, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function UploadPage() {
  const router = useRouter();
  const { t, highContrast } = useAccessibility();
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<string>("idle"); // idle, uploading, processing, error, needs_recapture
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setErrorMessage(null);
      setStage("idle");

      // Generate preview for images
      if (file.type.startsWith("image/")) {
        setPreviewUrl(URL.createObjectURL(file));
      } else {
        setPreviewUrl(null);
      }
    }
  };

  const startProcessing = async () => {
    if (!selectedFile) return;

    try {
      setStage("uploading");
      setErrorMessage(null);

      const res = await api.uploadDocument(selectedFile);
      
      setStage("processing");
      
      // Poll status
      let attempts = 0;
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const statusRes = await api.getDocumentStatus(res.document_id);
          if (statusRes.state === "READY") {
            clearInterval(pollInterval);
            setStage("ready");
            setTimeout(() => {
              router.push(`/documents/${res.document_id}`);
            }, 600);
          } else if (statusRes.state === "NEEDS_RECAPTURE") {
            clearInterval(pollInterval);
            setStage("needs_recapture");
            setErrorMessage(statusRes.message || t.needsRecapture);
          } else if (statusRes.state === "FAILED_FINAL") {
            clearInterval(pollInterval);
            setStage("error");
            setErrorMessage(statusRes.message || "Document processing failed.");
          }

          if (attempts > 30) {
            clearInterval(pollInterval);
            router.push(`/documents/${res.document_id}`);
          }
        } catch (err) {
          clearInterval(pollInterval);
          setStage("error");
          setErrorMessage("Failed to check processing status.");
        }
      }, 1000);

    } catch (err: any) {
      setStage("error");
      setErrorMessage(err.message || "Upload failed. Please check file format and try again.");
    }
  };

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-md";

  return (
    <div className="space-y-6 max-w-2xl mx-auto py-4">
      {/* Back button */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px]"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>{t.home}</span>
      </Link>

      <div className={`${cardBg} rounded-3xl p-6 sm:p-8`}>
        <h1 className="text-2xl sm:text-3xl font-extrabold mb-2">
          {stage === "needs_recapture" ? t.needsRecapture : t.uploadDoc}
        </h1>
        <p className="opacity-80 text-base mb-6">
          PDF, JPG, or PNG (up to 15MB). We verify all dates, amounts, and directives before explaining.
        </p>

        {/* Hidden inputs for Camera and File Picker */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,image/jpeg,image/png"
          onChange={handleFileChange}
          className="hidden"
          id="file-upload"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          className="hidden"
          id="camera-capture"
        />

        {/* Choose Actions */}
        {stage === "idle" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                onClick={() => cameraInputRef.current?.click()}
                className={`min-h-[56px] px-6 py-4 rounded-2xl font-bold flex items-center justify-center gap-3 text-lg focus:ring-4 focus:ring-yellow-400 ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                <Camera className="w-6 h-6" />
                <span>{t.takePhoto}</span>
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                className={`min-h-[56px] px-6 py-4 rounded-2xl font-bold flex items-center justify-center gap-3 text-lg border-2 focus:ring-4 focus:ring-yellow-400 ${
                  highContrast
                    ? "bg-zinc-900 border-yellow-400 text-yellow-300"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300"
                }`}
              >
                <Upload className="w-6 h-6 text-emerald-600" />
                <span>Choose File (PDF/Image)</span>
              </button>
            </div>

            {/* Selected File Card */}
            {selectedFile && (
              <div className="mt-6 p-4 rounded-2xl border-2 border-emerald-500/40 bg-emerald-50/20">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-lg">{selectedFile.name}</h3>
                    <p className="text-sm opacity-75">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <span className="text-emerald-500 font-bold text-sm">Ready to check</span>
                </div>

                {previewUrl && (
                  <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 max-h-60 flex justify-center bg-black">
                    <img src={previewUrl} alt="Preview" className="object-contain max-h-60" />
                  </div>
                )}

                <button
                  onClick={startProcessing}
                  className={`mt-4 w-full min-h-[56px] px-6 py-3 rounded-xl font-bold text-lg focus:ring-4 focus:ring-yellow-400 ${
                    highContrast
                      ? "bg-yellow-400 text-black hover:bg-yellow-300"
                      : "bg-emerald-600 hover:bg-emerald-700 text-white"
                  }`}
                >
                  Confirm & Process Document
                </button>
              </div>
            )}
          </div>
        )}

        {/* Processing State Machine */}
        {(stage === "uploading" || stage === "processing" || stage === "ready") && (
          <div className="py-10 text-center space-y-4">
            <div className="inline-block p-4 rounded-full bg-emerald-100 text-emerald-600 animate-pulse">
              <RefreshCw className="w-10 h-10 animate-spin" />
            </div>
            <h2 className="text-xl sm:text-2xl font-bold">
              {stage === "uploading"
                ? t.uploading
                : stage === "processing"
                ? t.verifyingEvidence
                : t.ready}
            </h2>
            <p className="text-base opacity-75 max-w-md mx-auto">
              Extracting text blocks, assessing image quality, and generating evidence-grounded Action Cards.
            </p>
          </div>
        )}

        {/* Recapture Required View (Quality Gate triggered) */}
        {stage === "needs_recapture" && (
          <div className="py-6 space-y-4">
            <div className="p-4 rounded-2xl bg-amber-500/10 border-2 border-amber-500 text-amber-500 flex items-start gap-3">
              <AlertCircle className="w-7 h-7 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-bold">అస్పష్టమైన చిత్రం (Needs Recapture)</h3>
                <p className="text-base text-slate-800 dark:text-slate-200 mt-1">
                  {errorMessage || "Image is blurry or cropped. NoticeSaathi never guesses important dates or actions."}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <button
                onClick={() => cameraInputRef.current?.click()}
                className={`min-h-[56px] px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                <Camera className="w-6 h-6" />
                <span>{t.retakePhoto}</span>
              </button>

              <button
                onClick={() => setStage("idle")}
                className={`min-h-[56px] px-6 py-3 rounded-xl font-bold border-2 ${
                  highContrast
                    ? "border-yellow-400 text-yellow-300"
                    : "border-slate-300 text-slate-700 hover:bg-slate-100"
                }`}
              >
                Select Different File
              </button>
            </div>
          </div>
        )}

        {/* Error View */}
        {stage === "error" && (
          <div className="py-6 space-y-4">
            <div className="p-4 rounded-2xl bg-rose-500/10 border-2 border-rose-500 text-rose-500 flex items-start gap-3">
              <AlertCircle className="w-7 h-7 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-bold">Error</h3>
                <p className="text-base text-slate-800 dark:text-slate-200 mt-1">
                  {errorMessage}
                </p>
              </div>
            </div>

            <button
              onClick={() => setStage("idle")}
              className={`min-h-[56px] w-full px-6 py-3 rounded-xl font-bold ${
                highContrast
                  ? "bg-yellow-400 text-black"
                  : "bg-slate-800 hover:bg-slate-900 text-white"
              }`}
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

