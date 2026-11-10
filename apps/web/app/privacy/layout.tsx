import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy & Data Protection",
  description: "NoticeSaathi Privacy Policy. Compliant with DPDP Act 2023, 48-hour automated retention, local OCR boundaries, and user consent controls.",
  alternates: {
    canonical: "/privacy",
  },
  openGraph: {
    title: "Privacy Policy — NoticeSaathi",
    description: "Compliant with DPDP Act 2023. 48-hour automated retention, local OCR, and strict user consent.",
    url: "https://noticesaathi.org/privacy",
    type: "website",
  },
};

export default function PrivacyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

