import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aegis | Clinical Wearable Platform",
  description:
    "Context-Aware Multi-Agent Clinical Wearable Platform for personalized medicine — real-time telemetry dashboard",
  authors: [{ name: "Aegis" }],
  openGraph: {
    title: "Aegis Clinical Platform",
    description: "Context-Aware Multi-Agent Clinical Wearable Platform",
    type: "website",
  },
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
