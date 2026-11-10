import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Document History",
  description: "View and manage your recently analyzed notices and privacy settings.",
  alternates: {
    canonical: "/history",
  },
  robots: {
    index: false,
    follow: false,
  },
};

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

