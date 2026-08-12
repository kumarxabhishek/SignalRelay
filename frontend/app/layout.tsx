import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SignalRelay — Evidence-backed NSE market research",
  description: "Inspect evidence-backed, source-traceable market activity reports for NSE-listed stocks. Research software — not investment advice.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
  openGraph: { title: "SignalRelay — Evidence-backed NSE market research", description: "Research dashboard for evidence-backed NSE market signals. Transparent sources, uncertainty made visible.", type: "website", siteName: "SignalRelay" },
  twitter: { card: "summary", title: "SignalRelay — Evidence-backed NSE market research", description: "Research dashboard for evidence-backed NSE market signals. Transparent sources, uncertainty made visible." },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body className={inter.variable}>{children}</body></html>; }
