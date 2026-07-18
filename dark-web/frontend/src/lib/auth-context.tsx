"use client";

import { createContext, useContext, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { login as apiLogin, getMe } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  setUser: (u: User | null) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const router = useRouter();

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiLogin(email, password);
    localStorage.setItem("dwm_token", access_token);
    const me = await getMe();
    setUser(me);
    router.replace("/");
  }, [router]);

  const logout = useCallback(() => {
    localStorage.removeItem("dwm_token");
    setUser(null);
    router.replace("/login");
  }, [router]);

  return <Ctx.Provider value={{ user, setUser, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
