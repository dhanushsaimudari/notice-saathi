import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Upload Document",
  description: "Upload a legal or property tax notice for evidence-first analysis.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function UploadLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

