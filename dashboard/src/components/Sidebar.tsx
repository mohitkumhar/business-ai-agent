"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LANDING_PAGE_URL } from "@/lib/publicUrls";
import { 
  DashboardIcon, 
  ChatbotIcon, 
  SparklesIcon, 
  ReceiptIcon, 
  PackageIcon, 
  UsersIcon, 
  AlertTriangleIcon,
  FileUpIcon,
  SettingsIcon,
  XIcon
} from "./Icons";

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

function clearProfitPilotSession() {
  if (typeof window === "undefined") return;
  const keys = Object.keys(localStorage);
  for (const key of keys) {
    if (key.startsWith("profit_pilot")) localStorage.removeItem(key);
  }
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();

  // Management section (Testsparkhack se Import Data add kiya)
  const [showChatbot, setShowChatbot] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setShowChatbot(localStorage.getItem("profitpilot_show_chatbot") === "true");
    }
  }, []);

  const dashboardMenu = [
    { label: "Overview", href: "/", icon: <DashboardIcon size={18} /> },
    ...(showChatbot ? [{ label: "AI Chatbot", href: "/chatbot", icon: <ChatbotIcon size={18} /> }] : []),
    { label: "Import Data", href: "/import", icon: <FileUpIcon size={18} /> },
  ];

  // Business section (Kushal-dev se)
  const businessMenu = [
    { label: "Transactions", href: "/transactions", icon: <ReceiptIcon size={18} /> },
    { label: "Inventory", href: "/inventory", icon: <PackageIcon size={18} /> },
    { label: "Staff", href: "/staff", icon: <UsersIcon size={18} /> },
    { label: "Alerts", href: "/alerts", icon: <AlertTriangleIcon size={18} /> },
  ];

  // System section (Kushal-dev se)
  const systemMenu = [
    { label: "Profile", href: "/profile", icon: <SparklesIcon size={18} /> },
    { label: "Settings", href: "/settings", icon: <SettingsIcon size={18} /> },

  ];

  return (
    <>
      <div
        className={`sidebar-backdrop ${isOpen ? "open" : ""}`}
        aria-hidden="true"
        onClick={onClose}
      />
      <aside
        id="dashboard-sidebar"
        className={`sidebar ${isOpen ? "open" : ""}`}
      >
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-icon"></div>
          <span className="logo-text">ProfitPilot</span>
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <XIcon size={18} />
          </button>
        </div>

      {/* Management Section */}
      <nav className="sidebar-nav">
        <div className="sidebar-section">
          <div className="sidebar-section-title">Management</div>
        </div>
        {dashboardMenu.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link ${pathname === item.href ? "active" : ""}`}
            onClick={onClose}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Business Section */}
      <nav className="sidebar-nav" style={{ marginTop: "16px" }}>
        <div className="sidebar-section">
          <div className="sidebar-section-title">Business</div>
        </div>
        {businessMenu.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link ${pathname === item.href ? "active" : ""}`}
            onClick={onClose}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* System Section */}
      <nav className="sidebar-nav" style={{ marginTop: "16px" }}>
        <div className="sidebar-section">
          <div className="sidebar-section-title">System</div>
        </div>
        {systemMenu.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link ${pathname === item.href ? "active" : ""}`}
            onClick={onClose}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Logout button (Optional but useful from testsparkhack) */}
      <div className="sidebar-footer" style={{ marginTop: 'auto' }}>
        <button
          type="button"
          onClick={() => {
            onClose?.();
            clearProfitPilotSession();
            window.location.href = LANDING_PAGE_URL.replace(/\/$/, "");
          }}
          className="nav-link logout-btn"
          style={{ background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', width: '100%', color: '#94A3B8' }}
        >
          <span className="nav-icon">🚪</span>
          <span>Logout</span>
        </button>
      </div>
      </aside>
    </>
  );
}
