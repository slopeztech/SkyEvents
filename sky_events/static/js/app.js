/**
 * app.js — SkyEvents general application JS
 *
 * Lightweight vanilla JS. No build step required.
 * Heavy features (charts, maps) can be lazy-loaded per page.
 */
(function () {
  "use strict";

  /* ── Auto-dismiss flash messages ─────────────────────────────────────── */
  document.querySelectorAll("[data-auto-dismiss]").forEach(function (el) {
    var delay = parseInt(el.getAttribute("data-auto-dismiss") || "5000", 10);
    setTimeout(function () {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(function () {
        el.remove();
      }, 400);
    }, delay);
  });

  /* ── Password visibility toggle ──────────────────────────────────────── */
  document.querySelectorAll("[data-password-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-password-toggle");
      var input = document.getElementById(targetId);
      if (!input) return;
      var isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      // Swap icon
      var iconShow = btn.querySelector("[data-icon-show]");
      var iconHide = btn.querySelector("[data-icon-hide]");
      if (iconShow) iconShow.classList.toggle("hidden", !isPassword);
      if (iconHide) iconHide.classList.toggle("hidden", isPassword);
    });
  });

  /* ── Mobile sidebar toggle ───────────────────────────────────────────── */
  var sidebarToggle = document.getElementById("sidebar-toggle");
  var sidebar = document.getElementById("app-sidebar");
  var sidebarOverlay = document.getElementById("sidebar-overlay");

  if (sidebarToggle && sidebar) {
    function openSidebar() {
      sidebar.classList.remove("-translate-x-full");
      if (sidebarOverlay) sidebarOverlay.classList.remove("hidden");
    }
    function closeSidebar() {
      sidebar.classList.add("-translate-x-full");
      if (sidebarOverlay) sidebarOverlay.classList.add("hidden");
    }
    sidebarToggle.addEventListener("click", function () {
      if (sidebar.classList.contains("-translate-x-full")) {
        openSidebar();
      } else {
        closeSidebar();
      }
    });
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener("click", closeSidebar);
    }
  }

  /* ── Action dropdowns ────────────────────────────────────────────────── *
   * Pattern:                                                                *
   *   <div data-dropdown>                                                   *
   *     <button data-dropdown-trigger>…</button>                           *
   *     <div data-dropdown-menu class="hidden">…</div>                     *
   *   </div>                                                                *
   * ─────────────────────────────────────────────────────────────────────── */
  var activeDropdown = null;

  function closeDropdown(wrapper) {
    var menu    = wrapper.querySelector("[data-dropdown-menu]");
    var trigger = wrapper.querySelector("[data-dropdown-trigger]");
    if (!menu) return;
    menu.classList.add("hidden");
    menu.removeAttribute("style");
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    activeDropdown = null;
  }

  function openDropdown(wrapper) {
    var menu    = wrapper.querySelector("[data-dropdown-menu]");
    var trigger = wrapper.querySelector("[data-dropdown-trigger]");
    if (!menu || !trigger) return;

    // Position with fixed so the menu escapes overflow:hidden parents (cards, tables)
    var rect = trigger.getBoundingClientRect();
    menu.style.position = "fixed";
    menu.style.top      = (rect.bottom + 6) + "px";
    menu.style.right    = (window.innerWidth - rect.right) + "px";
    menu.style.left     = "auto";
    menu.style.zIndex   = "9999";

    menu.classList.remove("hidden");
    trigger.setAttribute("aria-expanded", "true");
    activeDropdown = wrapper;
  }

  document.querySelectorAll("[data-dropdown]").forEach(function (wrapper) {
    var trigger = wrapper.querySelector("[data-dropdown-trigger]");
    if (!trigger) return;

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      var menu = wrapper.querySelector("[data-dropdown-menu]");
      var isOpen = menu && !menu.classList.contains("hidden");

      // Close any other open dropdown first
      if (activeDropdown && activeDropdown !== wrapper) {
        closeDropdown(activeDropdown);
      }

      if (isOpen) {
        closeDropdown(wrapper);
      } else {
        openDropdown(wrapper);
      }
    });
  });

  // Close on outside click, Escape, or scroll
  document.addEventListener("click", function () {
    if (activeDropdown) closeDropdown(activeDropdown);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && activeDropdown) closeDropdown(activeDropdown);
  });

  // Reposition on window resize; close on page scroll
  window.addEventListener("resize", function () {
    if (activeDropdown) closeDropdown(activeDropdown);
  });
  window.addEventListener("scroll", function () {
    if (activeDropdown) closeDropdown(activeDropdown);
  }, { passive: true, capture: true });
})();
