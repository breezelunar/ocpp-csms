/**
 * dashboard.js – lightweight client-side logic for the OCPP CSMS dashboard.
 *
 * Features:
 *  - Auto-refresh the current page every 30 seconds.
 *  - Highlight the active nav link.
 *  - Confirm before destructive actions (delete).
 *  - Live relative timestamps.
 */

(function () {
    "use strict";

    const REFRESH_INTERVAL_MS = 30000;

    // ── Active nav link ──────────────────────────────────────────────────────
    function highlightActiveNav() {
        const path = window.location.pathname;
        document.querySelectorAll("nav a").forEach(function (link) {
            const href = link.getAttribute("href");
            if (href && (path === href || (href !== "/" && path.startsWith(href)))) {
                link.classList.add("active");
            }
        });
    }

    // ── Auto-refresh ─────────────────────────────────────────────────────────
    function startAutoRefresh() {
        setTimeout(function () {
            window.location.reload();
        }, REFRESH_INTERVAL_MS);
    }

    // ── Confirm delete ───────────────────────────────────────────────────────
    function bindDeleteConfirm() {
        document.querySelectorAll("[data-confirm]").forEach(function (el) {
            el.addEventListener("click", function (evt) {
                const msg = el.getAttribute("data-confirm") || "Are you sure?";
                if (!window.confirm(msg)) {
                    evt.preventDefault();
                }
            });
        });
    }

    // ── Relative timestamps ──────────────────────────────────────────────────
    function formatRelative(isoString) {
        if (!isoString) return "—";
        const date = new Date(isoString);
        if (isNaN(date)) return isoString;
        const diffMs = Date.now() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);
        if (diffSec < 60) return diffSec + "s ago";
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return diffMin + "m ago";
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return diffHr + "h ago";
        return Math.floor(diffHr / 24) + "d ago";
    }

    function applyRelativeTimestamps() {
        document.querySelectorAll("[data-timestamp]").forEach(function (el) {
            const iso = el.getAttribute("data-timestamp");
            el.textContent = formatRelative(iso);
            el.title = iso;
        });
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", function () {
        highlightActiveNav();
        startAutoRefresh();
        bindDeleteConfirm();
        applyRelativeTimestamps();
    });
}());
