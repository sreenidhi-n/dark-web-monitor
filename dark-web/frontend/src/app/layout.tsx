"use client";

import { Inter } from "next/font/google";
import Link from "next/link";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/findings", label: "Findings" },
  { href: "/sources", label: "Sources" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/alerts", label: "Alerts" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <QueryClientProvider client={queryClient}>
          <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center gap-8">
            <span className="font-bold text-red-500 tracking-widest text-sm">DWM</span>
            {NAV.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
          <main className="p-6">{children}</main>
        </QueryClientProvider>
      </body>
    </html>
  );
}
