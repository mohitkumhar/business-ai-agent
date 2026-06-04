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
            <p className="text-slate-500">We&apos;re working on making this page available soon!</p>
          </div>
        </div>
      </div>
    </div>
  );
}
