"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
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
  const [displayName, setDisplayName] = useState("User");
  const [userEmail, setUserEmail] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  // Theme context from kushal-dev
  const { theme, toggleTheme } = useTheme();

  // User sync logic from testsparkhack
  useEffect(() => {
    syncUserEmailFromUrl();
    setDisplayName(readStoredName());
    setUserEmail(readStoredEmail());
    void syncUserNameFromApi().then(() => {
      setDisplayName(readStoredName());
      setUserEmail(readStoredEmail());
    });
    const onUpdate = () => {
      setDisplayName(readStoredName());
      setUserEmail(readStoredEmail());
    };
    window.addEventListener("profitpilot-user", onUpdate);
    window.addEventListener("storage", onUpdate);
    return () => {
      window.removeEventListener("profitpilot-user", onUpdate);
      window.removeEventListener("storage", onUpdate);
    };
  }, []);

  // Dropdown click outside logic
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onSearch?.(val);
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onMenuClick}
          aria-label="Open navigation"
          aria-controls="dashboard-sidebar"
        >
          <MenuIcon size={20} />
        </button>
        <span className="topbar-title">{title}</span>
        <div className="search-box">
          <span className="search-icon"><SearchIcon size={15} color="#94A3B8" /></span>
          <input
            type="text"
            placeholder="Search orders, products, or customers..."
            value={query}
            onChange={handleChange}
          />
          <span style={{ fontSize: 11, color: "#94A3B8", fontWeight: 500 }}>
            ⌘K
          </span>
        </div>
      </div>
      
      <div className="topbar-right">
        {/* Theme Toggle Button (Added from kushal-dev) */}
        <button 
          className="topbar-icon-btn" 
          onClick={toggleTheme}
          title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
        >
          {theme === "light" ? <MoonIcon size={16} /> : <SunIcon size={16} />}
        </button>

        <button className="topbar-icon-btn" title="Help">
          <HelpCircleIcon size={16} />
        </button>
        <button className="topbar-icon-btn" title="Notifications">
          <BellIcon size={16} />
        </button>

        {/* User Profile Dropdown (Added from testsparkhack) */}
        <div className="topbar-profile-wrap" ref={menuRef}>
          <button
            type="button"
            className="topbar-profile-trigger"
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span className="user-name-text">
              {displayName}
            </span>
            <div className="avatar">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          
          {menuOpen && (
            <div className="topbar-dropdown">
              {userEmail && <div className="muted">{userEmail}</div>}
              <Link href="/profile" onClick={() => setMenuOpen(false)}>Profile</Link>
              <Link href="/import" onClick={() => setMenuOpen(false)}>Import Data</Link>
              <button type="button" onClick={clearSessionAndGoLanding}>Log out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
