import type { Metadata } from "next";
import "./globals.css";
import { PHProvider } from "./providers";

export const metadata: Metadata = {
  title: "PageScore — AI Landing Page Analyzer",
  description:
    "Get an instant AI-powered analysis of your landing page. Find what's broken, what's missing, and what to fix — in 30 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <PHProvider>{children}</PHProvider>
      </body>
    </html>
  );
}
