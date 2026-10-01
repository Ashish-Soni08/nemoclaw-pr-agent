import type { Metadata } from "next";
import { Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const ui = Archivo({ variable: "--font-ui", subsets: ["latin"] });
const data = JetBrains_Mono({ variable: "--font-data", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PR Agent Ledger",
  description: "Every decision the NemoClaw PR agent made, why it made it, and what it cost.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${ui.variable} ${data.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
