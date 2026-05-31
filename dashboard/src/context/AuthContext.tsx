"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { setToken as setGlobalToken } from "@/lib/api";

const SESSION_BRIDGE_KEY = "profit_pilot_token_bridge";

interface AuthContextType {
  token: string | null;
  setToken: (token: string | null) => void;
  getAuthHeaders: () => HeadersInit;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  setToken: () => {},
  getAuthHeaders: () => ({ "Content-Type": "application/json" }),
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const bridged = sessionStorage.getItem(SESSION_BRIDGE_KEY);
    if (bridged) {
      setGlobalToken(bridged);
      setTokenState(bridged);
      sessionStorage.removeItem(SESSION_BRIDGE_KEY);
    }
  }, []);

  const setToken = useCallback((newToken: string | null) => {
    setGlobalToken(newToken);
    setTokenState(newToken);
  }, []);

  const getAuthHeaders = useCallback((): HeadersInit => {
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, setToken, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);