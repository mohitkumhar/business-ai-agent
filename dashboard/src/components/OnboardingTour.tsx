"use client";

import React, { useState, useEffect, useRef } from "react";
import { XIcon } from "./Icons";

interface TourStep {
  id: string;
  target?: string; // CSS selector
  title: string;
  content: string;
  position?: "top" | "bottom" | "left" | "right" | "center";
}

const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    title: "Welcome to ProfitPilot! 🚀",
    content: "We're excited to have you here. Let's take a quick tour of your new business AI dashboard.",
    position: "center",
  },
  {
    id: "sidebar",
    target: "#dashboard-sidebar",
    title: "Navigation Sidebar",
    content: "Easily switch between Overview, AI Chatbot, Transactions, and more from here.",
    position: "right",
  },
  {
    id: "kpi-cards",
    target: '[data-widget-id="kpi-cards"]',
    title: "Vital Metrics",
    content: "Track your Total Revenue, Expenses, Net Profit, and Active Alerts at a glance.",
    position: "bottom",
  },
  {
    id: "charts",
    target: '[data-widget-id="revenue-vs-expenses"]',
    title: "Performance Trends",
    content: "Visualize your revenue and expenses over time to identify growth patterns.",
    position: "top",
  },
  {
    id: "alerts",
    target: "#tour-alerts",
    title: "Smart Alerts",
    content: "Stay notified about critical inventory levels, anomalies, or financial risks.",
    position: "right",
  },
  {
    id: "chatbot",
    target: "#tour-chatbot",
    title: "AI Business Assistant",
    content: "Ask natural language questions like 'What was my best selling product last month?'",
    position: "right",
  },
  {
    id: "import",
    target: "#tour-import",
    title: "Data Integration",
    content: "Quickly upload your CSV or Excel files to sync your business data.",
    position: "right",
  },
  {
    id: "settings",
    target: "#tour-settings",
    title: "Customization",
    content: "Adjust your account preferences and notification settings here.",
    position: "right",
  },
  {
    id: "completion",
    title: "You're All Set! 🎉",
    content: "Feel free to explore and ask our AI anything. Your data is now working for you.",
    position: "center",
  },
];

export default function OnboardingTour() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0, height: 0 });
  const [isVisible, setIsVisible] = useState(false);
  const tourRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const hasCompleted = localStorage.getItem("onboarding_tour_completed");
    if (!hasCompleted) {
      setTimeout(() => {
        setCurrentStep(0);
        setIsVisible(true);
      }, 1500);
    }

    const handleRestart = () => {
        localStorage.removeItem("onboarding_tour_completed");
        setCurrentStep(0);
        setIsVisible(true);
    };

    window.addEventListener("restart-onboarding-tour", handleRestart);
    return () => window.removeEventListener("restart-onboarding-tour", handleRestart);
  }, []);

  useEffect(() => {
    if (currentStep >= 0 && currentStep < TOUR_STEPS.length) {
      const step = TOUR_STEPS[currentStep];
      if (step.target) {
        const element = document.querySelector(step.target);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "center" });
          const rect = element.getBoundingClientRect();
          setCoords({
            top: rect.top + window.scrollY,
            left: rect.left + window.scrollX,
            width: rect.width,
            height: rect.height,
          });
        }
      }
    }
  }, [currentStep]);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      completeTour();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const completeTour = () => {
    setIsVisible(false);
    setCurrentStep(-1);
    localStorage.setItem("onboarding_tour_completed", "true");
  };

  if (!isVisible || currentStep < 0) return null;

  const step = TOUR_STEPS[currentStep];
  const isCenter = step.position === "center" || !step.target;

  return (
    <div className="fixed inset-0 z-[10000] pointer-events-none">
      {/* Overlay with Spotlight */}
      <div 
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-[2px] transition-all duration-500 pointer-events-auto"
        style={{
          clipPath: step.target 
            ? `polygon(0% 0%, 0% 100%, ${coords.left}px 100%, ${coords.left}px ${coords.top}px, ${coords.left + coords.width}px ${coords.top}px, ${coords.left + coords.width}px ${coords.top + coords.height}px, ${coords.left}px ${coords.top + coords.height}px, ${coords.left}px 100%, 100% 100%, 100% 0%)`
            : "none"
        }}
        onClick={completeTour}
      />

      {/* Tooltip Card */}
      <div
        ref={tourRef}
        className="absolute pointer-events-auto transition-all duration-500 ease-out"
        style={
          isCenter
            ? { top: "50%", left: "50%", transform: "translate(-50%, -50%)" }
            : {
                top: step.position === "bottom" ? coords.top + coords.height + 15 : step.position === "top" ? coords.top - 200 : coords.top,
                left: step.position === "right" ? coords.left + coords.width + 20 : coords.left,
                maxWidth: "320px",
              }
        }
      >
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl p-6 border border-indigo-500/30 animate-in fade-in zoom-in duration-300">
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-black uppercase tracking-widest text-indigo-500 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-1 rounded-md">
              Step {currentStep + 1} of {TOUR_STEPS.length}
            </span>
            <button onClick={completeTour} className="text-slate-400 hover:text-slate-600 transition-colors">
              <XIcon size={16} />
            </button>
          </div>
          
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2 leading-tight">
            {step.title}
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-6">
            {step.content}
          </p>

          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <button
                onClick={handleBack}
                className="px-4 py-2 text-xs font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-2.5 px-4 rounded-xl shadow-lg shadow-indigo-500/20 transition-all active:scale-95"
            >
              {currentStep === TOUR_STEPS.length - 1 ? "Get Started" : "Next"}
            </button>
            {currentStep < TOUR_STEPS.length - 1 && (
                <button 
                    onClick={completeTour}
                    className="text-[10px] font-bold text-slate-400 uppercase tracking-wider hover:text-slate-600"
                >
                    Skip
                </button>
            )}
          </div>
        </div>
      </div>

      {/* Spotlight Ring */}
      {step.target && (
        <div
          className="absolute border-2 border-indigo-500 rounded-lg transition-all duration-500 shadow-[0_0_0_9999px_rgba(0,0,0,0)] ring-[0_0_15px_rgba(99,102,241,0.5)]"
          style={{
            top: coords.top - 4,
            left: coords.left - 4,
            width: coords.width + 8,
            height: coords.height + 8,
          }}
        />
      )}
    </div>
  );
}
