"use client";

import { Inter } from "next/font/google";
import { useState } from "react";
import { usePathname } from "next/navigation";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { RouteGuard } from "@/components/RouteGuard";
import { AppNav } from "@/components/AppNav";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

function AppShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  if (isLogin || !user) return <>{children}</>;

  return (
    <>
      <AppNav />
      <main className="p-6">{children}</main>
    </>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <RouteGuard>
              <AppShell>{children}</AppShell>
            </RouteGuard>
          </AuthProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
