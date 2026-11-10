import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { AccessibilityProvider } from "@/lib/accessibility";
import Navbar from "@/components/Navbar";
import { ShieldCheck } from "lucide-react";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || "https://noticesaathi.org"),
  title: {
    default: "NoticeSaathi — Proof Before Explanation",
    template: "%s | NoticeSaathi",
  },
  description: "Evidence-first, voice-enabled document understanding for older adults and regional Indian language speakers. Compliant with DPDP Act 2023.",
  keywords: ["government notices", "property tax", "legal notice", "telugu voice", "evidence citations", "action cards", "accessibility"],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "NoticeSaathi — Proof Before Explanation",
    description: "Every answer grounded in verified text. Telugu voice explanation and accessibility-first design.",
    url: "https://noticesaathi.org",
    siteName: "NoticeSaathi",
    locale: "te_IN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "NoticeSaathi — Proof Before Explanation",
    description: "Evidence-first document understanding with regional voice interaction.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5, // Allow zooming for accessibility
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://noticesaathi.org/#organization",
      "name": "NoticeSaathi",
      "url": "https://noticesaathi.org",
      "logo": "https://noticesaathi.org/logo.png",
      "description": "Evidence-first, voice-enabled document understanding platform for Indian citizens and older adults.",
      "sameAs": ["https://github.com/dhanushsaimudari/notice-saathi"]
    },
    {
      "@type": "WebApplication",
      "@id": "https://noticesaathi.org/#webapp",
      "name": "NoticeSaathi",
      "applicationCategory": "GovernmentApplication",
      "operatingSystem": "All",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "INR"
      },
      "featureList": [
        "Local OCR Extraction",
        "Evidence-first Action Cards",
        "Telugu Voice Interaction via Gnani.ai",
        "Contradiction and Ambiguity Interceptor",
        "Automated 48-Hour Data Retention"
      ]
    }
  ]
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="antialiased font-sans min-h-screen overflow-x-hidden flex flex-col justify-between">
        <AccessibilityProvider>
          <div>
            <Navbar />
            <main className="w-full max-w-4xl mx-auto px-3.5 py-4 sm:px-6 sm:py-6 overflow-x-hidden min-w-0">
              {children}
            </main>
          </div>

          {/* Accessible Footer with Internal Navigation Links */}
          <footer className="w-full border-t border-slate-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-950/50 py-6 px-4 mt-12 text-sm">
            <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 font-semibold text-slate-700 dark:text-zinc-300">
                <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>NoticeSaathi — Proof Before Explanation</span>
              </div>

              <nav aria-label="Footer Navigation" className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 font-medium">
                <Link href="/" className="hover:underline text-slate-600 dark:text-zinc-400 focus:ring-2 focus:ring-yellow-400 rounded px-1">
                  Home
                </Link>
                <Link href="/upload" className="hover:underline text-slate-600 dark:text-zinc-400 focus:ring-2 focus:ring-yellow-400 rounded px-1">
                  Upload
                </Link>
                <Link href="/history" className="hover:underline text-slate-600 dark:text-zinc-400 focus:ring-2 focus:ring-yellow-400 rounded px-1">
                  History
                </Link>
                <Link href="/privacy" className="hover:underline text-slate-600 dark:text-zinc-400 focus:ring-2 focus:ring-yellow-400 rounded px-1">
                  Privacy Policy
                </Link>
              </nav>

              <div className="text-xs opacity-70 text-center sm:text-right">
                Privacy-First Architecture • Configurable Data Retention
              </div>
            </div>
          </footer>
        </AccessibilityProvider>
      </body>
    </html>
  );
}
