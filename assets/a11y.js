/* Plantwick accessibility toolbar - self-hosted, no dependencies.
   Provides font scaling, high contrast, link highlight, readable font.
   Settings persist via localStorage. */
(function () {
  "use strict";
  var KEY = "leaflore-a11y";
  var html = document.documentElement;
  var state = { font: 0, contrast: false, links: false, readable: false };

  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    Object.assign(state, saved);
  } catch (e) {}

  var FONT_STEPS = [100, 112, 125, 140, 160];

  function apply() {
    html.style.fontSize = FONT_STEPS[state.font] + "%";
    html.classList.toggle("a11y-contrast", state.contrast);
    html.classList.toggle("a11y-links", state.links);
    html.classList.toggle("a11y-readable", state.readable);
    var c = document.getElementById("a11y-contrast-btn");
    var l = document.getElementById("a11y-links-btn");
    var r = document.getElementById("a11y-readable-btn");
    if (c) c.setAttribute("aria-pressed", state.contrast);
    if (l) l.setAttribute("aria-pressed", state.links);
    if (r) r.setAttribute("aria-pressed", state.readable);
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  function update() { apply(); save(); }

  document.addEventListener("DOMContentLoaded", function () {
    var fab = document.getElementById("a11y-fab");
    var panel = document.getElementById("a11y-panel");
    if (!fab || !panel) { apply(); return; }

    function toggle(open) {
      var willOpen = open !== undefined ? open : panel.hidden;
      panel.hidden = !willOpen;
      fab.setAttribute("aria-expanded", willOpen);
      if (willOpen) { var b = panel.querySelector("button"); if (b) b.focus(); }
    }

    fab.addEventListener("click", function () { toggle(); });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !panel.hidden) { toggle(false); fab.focus(); }
    });
    document.addEventListener("click", function (e) {
      if (!panel.hidden && !panel.contains(e.target) && e.target !== fab) toggle(false);
    });

    panel.addEventListener("click", function (e) {
      var act = e.target.getAttribute && e.target.getAttribute("data-a11y");
      if (!act) return;
      if (act === "font-up") state.font = Math.min(state.font + 1, FONT_STEPS.length - 1);
      else if (act === "font-down") state.font = Math.max(state.font - 1, 0);
      else if (act === "contrast") state.contrast = !state.contrast;
      else if (act === "links") state.links = !state.links;
      else if (act === "readable") state.readable = !state.readable;
      else if (act === "reset") state = { font: 0, contrast: false, links: false, readable: false };
      update();
    });

    apply();
  });
})();
