"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { SearchIcon, HelpCircleIcon, BellIcon, SunIcon, MoonIcon, MenuIcon } from "./Icons";
import { LANDING_PAGE_URL } from "@/lib/publicUrls";
import { syncUserEmailFromUrl, syncUserNameFromApi } from "@/lib/syncDashboardUser";
import { useTheme } from "@/context/ThemeContext";

interface TopbarProps {
  onSearch: (query: string) => void;
  title?: string;
  onMenuClick?: () => void;
}

function readStoredName(): string {
  try {
    const u = JSON.parse(localStorage.getItem("profit_pilot_user") || "{}") as {
      full_name?: string;
    };
    return (u.full_name || "").trim() || "User";
  } catch {
    return "User";
  }
}

function readStoredEmail(): string {
  try {
    const u = JSON.parse(localStorage.getItem("profit_pilot_user") || "{}") as {
      email?: string;
    };
    return (u.email || "").trim();
  } catch {
    return "";
  }
}

function clearSessionAndGoLanding() {
  const keys = Object.keys(localStorage);
  for (const key of keys) {
    if (key.startsWith("profit_pilot")) localStorage.removeItem(key);
  }
  window.location.href = LANDING_PAGE_URL.replace(/\/$/, "");
}

export default function Topbar({ onSearch, title = "Overview", onMenuClick }: TopbarProps) {
  const [query, setQuery] = useState("");
  const [displayName, setDisplayName] = useState(readStoredName);
  const [userEmail, setUserEmail] = useState(readStoredEmail);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  // Theme context from kushal-dev
  const { theme, toggleTheme } = useTheme();

  const refreshUserState = useCallback(() => {
    setDisplayName(readStoredName());
    setUserEmail(readStoredEmail());
  }, []);

  // User sync logic from testsparkhack
  useEffect(() => {
    syncUserEmailFromUrl();
    queueMicrotask(refreshUserState);
    void syncUserNameFromApi().then(refreshUserState);
    .catch(err => console.error(err))