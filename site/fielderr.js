// Fehlermeldung direkt am Feld (statt gesammelt an anderer Stelle): rot, mit Symbol, per Screenreader vorgelesen.
(function () {
  "use strict";
  function box(input) {
    const id = input.id || (input.id = "f" + Math.random().toString(36).slice(2, 7));
    let el = document.getElementById(id + "-err");
    if (!el) {
      el = document.createElement("p");
      el.id = id + "-err";
      el.className = "field-error";
      el.setAttribute("role", "alert");
      const anchor = input.closest(".inline-form") || input.closest("label") || input;
      anchor.insertAdjacentElement("afterend", el);
    }
    return el;
  }
  function clear(input) {
    const el = document.getElementById((input.id || "") + "-err");
    if (el) el.hidden = true;
    input.removeAttribute("aria-invalid");
  }
  function show(input, message, focus) {
    const el = box(input);
    el.textContent = message;
    el.hidden = false;
    input.setAttribute("aria-invalid", "true");
    const ids = (input.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
    if (!ids.includes(el.id)) ids.push(el.id);
    input.setAttribute("aria-describedby", ids.join(" "));
    if (!input.dataset.feBound) {
      input.dataset.feBound = "1";
      input.addEventListener("input", () => clear(input));
      input.addEventListener("change", () => clear(input));
    }
    if (focus !== false) input.focus();
  }
  window.SCField = { show, clear };
})();
