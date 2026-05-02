import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aegis | Clinical Intelligence Platform",
  description:
    "Context-Aware Multi-Agent Clinical Wearable Platform — real-time telemetry, AI diagnostics, and 3D digital twin",
  authors: [{ name: "Aegis" }],
  manifest: "/manifest.json",
  openGraph: {
    title: "MedVerse Clinical Platform",
    description: "Context-Aware Multi-Agent Clinical Wearable Platform",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#4f46e5",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
