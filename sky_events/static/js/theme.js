/**
 * theme.js — Dark / light mode initialiser
 *
 * Runs BEFORE first paint (included at end of <head>) to prevent FOUC.
 * Reads from localStorage, falls back to OS preference.
 * Exposes window.SkyTheme.toggle() for the toggle button.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "sky-theme";
  const CLASS_DARK = "dark";

  function getPreferred() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.classList.add(CLASS_DARK);
    } else {
      document.documentElement.classList.remove(CLASS_DARK);
    }
  }

  // Apply immediately — before CSS renders
  applyTheme(getPreferred());

  // Public API used by the toggle button
  window.SkyTheme = {
    get: function () {
      return document.documentElement.classList.contains(CLASS_DARK)
        ? "dark"
        : "light";
    },
    set: function (theme) {
      localStorage.setItem(STORAGE_KEY, theme);
      applyTheme(theme);
      document.querySelectorAll("[data-theme-icon]").forEach(function (el) {
        el.setAttribute(
          "data-theme-icon",
          theme === "dark" ? "dark" : "light"
        );
      });
    },
    toggle: function () {
      var next = window.SkyTheme.get() === "dark" ? "light" : "dark";
      window.SkyTheme.set(next);
    },
  };
})();
