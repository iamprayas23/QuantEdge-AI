import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QuantEdge | Quantitative Backtesting & Grounded AI Platform",
  description: "Institutional-Grade Quantitative Backtesting, Regime Analysis & Grounded AI Strategy Research",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0a0d14] text-[#e2e8f0] min-h-screen">
        {children}
      </body>
    </html>
  );
}
