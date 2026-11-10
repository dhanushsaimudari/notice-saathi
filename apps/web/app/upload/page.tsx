"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAccessibility } from "@/lib/accessibility";
import { api } from "@/lib/api";
import { Camera, Upload, AlertCircle, RefreshCw, ArrowLeft, X, Video } from "lucide-react";
import Link from "next/link";

export default function UploadPage() {
  const router = useRouter();
  const { t, highContrast } = useAccessibility();
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<string>("idle"); // idle, uploading, processing, ready, error, status_error, needs_recapture
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Live Camera State & Refs
  const [isCameraActive, setIsCameraActive] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const clearPollTimer = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  // Cleanup media stream and poll timers on unmount
  useEffect(() => {
    return () => {
      stopCamera();
      clearPollTimer();
    };
  }, []);

  // Handle URL query parameters (?pick=file or ?pick=camera)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const pick = params.get("pick");
      if (pick === "file") {
        const timer = setTimeout(() => {
          fileInputRef.current?.click();
        }, 150);
        return () => clearTimeout(timer);
      } else if (pick === "camera") {
        const timer = setTimeout(() => {
          startCamera();
        }, 150);
        return () => clearTimeout(timer);
      }
    }
  }, []);

  const stopCamera = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
  };

  const startCamera = async () => {
    setCameraError(null);
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      // Fallback for browsers or devices without getUserMedia
      cameraInputRef.current?.click();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false, // Strictly video only, never request microphone for camera capture
      });

      mediaStreamRef.current = stream;
      setIsCameraActive(true);

      // Attach stream to video element
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch((err) => {
            console.warn("Video playback was interrupted:", err);
          });
        }
      }, 50);
    } catch (err: any) {
      console.warn("Camera access failed:", err);
      let msg = "Unable to access camera.";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        msg = "Camera permission was denied. Please allow camera access in your browser settings or choose a photo/PDF file.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        msg = "No camera found on this device. Please select a document image or PDF file.";
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        msg = "Camera is currently in use by another application.";
      }
      setCameraError(msg);
      setIsCameraActive(false);
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], "notice_camera_capture.jpg", { type: "image/jpeg" });
          setSelectedFile(file);
          setPreviewUrl(URL.createObjectURL(file));
          setErrorMessage(null);
          stopCamera();
          startProcessing(file);
        }
      },
      "image/jpeg",
      0.92
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setErrorMessage(null);

      // Generate preview for images
      if (file.type.startsWith("image/")) {
        setPreviewUrl(URL.createObjectURL(file));
      } else {
        setPreviewUrl(null);
      }

      // Automatically begin document upload & verification immediately
      startProcessing(file);
    }
  };

  const pollStatus = (docId: string) => {
    clearPollTimer();
    setStage("processing");
    setErrorMessage(null);

    let attempts = 0;
    let consecutiveErrors = 0;

    pollTimerRef.current = setInterval(async () => {
      attempts++;
      try {
        const statusRes = await api.getDocumentStatus(docId);
        consecutiveErrors = 0; // Reset on success

        if (statusRes.state === "READY") {
          clearPollTimer();
          setStage("ready");
          setTimeout(() => {
            router.push(`/documents/${docId}`);
          }, 400);
          return;
        } else if (statusRes.state === "NEEDS_RECAPTURE") {
          clearPollTimer();
          setStage("needs_recapture");
          setErrorMessage(statusRes.message || t.needsRecapture);
          return;
        } else if (statusRes.state === "FAILED_FINAL") {
          clearPollTimer();
          setStage("error");
          setErrorMessage(statusRes.message || "Document processing failed.");
          return;
        }

        if (attempts >= 40) {
          clearPollTimer();
          router.push(`/documents/${docId}`);
        }
      } catch (err: any) {
        consecutiveErrors++;
        console.warn(`Status polling check ${attempts} failed:`, err);
        if (consecutiveErrors >= 3 || attempts >= 30) {
          clearPollTimer();
          setStage("status_error");
          setErrorMessage(
            "Document was uploaded safely, but checking status failed. You can check status again or open the document."
          );
        }
      }
    }, 1000);
  };

  const startProcessing = async (fileToProcess?: File) => {
    const file = fileToProcess || selectedFile;
    if (!file) return;

    try {
      setStage("uploading");
      setErrorMessage(null);
      clearPollTimer();

      const res = await api.uploadDocument(file);
      setUploadedDocId(res.document_id);

      // Backend synchronous pipeline already completed processing
      if (res.state === "READY") {
        setStage("ready");
        setTimeout(() => {
          router.push(`/documents/${res.document_id}`);
        }, 400);
        return;
      }

      if (res.state === "NEEDS_RECAPTURE") {
        setStage("needs_recapture");
        setErrorMessage(res.quality_metrics?.details?.join(". ") || t.needsRecapture);
        return;
      }

      // If document is in an intermediate state (e.g. PROCESSING), poll status
      pollStatus(res.document_id);
    } catch (err: any) {
      setStage("error");
      setErrorMessage(err.message || "Upload failed. Please check file format and try again.");
    }
  };

  const cardBg = highContrast
    ? "bg-zinc-950 border-4 border-yellow-400 text-yellow-300"
    : "bg-white border border-slate-200 text-slate-900 shadow-md";

  return (
    <div className="space-y-4 sm:space-y-6 max-w-2xl mx-auto py-2 sm:py-4 w-full">
      {/* Back button */}
      <Link
        href="/"
        className="inline-flex items-center gap-2 font-bold px-3 py-2 rounded-lg hover:underline focus:ring-4 focus:ring-yellow-400 min-h-[48px] text-base"
      >
        <ArrowLeft className="w-5 h-5 shrink-0" />
        <span>{t.home}</span>
      </Link>

      <div className={`${cardBg} rounded-2xl sm:rounded-3xl p-4 sm:p-8`}>
        <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold mb-2 break-words">
          {stage === "needs_recapture" ? t.needsRecapture : t.uploadDoc}
        </h1>
        <p className="opacity-80 text-sm sm:text-base mb-5 sm:mb-6 leading-relaxed break-words">
          PDF, JPG, or PNG (up to 15MB). We verify all dates, amounts, and directives before explaining.
        </p>

        {/* Visually hidden inputs for Camera and File Picker (accessible in DOM, never hidden via display:none) */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png,image/*"
          onChange={handleFileChange}
          onClick={(e) => {
            (e.target as HTMLInputElement).value = "";
          }}
          className="sr-only"
          id="file-upload"
          tabIndex={-1}
          aria-hidden="true"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileChange}
          onClick={(e) => {
            (e.target as HTMLInputElement).value = "";
          }}
          className="sr-only"
          id="camera-capture"
          tabIndex={-1}
          aria-hidden="true"
        />

        {/* Live Camera Viewfinder */}
        {isCameraActive && (
          <div className="mb-6 p-4 rounded-2xl border-2 border-emerald-500/50 bg-black/90 text-white space-y-4">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 font-bold text-sm sm:text-base text-emerald-400">
                <Video className="w-5 h-5" />
                Live Camera Viewfinder
              </span>
              <button
                onClick={stopCamera}
                className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 min-h-[44px] min-w-[44px] flex items-center justify-center focus:ring-2 focus:ring-yellow-400 cursor-pointer"
                aria-label="Close camera"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs sm:text-sm text-zinc-300">
              Align your notice clearly inside the frame. Ensure good lighting and readable text.
            </p>

            <div className="overflow-hidden rounded-xl bg-black border border-zinc-700 flex justify-center">
              <video
                ref={videoRef}
                playsInline
                autoPlay
                muted
                className="w-full max-h-[360px] object-contain bg-black"
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-3 items-stretch">
              <button
                type="button"
                onClick={capturePhoto}
                className={`flex-1 min-h-[56px] px-6 py-3.5 rounded-xl font-bold flex items-center justify-center gap-2 text-base sm:text-lg focus:ring-4 focus:ring-yellow-400 transition-colors cursor-pointer ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg"
                }`}
              >
                <Camera className="w-6 h-6 shrink-0" />
                <span>Capture Photo</span>
              </button>

              <button
                type="button"
                onClick={stopCamera}
                className="min-h-[56px] px-5 py-3 rounded-xl font-bold border-2 border-zinc-600 hover:bg-zinc-800 text-zinc-200 text-base cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Camera Error / Permission Fallback Notification */}
        {cameraError && (
          <div className="mb-4 p-4 rounded-xl bg-amber-500/10 border-2 border-amber-500 text-amber-500 space-y-2">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <p className="text-sm font-semibold">{cameraError}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setCameraError(null);
                fileInputRef.current?.click();
              }}
              className="text-xs font-bold underline hover:opacity-80 block cursor-pointer"
            >
              Choose a file from your device instead &rarr;
            </button>
          </div>
        )}

        {/* Choose Actions */}
        {stage === "idle" && !isCameraActive && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
              <button
                type="button"
                onClick={startCamera}
                className={`min-h-[56px] px-5 py-3.5 sm:py-4 rounded-xl sm:rounded-2xl font-bold flex items-center justify-center gap-3 text-base sm:text-lg focus:ring-4 focus:ring-yellow-400 text-center transition-colors cursor-pointer ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                <Camera className="w-6 h-6 shrink-0" />
                <span className="break-words">{t.takePhoto}</span>
              </button>

              <label
                htmlFor="file-upload"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                className={`min-h-[56px] px-5 py-3.5 sm:py-4 rounded-xl sm:rounded-2xl font-bold flex items-center justify-center gap-3 text-base sm:text-lg border-2 focus:ring-4 focus:ring-yellow-400 text-center transition-colors cursor-pointer select-none ${
                  highContrast
                    ? "bg-zinc-900 border-yellow-400 text-yellow-300 hover:bg-zinc-800"
                    : "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300"
                }`}
              >
                <Upload className="w-6 h-6 text-emerald-600 shrink-0" />
                <span className="break-words">{t.uploadDoc}</span>
              </label>
            </div>

            {/* Selected File Card (if upload in progress or needs manual restart) */}
            {selectedFile && (
              <div className="mt-4 sm:mt-6 p-4 rounded-2xl border-2 border-emerald-500/40 bg-emerald-50/20">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-bold text-base sm:text-lg truncate">{selectedFile.name}</h3>
                    <p className="text-xs sm:text-sm opacity-75 font-mono">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <span className="text-emerald-500 font-bold text-xs sm:text-sm shrink-0">Selected</span>
                </div>

                {previewUrl && (
                  <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 dark:border-zinc-700 max-h-60 flex justify-center bg-black">
                    <img src={previewUrl} alt="Document preview" className="object-contain max-h-60 w-auto" />
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => startProcessing()}
                  className={`mt-4 w-full min-h-[56px] px-5 py-3 rounded-xl font-bold text-base sm:text-lg focus:ring-4 focus:ring-yellow-400 transition-colors cursor-pointer ${
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
          <div className="py-6 sm:py-8 text-center space-y-4">
            {previewUrl && (
              <div className="mx-auto max-w-xs overflow-hidden rounded-xl border border-slate-200 dark:border-zinc-700 max-h-48 flex justify-center bg-black mb-3">
                <img src={previewUrl} alt="Analyzing document" className="object-contain max-h-48 w-auto opacity-80" />
              </div>
            )}
            <div className="inline-block p-4 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 animate-pulse">
              <RefreshCw className="w-8 h-8 sm:w-10 sm:h-10 animate-spin" />
            </div>
            <h2 className="text-lg sm:text-2xl font-bold break-words">
              {stage === "uploading"
                ? t.uploading
                : stage === "processing"
                ? t.verifyingEvidence
                : t.ready}
            </h2>
            {selectedFile && (
              <p className="font-mono text-xs sm:text-sm text-emerald-600 dark:text-emerald-400 font-bold truncate max-w-sm mx-auto">
                {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
            <p className="text-sm sm:text-base opacity-75 max-w-md mx-auto leading-relaxed break-words">
              Extracting text blocks, assessing image quality, and generating evidence-grounded Action Cards.
            </p>
          </div>
        )}

        {/* Recapture Required View (Quality Gate triggered) */}
        {stage === "needs_recapture" && (
          <div className="py-4 sm:py-6 space-y-4">
            <div className="p-4 rounded-2xl bg-amber-500/10 border-2 border-amber-500 text-amber-500 flex items-start gap-3">
              <AlertCircle className="w-6 h-6 sm:w-7 sm:h-7 shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <h3 className="text-base sm:text-lg font-bold break-words">అస్పష్టమైన చిత్రం (Needs Recapture)</h3>
                <p className="text-sm sm:text-base text-slate-800 dark:text-slate-200 mt-1 leading-relaxed break-words">
                  {errorMessage || "Image is blurry or cropped. NoticeSaathi never guesses important dates or actions."}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mt-4">
              <button
                onClick={startCamera}
                className={`min-h-[56px] px-5 py-3 rounded-xl font-bold flex items-center justify-center gap-2 text-base transition-colors ${
                  highContrast
                    ? "bg-yellow-400 text-black hover:bg-yellow-300"
                    : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                <Camera className="w-5 h-5 sm:w-6 sm:h-6 shrink-0" />
                <span>{t.retakePhoto}</span>
              </button>

              <button
                onClick={() => setStage("idle")}
                className={`min-h-[56px] px-5 py-3 rounded-xl font-bold border-2 text-base transition-colors ${
                  highContrast
                    ? "border-yellow-400 text-yellow-300 hover:bg-zinc-800"
                    : "border-slate-300 text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:border-zinc-700"
                }`}
              >
                Select Different File
              </button>
            </div>
          </div>
        )}

        {/* Status Error View (Uploaded safely, but polling hit transient network error) */}
        {stage === "status_error" && (
          <div className="py-4 sm:py-6 space-y-4">
            <div className="p-4 rounded-2xl bg-amber-500/10 border-2 border-amber-500 text-amber-500 flex items-start gap-3">
              <AlertCircle className="w-6 h-6 sm:w-7 sm:h-7 shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <h3 className="text-base sm:text-lg font-bold">Status Check Interrupted</h3>
                <p className="text-sm sm:text-base text-slate-800 dark:text-slate-200 mt-1 leading-relaxed break-words">
                  {errorMessage || "Document was uploaded safely, but checking status failed."}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 mt-4">
              {uploadedDocId && (
                <button
                  onClick={() => pollStatus(uploadedDocId)}
                  className={`min-h-[56px] px-5 py-3 rounded-xl font-bold flex items-center justify-center gap-2 text-base transition-colors ${
                    highContrast
                      ? "bg-yellow-400 text-black hover:bg-yellow-300"
                      : "bg-emerald-600 hover:bg-emerald-700 text-white"
                  }`}
                >
                  <RefreshCw className="w-5 h-5 shrink-0" />
                  <span>Check Status Again</span>
                </button>
              )}
              {uploadedDocId && (
                <button
                  onClick={() => router.push(`/documents/${uploadedDocId}`)}
                  className={`min-h-[56px] px-5 py-3 rounded-xl font-bold border-2 text-base transition-colors ${
                    highContrast
                      ? "border-yellow-400 text-yellow-300 hover:bg-zinc-800"
                      : "border-slate-300 text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:border-zinc-700"
                  }`}
                >
                  Go to Document
                </button>
              )}
            </div>

            <button
              onClick={() => {
                setUploadedDocId(null);
                setSelectedFile(null);
                setPreviewUrl(null);
                setStage("idle");
              }}
              className="w-full text-center text-sm font-semibold opacity-75 hover:opacity-100 underline mt-2"
            >
              Upload a different document
            </button>
          </div>
        )}

        {/* Error View */}
        {stage === "error" && (
          <div className="py-4 sm:py-6 space-y-4">
            <div className="p-4 rounded-2xl bg-rose-500/10 border-2 border-rose-500 text-rose-500 flex items-start gap-3">
              <AlertCircle className="w-6 h-6 sm:w-7 sm:h-7 shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <h3 className="text-base sm:text-lg font-bold">Error</h3>
                <p className="text-sm sm:text-base text-slate-800 dark:text-slate-200 mt-1 leading-relaxed break-words">
                  {errorMessage}
                </p>
              </div>
            </div>

            <button
              onClick={() => setStage("idle")}
              className={`min-h-[56px] w-full px-5 py-3 rounded-xl font-bold text-base transition-colors ${
                highContrast
                  ? "bg-yellow-400 text-black hover:bg-yellow-300"
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
