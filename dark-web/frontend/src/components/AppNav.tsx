"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/findings", label: "Findings" },
  { href: "/sources", label: "Sources" },
  { href: "/watchlists", label: "Watchlists" },
  { href: "/alerts", label: "Alerts" },
];

export function AppNav() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user || pathname === "/login") return null;

  return (
    <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center gap-6">
      <span className="font-bold text-red-500 tracking-widest text-sm mr-2">DWM</span>

      {NAV.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          className={`text-sm transition-colors ${
            pathname === href
              ? "text-gray-100 font-medium"
              : "text-gray-400 hover:text-gray-100"
          }`}
        >
          {label}
        </Link>
      ))}

      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-gray-500 hidden sm:block">{user.email}</span>
        <span className="text-[10px] uppercase tracking-wider border border-gray-700 rounded px-1.5 py-0.5 text-gray-600">
          {user.role}
        </span>
        <button
          onClick={logout}
          title="Sign out"
          className="text-gray-600 hover:text-gray-200 transition-colors ml-1"
        >
          <LogOut size={15} />
        </button>
      </div>
    </nav>
  );
}
