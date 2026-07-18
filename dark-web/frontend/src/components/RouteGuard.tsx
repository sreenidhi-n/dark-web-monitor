"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getMe } from "@/lib/api";
import { Spinner } from "./ui/Spinner";

export function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const [initializing, setInitializing] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const token = localStorage.getItem("dwm_token");
    if (!token) {
      setInitializing(false);
      if (pathname !== "/login") router.replace("/login");
      return;
    }
    if (user) {
      setInitializing(false);
      return;
    }
    getMe()
      .then((me) => { setUser(me); setInitializing(false); })
      .catch(() => {
        localStorage.removeItem("dwm_token");
        setInitializing(false);
        router.replace("/login");
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (initializing && pathname !== "/login") {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-gray-950">
        <Spinner size="lg" />
      </div>
    );
  }

  return <>{children}</>;
}
