import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { MobileNavigation, Sidebar } from "@/components/shell/Navigation";
import { StatusFooter } from "@/components/shell/StatusFooter";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: { default: "DemandIQ — Intelligent Demand & Inventory Analytics", template: "%s · DemandIQ" },
  description:
    "Research explorer for a Cairo University graduation project: validated demand forecasts and bounded, hypothetical inventory simulations.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#0f1b33", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-GB" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">
        <a href="#main" className="sr-only z-50 rounded bg-surface px-3 py-2 text-ink focus:not-sr-only focus:fixed focus:left-3 focus:top-3">
          Skip to content
        </a>
        <div className="flex min-h-dvh">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <MobileNavigation />
            <main id="main" className="w-full flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
              <div className="mx-auto w-full max-w-[1280px]">{children}</div>
            </main>
            <StatusFooter />
          </div>
        </div>
      </body>
    </html>
  );
}
