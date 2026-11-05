import type { Metadata } from "next";
import "./globals.css";
import { AccessibilityProvider } from "@/lib/accessibility";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "NoticeSaathi — Proof Before Explanation",
  description: "Evidence-first, voice-enabled document understanding for older adults and accessibility needs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-sans">
        <AccessibilityProvider>
          <Navbar />
          <main className="max-w-4xl mx-auto px-4 py-6 sm:px-6">{children}</main>
        </AccessibilityProvider>
      </body>
    </html>
  );
}
