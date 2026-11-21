import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FacultyScreen - Professor Resume Screening & Curation Platform",
  description: "AI-Powered Multimodal Academic Recruitment & Decision-Support System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
