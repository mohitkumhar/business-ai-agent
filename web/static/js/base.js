/* ──────────────────────────────────────────────────────────────────
   base.js – Sidebar toggling & clock
   ────────────────────────────────────────────────────────────────── */

(function () {
    "use strict";

    const sidebar        = document.getElementById("sidebar");
    const sidebarToggle  = document.getElementById("sidebarToggle");
    const mobileToggle   = document.getElementById("mobileToggle");
    const overlay        = document.getElementById("overlay");
    const dateTimeEl     = document.getElementById("currentDateTime");

    // Desktop collapse
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    // Mobile open / close
    if (mobileToggle) {
        mobileToggle.addEventListener("click", () => {
            sidebar.classList.toggle("mobile-open");
            overlay.classList.toggle("active");
        });
    }
    if (overlay) {
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("mobile-open");
            overlay.classList.remove("active");
        });
    }

    // Live clock
    function updateClock() {
        if (!dateTimeEl) return;
        const now = new Date();
        dateTimeEl.textContent = now.toLocaleString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }
    updateClock();
    clearInterval(window.__interval); window.__interval = setInterval(updateClock, 1000);
})();
