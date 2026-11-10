import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Document Analysis",
  description: "Evidence-first Action Cards and verified citations extracted from document text.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function DocumentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

