"use client";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { SettingsIcon } from "@/components/Icons";

export default function SettingsPage() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-area">
        <Topbar onSearch={() => {}} />
        <div className="content-wrapper">
          <div className="welcome-banner">
            <div className="welcome-text">
              <h2>Settings</h2>
              <p>Configure your dashboard preferences and AI settings</p>
            </div>
          </div>
          
          <div className="table-card mt-6 p-8 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
              <SettingsIcon size={32} color="var(--text-muted)" />
            </div>
            <h3 className="text-xl font-bold mb-2">Settings under construction</h3>
            <p className="text-slate-500 mb-8">We&apos;re working on making this page available soon!</p>

            <div className="w-full max-w-sm p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
              <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">Help & Support</h4>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("restart-onboarding-tour"));
                  window.location.href = "/";
                }}
                className="w-full py-3 px-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all flex items-center justify-center gap-2"
              >
                <span>Restart Onboarding Tour</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
