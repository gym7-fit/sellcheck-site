// Geführter Ablauf der Tools-Seite: Schritte, Freischaltung, automatisches Weiterscrollen, Überprüfung.
// Die Regeln selbst stehen in wizard-lib.js (getestet). Hier steht nur die Oberfläche.
(function () {
  "use strict";
  const SC = window.SellCheck;
  const W = window.SCWizard;
  const T = window.SCTax;
  const $ = (id) => document.getElementById(id);
  const STATE_KEY = "sellcheck.wizard.v1";
  const SETTINGS_KEY = "sellcheck.settings.v1"; // vom Report gelesen
  const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
  const money = (c) => eur.format(c / 100);

  // Tastaturbedienung merken: Der Fokusring auf den Schritt-Überschriften soll nur nach Tastatureingaben erscheinen.
  // Safari zeigt :focus-visible sonst auch nach einem Fingertipp, wenn der Fokus nach dem Weiterspringen verschoben wird.
  document.addEventListener("keydown", () => document.documentElement.classList.add("kb"), true);
  document.addEventListener("pointerdown", () => document.documentElement.classList.remove("kb"), true);
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const platformNames = SC.PLATFORMS.map((p) => p.name);
  const el = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };

  /* ---------- Zustand ---------- */
  function load() {
    try {
      return W.sanitizeState(JSON.parse(localStorage.getItem(STATE_KEY) || "{}"), platformNames);
    } catch {
      return W.sanitizeState({}, platformNames);
    }
  }
  let state = load();
  function save() {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch { /* Speicher gesperrt */ }
    // Dieselben Angaben für den Report, ohne dass er den Ablauf kennen muss.
    const settings = T.sanitizeSettings({ mode: state.mode || "business", vat: state.vat || "small", rate: state.rate, name: state.name, taxId: state.taxId });
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch { /* ignorieren */ }
  }
  const currentYear = () => state.year || new Date().getFullYear();

  // Startjahr: das jüngste Jahr mit Daten, sonst das laufende.
  if (!state.year) {
    const years = SC.sales.map((s) => Number(s.date.slice(0, 4))).sort((a, b) => b - a);
    state.year = years[0] || new Date().getFullYear();
  }

  /* ---------- Hilfen ---------- */
  const live = (text) => { const n = $("sr-live"); n.textContent = ""; setTimeout(() => (n.textContent = text), 50); };
  const open = new Set(); // Schritte, die gerade bewusst offen gehalten werden
  let lastProgress = null;
  let prevDone = null;
  let prevActive = null;
  let view = "wizard";

  function scrollToStep(n, focus) {
    const target = n > 6 ? $("wiz-end") : $("step-" + n);
    if (!target) return;
    target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    if (focus && n <= 6) {
      const h = $("step-" + n + "-title");
      setTimeout(() => h && h.focus({ preventScroll: true }), reduceMotion ? 0 : 450);
    }
  }

  // Nach einem erfüllten Schritt: kurz sichtbar lassen, dann zum nächsten offenen Schritt scrollen.
  let advanceTimer = null;
  function advanceFrom(n, delay) {
    clearTimeout(advanceTimer);
    advanceTimer = setTimeout(() => {
      open.delete(n);
      const p = render();
      const next = p.active;
      if (next <= 6) live(`Schritt ${n} ist erledigt. Weiter mit Schritt ${next}: ${W.STEPS[next - 1].title}.`);
      else live("Alle Schritte sind erledigt. Du kannst jetzt alles überprüfen.");
      scrollToStep(next, true);
    }, delay);
  }

  /* ---------- Bausteine der Oberfläche ---------- */
  function fillYears() {
    const sel = $("w-year");
    const now = new Date().getFullYear();
    const years = new Set([now, now - 1, now - 2, state.year]);
    SC.sales.forEach((s) => years.add(Number(s.date.slice(0, 4))));
    const sorted = [...years].filter(Boolean).sort((a, b) => b - a);
    sel.replaceChildren(...sorted.map((y) => { const o = el("option", String(y)); o.value = String(y); return o; }));
    sel.value = String(state.year);
  }

  function buildPlatformChips() {
    const box = $("w-platforms");
    box.replaceChildren();
    platformNames.forEach((name) => {
      const label = el("label", undefined, "chip");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = name;
      cb.checked = state.platforms.includes(name);
      label.append(cb, el("span", name));
      box.append(label);
    });
  }

  function syncInputs() {
    $("w-year").value = String(state.year);
    document.querySelectorAll('input[name="w-mode"]').forEach((r) => (r.checked = r.value === state.mode));
    document.querySelectorAll('input[name="w-vat"]').forEach((r) => (r.checked = r.value === state.vat));
    $("w-rate").value = String(state.rate);
    $("x-name").value = state.name;
    $("x-taxid").value = state.taxId;
  }

  // Meldegrenzen-Plattform passend zur Auswahl: die gewählten Plattformen stehen oben in den Auswahllisten.
  function preferPlatforms() {
    const sel = $("t-platform");
    if (!sel || !state.platforms.length) return;
    const chosen = state.platforms;
    const opts = [...sel.options].map((o) => o.value);
    const ordered = [...chosen.filter((n) => opts.includes(n)), ...opts.filter((n) => !chosen.includes(n))];
    const keep = sel.value;
    sel.replaceChildren(...ordered.map((n) => { const o = el("option", n); o.value = n; return o; }));
    sel.value = chosen.includes(keep) ? keep : ordered[0];
  }

  /* ---------- Zusammenfassungen je Schritt ---------- */
  function summary(n, p) {
    const modeText = state.mode === "business" ? "Gewerblich" : "Privat";
    switch (n) {
      case 1:
        return `${state.year} · ${modeText}` + (state.mode === "business" ? ` · ${state.vat === "small" ? "Kleinunternehmer" : "Regelbesteuerung " + state.rate + " %"}` : "");
      case 2:
        return state.platforms.join(", ");
      case 3: {
        const stock = W.entriesOfYear(SC.sales, state.year).filter((s) => s.status === "stock").length;
        return `${p.count} ${p.count === 1 ? "Eintrag" : "Einträge"} für ${state.year}` + (stock ? `, davon ${stock} im Bestand` : "");
      }
      case 4:
        return p.incomplete.length === 0 ? "Alles vollständig" : `${p.incomplete.length} ohne Angabe, bewusst übersprungen`;
      case 5: {
        const r = T.computeEuer(SC.sales, { year: state.year, vat: state.vat || "small", rate: state.rate });
        const hit = r.byPlatform.filter((x) => x.meldegrenze).map((x) => x.platform);
        return hit.length ? `Grenze erreicht bei: ${hit.join(", ")}` : "Keine Plattform an der Grenze";
      }
      case 6:
        return state.name || state.taxId ? "Angaben gespeichert" : "Keine Angaben (freiwillig)";
      default:
        return "";
    }
  }

  const lockText = (n) => `Wird frei, sobald Schritt ${n - 1} abgeschlossen ist.`;

  /* ---------- Schritt 4: fehlende Angaben ---------- */
  const FIX_LIMIT = 25;
  function renderFix(p) {
    const body = $("fix-body");
    const head = $("fix-head");
    const list = p.incomplete;
    $("fix-ok").hidden = list.length > 0;
    $("fix-wrap").hidden = list.length === 0;
    const priv = state.mode === "private";
    $("help-4").textContent = priv
      ? "Für die private Auswertung brauchen wir bei jedem Verkauf die Art des Gegenstands. Kleidung und Alltagsgegenstände sind meist nicht steuerbar."
      : "Bei importierten Verkäufen fehlt oft der Einkaufspreis. Ohne ihn wirkt dein Gewinn zu hoch. Das Einkaufsdatum ist freiwillig, hilft aber bei der richtigen Zuordnung zum Jahr.";
    if (!list.length) { head.replaceChildren(); body.replaceChildren(); $("fix-bulk").replaceChildren(); return; }

    // Fokus merken, damit das Neuzeichnen nicht stört
    const act = document.activeElement;
    const focusKey = act && body.contains(act) ? { id: act.dataset.id, field: act.dataset.field } : null;

    const needBuy = list.some((x) => x.missing.includes("buy"));
    const needKind = list.some((x) => x.missing.includes("kind"));
    const cols = ["Datum", "Artikel", "Plattform", "Verkauf"];
    if (needBuy) cols.push("Einkaufspreis (€)");
    if (needKind) cols.push("Art");
    cols.push("Einkaufsdatum (optional)");
    const tr = document.createElement("tr");
    cols.forEach((c, i) => tr.append(el("th", c, i === 3 ? "num" : "")));
    head.replaceChildren(tr);

    const update = (entry, patch) => {
      const next = SC.sales.map((x) => (x.id === entry.id ? { ...x, ...patch } : x));
      if (!SC.commit(next)) $("note-4").textContent = "Speichern nicht möglich (Speicher voll oder gesperrt).";
    };

    body.replaceChildren(
      ...list.slice(0, FIX_LIMIT).map(({ entry, missing }) => {
        const row = document.createElement("tr");
        const td = (t, c) => el("td", t, c);
        row.append(td(T.deDate(entry.date)), td(entry.name), td(entry.platform), td(money(Math.round(entry.sell * 100)), "num"));
        if (needBuy) {
          const c = document.createElement("td");
          if (missing.includes("buy")) {
            const i = document.createElement("input");
            i.type = "number"; i.min = "0"; i.step = "0.01"; i.inputMode = "decimal"; i.className = "inline-num";
            i.placeholder = "z. B. 8,50"; i.dataset.id = entry.id; i.dataset.field = "buy";
            i.setAttribute("aria-label", `Einkaufspreis für ${entry.name}`);
            i.addEventListener("change", () => { const v = parseFloat(i.value); if (Number.isFinite(v) && v > 0) update(entry, { buy: v }); });
            c.append(i);
          } else c.textContent = "✓";
          row.append(c);
        }
        if (needKind) {
          const c = document.createElement("td");
          if (missing.includes("kind")) {
            const s = document.createElement("select");
            s.dataset.id = entry.id; s.dataset.field = "kind";
            s.setAttribute("aria-label", `Gegenstandsart für ${entry.name}`);
            [["", "Bitte wählen"], ["everyday", "Gebrauchsgegenstand"], ["other", "Sonstiges"]].forEach(([v, l]) => { const o = el("option", l); o.value = v; s.append(o); });
            s.addEventListener("change", () => { if (s.value) update(entry, { kind: s.value }); });
            c.append(s);
          } else c.textContent = "✓";
          row.append(c);
        }
        const dc = document.createElement("td");
        const d = document.createElement("input");
        d.type = "date"; d.value = entry.buyDate || ""; d.dataset.id = entry.id; d.dataset.field = "buyDate";
        d.setAttribute("aria-label", `Einkaufsdatum für ${entry.name}`);
        d.addEventListener("change", () => { if (T.validIso(d.value)) update(entry, { buyDate: d.value }); });
        dc.append(d);
        row.append(dc);
        return row;
      })
    );
    $("fix-more").hidden = list.length <= FIX_LIMIT;
    if (list.length > FIX_LIMIT) $("fix-more").textContent = `Angezeigt werden die ersten ${FIX_LIMIT} von ${list.length}. Wenn du diese ergänzt hast, erscheinen die nächsten.`;

    // Sammelaktionen
    const bulk = $("fix-bulk");
    bulk.replaceChildren();
    if (needBuy) {
      const wrap = el("div", undefined, "bulk-item");
      const lab = el("label", "Gleichen Einkaufspreis für alle fehlenden setzen");
      lab.htmlFor = "bulk-buy";
      const row = el("div", undefined, "inline-form");
      const inp = document.createElement("input");
      inp.id = "bulk-buy"; inp.type = "number"; inp.min = "0"; inp.step = "0.01"; inp.placeholder = "€ je Artikel";
      const btn = el("button", "Anwenden", "btn secondary small");
      btn.type = "button";
      btn.addEventListener("click", () => {
        const v = parseFloat(inp.value);
        if (!(v > 0)) { $("note-4").textContent = "Bitte einen Betrag über 0 eingeben."; return; }
        const ids = new Set(list.filter((x) => x.missing.includes("buy")).map((x) => x.entry.id));
        SC.commit(SC.sales.map((x) => (ids.has(x.id) ? { ...x, buy: v } : x)));
      });
      row.append(inp, btn);
      wrap.append(lab, row);
      bulk.append(wrap);
    }
    if (needKind) {
      const btn = el("button", "Alle als Gebrauchsgegenstand markieren (z. B. Kleidung)", "btn secondary small");
      btn.type = "button";
      btn.addEventListener("click", () => {
        const ids = new Set(list.filter((x) => x.missing.includes("kind")).map((x) => x.entry.id));
        SC.commit(SC.sales.map((x) => (ids.has(x.id) ? { ...x, kind: "everyday" } : x)));
      });
      bulk.append(btn);
    }

    if (focusKey) {
      const target = body.querySelector(`[data-id="${CSS.escape(focusKey.id)}"][data-field="${focusKey.field}"]`) || body.querySelector("input, select");
      if (target) target.focus({ preventScroll: true });
    }
  }

  /* ---------- Rendern ---------- */
  function render() {
    const p = W.progress(state, SC.sales);
    lastProgress = p;

    // Neu erfüllte Schritte zuerst erkennen: Sie bleiben kurz offen, damit man die Auswahl bestätigt sieht,
    // und scrollen dann automatisch weiter (Schritt 3 steuern die Ereignisse selbst).
    const detected = [];
    if (prevDone && prevActive !== null) {
      W.STEPS.forEach((st) => {
        if (!prevDone[st.n] && p.done[st.n] && st.n === prevActive && st.n !== 3) detected.push(st.n);
      });
    }
    detected.forEach((n) => open.add(n));

    W.STEPS.forEach((st) => {
      const n = st.n;
      const sec = $("step-" + n);
      const locked = n > p.active;
      const active = n === p.active;
      const done = p.done[n];
      const expanded = open.has(n);
      sec.classList.toggle("is-locked", locked);
      sec.classList.toggle("is-active", active);
      sec.classList.toggle("is-done", done && !active);
      sec.setAttribute("aria-disabled", locked ? "true" : "false");
      const body = $("body-" + n);
      body.hidden = locked || (done && !active && !expanded);
      if (locked) body.setAttribute("inert", ""); else body.removeAttribute("inert");
      const status = $("status-" + n);
      status.textContent = locked ? "Gesperrt" : done && !active ? "✓ Erledigt" : "Jetzt dran";
      status.className = "step-status " + (locked ? "locked" : done && !active ? "done" : "now");
      $("sum-" + n).textContent = locked ? lockText(n) : done ? summary(n, p) : "";
      const editBtn = sec.querySelector(".step-edit");
      editBtn.hidden = !(done && !active && !locked);
      editBtn.textContent = expanded ? "Einklappen" : "Ändern";
      editBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
    });

    // Schritt 1: Zusatzfelder
    $("w-vat-group").hidden = state.mode !== "business";
    $("w-rate-wrap").hidden = !(state.mode === "business" && state.vat === "regular");
    $("hint-1").textContent = !state.mode ? "Wähle aus, wie du verkaufst. Danach geht es automatisch weiter." : state.mode === "business" && !state.vat ? "Wähle noch aus, wie du die Umsatzsteuer behandelst." : "";

    // Schritt 2
    $("next-2").disabled = state.platforms.length === 0;
    $("note-2").textContent = state.platforms.length ? `${state.platforms.length} ${state.platforms.length === 1 ? "Plattform" : "Plattformen"} gewählt.` : "Wähle mindestens eine Plattform.";

    // Schritt 3
    $("next-3").disabled = !p.done[3];
    const years = Object.keys(p.otherYears).sort((a, b) => b - a);
    $("note-3").textContent = p.count ? `${p.count} ${p.count === 1 ? "Eintrag" : "Einträge"} für ${state.year}.` : `Noch keine Verkäufe für ${state.year}.`;
    const hint = $("year-hint");
    if (!p.count && years.length) {
      const y = years[0];
      hint.hidden = false;
      hint.replaceChildren(el("span", `Du hast ${p.otherYears[y]} ${p.otherYears[y] === 1 ? "Eintrag" : "Einträge"} für ${y}, aber keine für ${state.year}. `));
      const b = el("button", `Steuerjahr auf ${y} umstellen`, "btn secondary small");
      b.type = "button";
      b.addEventListener("click", () => setYear(Number(y)));
      hint.append(b);
    } else hint.hidden = true;

    // Schritt 4
    renderFix(p);
    $("note-4").textContent = p.incomplete.length ? `${p.incomplete.length} ${p.incomplete.length === 1 ? "Verkauf braucht" : "Verkäufe brauchen"} noch eine Angabe.` : "";
    $("skip-4").hidden = !(p.incomplete.length && p.done[3] && state.ack[4] !== String(state.year));
    $("next-4").disabled = !p.done[4];

    // Schritt 5 und 6
    $("next-5").disabled = !p.done[4];
    $("next-6").disabled = !p.done[5];

    // Ende
    $("to-review").disabled = !p.canReview;
    $("wiz-end-note").textContent = p.canReview ? "Alle Schritte sind erledigt. Du kannst deine Angaben jetzt prüfen." : `Noch offen: Schritt ${Math.min(p.active, 6)}.`;

    renderStepper(p);

    detected.forEach((n) => advanceFrom(n, n === 1 ? 1000 : 600));
    prevDone = { ...p.done };
    prevActive = p.active;
    return p;
  }

  function renderStepper(p) {
    const ol = $("stepper");
    ol.replaceChildren();
    const items = [...W.STEPS.map((s) => ({ n: s.n, label: s.short })), { n: 7, label: "Prüfen" }];
    items.forEach((it) => {
      const done = it.n <= 6 ? p.done[it.n] && it.n !== p.active : false;
      const locked = it.n <= 6 ? it.n > p.active : !p.canReview;
      const current = it.n === Math.min(p.active, 7) && view === "wizard";
      const li = el("li", undefined, "stepper-item" + (done ? " done" : "") + (locked ? " locked" : "") + (current ? " current" : ""));
      const b = document.createElement("button");
      b.type = "button";
      b.disabled = locked;
      if (current) b.setAttribute("aria-current", "step");
      b.append(el("span", done ? "✓" : String(it.n), "stepper-dot"), el("span", it.label, "stepper-label"));
      b.addEventListener("click", () => {
        if (it.n === 7) { showReview(); return; }
        showWizard();
        if (p.done[it.n] && it.n !== p.active) open.add(it.n);
        render();
        scrollToStep(it.n, true);
      });
      li.append(b);
      ol.append(li);
    });
    const doneCount = W.STEPS.filter((s) => p.done[s.n]).length;
    $("stepper-fill").style.width = (doneCount / W.STEPS.length) * 100 + "%";
    $("stepper-mobile").textContent = view === "review" ? "Überprüfen" : p.active <= 6 ? `Schritt ${p.active} von 6: ${W.STEPS[p.active - 1].title}` : "Alle Schritte erledigt";
  }

  /* ---------- Ereignisse ---------- */
  function setYear(y) {
    state.year = y;
    state.ack[4] = state.ack[4] === String(y) ? state.ack[4] : null;
    save();
    fillYears();
    SC.refresh();
    live(`Steuerjahr ${y} gewählt.`);
  }

  $("w-year").addEventListener("change", () => setYear(Number($("w-year").value)));
  document.querySelectorAll('input[name="w-mode"]').forEach((r) => r.addEventListener("change", () => { state.mode = r.value; save(); render(); }));
  document.querySelectorAll('input[name="w-vat"]').forEach((r) => r.addEventListener("change", () => { state.vat = r.value; save(); render(); }));
  $("w-rate").addEventListener("change", () => { state.rate = Number($("w-rate").value) === 7 ? 7 : 19; save(); render(); });

  $("quiz-apply").addEventListener("click", () => {
    const q = SC.quiz();
    if (q.recommend !== "business" && q.recommend !== "private") return;
    state.mode = q.recommend;
    save();
    syncInputs();
    render();
    live(`Art übernommen: ${q.recommend === "business" ? "gewerblich" : "privat"}.`);
  });

  $("w-platforms").addEventListener("change", () => {
    state.platforms = [...$("w-platforms").querySelectorAll("input:checked")].map((i) => i.value);
    save();
    preferPlatforms();
    render();
  });

  $("next-2").addEventListener("click", () => { state.ack[2] = true; save(); render(); });
  $("next-3").addEventListener("click", () => { open.delete(3); hideToast(); render(); scrollToStep(Math.min(lastProgress.active, 7), true); });
  $("skip-4").addEventListener("click", () => { state.ack[4] = String(state.year); save(); render(); });
  $("next-4").addEventListener("click", () => { render(); scrollToStep(Math.min(lastProgress.active, 7), true); });
  $("next-5").addEventListener("click", () => { state.ack[5] = true; save(); render(); });
  $("next-6").addEventListener("click", () => { state.ack[6] = true; save(); render(); });

  ["x-name", "x-taxid"].forEach((id) => $(id).addEventListener("input", () => {
    state.name = $("x-name").value.slice(0, 80);
    state.taxId = $("x-taxid").value.slice(0, 40);
    save();
  }));

  document.querySelectorAll(".step-edit").forEach((b) => b.addEventListener("click", () => {
    const n = Number(b.dataset.edit);
    if (open.has(n)) open.delete(n); else open.add(n);
    render();
  }));

  /* ---------- Schritt 3: Rückmeldung nach Import und Eintrag ---------- */
  let toastTimer = null;
  function hideToast() {
    clearInterval(toastTimer);
    $("add-toast").hidden = true;
  }
  function showToast(seconds, nextStep) {
    hideToast();
    let left = seconds;
    const text = $("add-toast-text");
    const draw = () => (text.textContent = `Gespeichert ✓ Weiter zu Schritt ${nextStep} in ${left} s.`);
    $("toast-now").hidden = false;
    draw();
    $("add-toast").hidden = false;
    toastTimer = setInterval(() => {
      left -= 1;
      if (left <= 0) {
        hideToast();
        advanceFrom(3, 0);
      } else draw();
    }, 1000);
  }
  $("toast-now").addEventListener("click", () => { hideToast(); advanceFrom(3, 0); });
  $("toast-more").addEventListener("click", () => { hideToast(); $("t-name").focus(); });

  document.addEventListener("sellcheck:added", (ev) => {
    const p = render();
    if (!ev.detail.ok) return;
    open.add(3);
    render();
    if (ev.detail.wrongYear) {
      $("add-toast-text").textContent = `Dieser Eintrag gehört zum Jahr ${ev.detail.year}, nicht zu ${state.year}. Er zählt erst, wenn du das Steuerjahr entsprechend wählst.`;
      $("toast-now").hidden = true;
      $("add-toast").hidden = false;
      return;
    }
    if (p.done[3]) showToast(5, Math.min(p.active, 6));
  });

  document.addEventListener("sellcheck:imported", (ev) => {
    open.add(3);
    const p = render();
    const inYear = ev.detail.byYear[String(state.year)] || 0;
    if (inYear > 0 && p.done[3]) {
      live(`${ev.detail.count} Einträge importiert.`);
      advanceFrom(3, 1500);
    } else {
      live("Import abgeschlossen, aber keine Einträge für das gewählte Jahr.");
    }
  });

  /* ---------- Überprüfung ---------- */
  function row(label, value, goto) {
    const wrap = el("div", undefined, "review-row");
    wrap.append(el("dt", label));
    const dd = el("dd", value);
    if (goto) {
      const b = el("button", "Ändern", "linklike");
      b.type = "button";
      b.dataset.goto = String(goto);
      dd.append(b);
    }
    wrap.append(dd);
    return wrap;
  }

  function buildReview() {
    const p = W.progress(state, SC.sales);
    const business = state.mode === "business";
    const dl = $("r-basics");
    dl.replaceChildren(
      row("Steuerjahr", String(state.year), 1),
      row("Art", business ? "Gewerblich (Anlage EÜR)" : "Privat (Anlage SO prüfen)", 1)
    );
    if (business) dl.append(row("Umsatzsteuer", state.vat === "small" ? "Kleinunternehmer (§ 19 UStG)" : `Regelbesteuerung, ${state.rate} %`, 1));
    dl.append(row("Plattformen", state.platforms.join(", ") || "–", 2));
    dl.append(row("Name auf dem Report", state.name || "nicht angegeben", 6));
    dl.append(row("Steuernummer", state.taxId || "nicht angegeben", 6));

    const entries = W.entriesOfYear(SC.sales, state.year);
    const sold = entries.filter((e) => e.status !== "stock");
    const stock = entries.length - sold.length;
    const stat = (v, l, c) => { const d = el("div", undefined, "stat"); d.append(el("div", v, "v" + (c ? " " + c : "")), el("div", l, "l")); return d; };
    $("r-stats").replaceChildren(stat(String(sold.length), "Verkäufe"), stat(String(stock), "Im Bestand"), stat(String(new Set(entries.map((e) => e.platform)).size), new Set(entries.map((e) => e.platform)).size === 1 ? "Plattform" : "Plattformen"));

    const byPlat = new Map();
    sold.forEach((e) => { const r = byPlat.get(e.platform) || { n: 0, sum: 0 }; r.n++; r.sum += Math.round(e.sell * 100); byPlat.set(e.platform, r); });
    $("r-platforms").replaceChildren(...[...byPlat].map(([name, r]) => { const li = el("li"); li.append(el("b", name), document.createTextNode(`: ${r.n} ${r.n === 1 ? "Verkauf" : "Verkäufe"} · ${money(r.sum)}`)); return li; }));

    const checks = $("r-checks");
    checks.replaceChildren();
    const item = (level, text) => { const li = el("li", undefined, "check-item " + level); li.append(el("span", level === "ok" ? "✓" : level === "warn" ? "!" : "i", "check-mark"), el("span", text)); return li; };
    const lim = $("r-limits");
    lim.replaceChildren();

    const r = T.computeEuer(SC.sales, { year: state.year, vat: state.vat || "small", rate: state.rate });
    r.byPlatform.forEach((x) => {
      const ratio = Math.max(x.count / T.MELDE_COUNT, x.revenue / (T.MELDE_SUM * 100));
      const lvl = !x.reported ? "none" : ratio >= 1 ? "red" : ratio >= 0.6 ? "yellow" : "green";
      const txt = !x.reported ? "keine Meldung" : lvl === "red" ? "Grenze erreicht" : lvl === "yellow" ? "nähert sich" : "weit entfernt";
      const chip = el("div", undefined, "limit-chip " + lvl);
      chip.append(el("b", x.platform), el("span", `${x.count} Verkäufe · ${money(x.revenue)} · ${txt}`));
      lim.append(chip);
    });
    if (!r.byPlatform.length) lim.append(el("p", "Keine Verkäufe im gewählten Jahr.", "muted"));

    if (business) {
      $("r-result").replaceChildren(
        stat(money(r.revenueNet), state.vat === "regular" ? "Einnahmen netto" : "Betriebseinnahmen"),
        stat(money(r.expensesTotal), "Betriebsausgaben"),
        stat(money(r.profit), "Gewinn / Verlust", r.profit >= 0 ? "pos" : "neg")
      );
      if (r.dataComplete) checks.append(item("ok", "Keine Datenlücken gefunden, die das Ergebnis verfälschen."));
      r.warnings.forEach((w) => checks.append(item(w.level === "warn" ? "warn" : "info", w.text)));
    } else {
      const pr = T.computePrivate(SC.sales, { year: state.year });
      $("r-result").replaceChildren(
        stat(String(pr.freeCount), "nicht steuerbar"),
        stat(String(pr.relevantCount), "zu prüfen (≤ 1 Jahr)"),
        stat(money(pr.totalProfit), "Gewinn dieser Verkäufe", pr.totalProfit >= 0 ? "pos" : "neg")
      );
      if (pr.checkCount) checks.append(item("warn", `${pr.checkCount} Verkäufe sind nicht einzuordnen, weil Angaben fehlen.`));
      checks.append(item(pr.belowFreigrenze ? "ok" : "warn", pr.belowFreigrenze
        ? `Der Gesamtgewinn liegt unter der Freigrenze von ${pr.freigrenze.toLocaleString("de-DE")} € (§ 23 Abs. 3 EStG). Keine Steuerberatung, bitte prüfen.`
        : `Der Gesamtgewinn erreicht die Freigrenze von ${pr.freigrenze.toLocaleString("de-DE")} €. Dann wäre der gesamte Gewinn steuerpflichtig. Bitte steuerlich klären.`));
    }
    if (p.incomplete.length && state.ack[4] === String(state.year)) checks.append(item("warn", `${p.incomplete.length} Verkäufe haben noch fehlende Angaben. Das Ergebnis ist deshalb vorläufig.`));

    updateGateStatus();
    $("x-report").href = "report.html?y=" + encodeURIComponent(state.year);
    $("x-journal").hidden = !business;
    $("x-summary").hidden = !business;
    $("x-private").hidden = business;
    $("r-export-note").textContent = business
      ? "Der Report ist eine Ausfüllhilfe für die Anlage EÜR zum Abtippen in Mein ELSTER. Das Journal ist für deinen Steuerberater. Es wird nichts ans Finanzamt übertragen."
      : "Die Aufstellung bereitet die Anlage SO vor. Einordnung und Eintrag prüfst du selbst oder mit Beratung. Es wird nichts ans Finanzamt übertragen.";
  }

  function showReview() {
    const p = W.progress(state, SC.sales);
    if (!p.canReview) return;
    if (window.SCGate && !window.SCGate.unlocked()) {
      window.SCGate.require(showReview); // Formular, danach geht es hier weiter
      return;
    }
    view = "review";
    $("view-wizard").hidden = true;
    $("view-review").hidden = false;
    buildReview();
    renderStepper(p);
    if (location.hash !== "#review") history.pushState(null, "", "#review");
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    setTimeout(() => $("review-title").focus({ preventScroll: true }), 50);
    live("Überprüfung geöffnet.");
  }

  function showWizard() {
    if (view === "wizard") return;
    view = "wizard";
    $("view-review").hidden = true;
    $("view-wizard").hidden = false;
    if (location.hash === "#review") history.pushState(null, "", location.pathname + location.search);
    render();
  }

  $("to-review").addEventListener("click", showReview);
  $("back-wizard").addEventListener("click", () => { showWizard(); scrollToStep(7, false); });
  $("view-review").addEventListener("click", (e) => {
    const b = e.target.closest("[data-goto]");
    if (!b) return;
    const n = Number(b.dataset.goto);
    showWizard();
    open.add(n);
    render();
    scrollToStep(n, true);
  });
  window.addEventListener("popstate", () => { if (location.hash === "#review") showReview(); else showWizard(); });

  /* ---------- Exporte ---------- */
  const gated = (fn) => () => (window.SCGate ? window.SCGate.require(fn) : fn());

  function run(kind) {
    const year = state.year;
    const settings = T.sanitizeSettings({ mode: state.mode, vat: state.vat, rate: state.rate });
    if (kind === "private") SC.download(T.privateCsv(T.computePrivate(SC.sales, { year })), `sellcheck-anlage-so-${year}.csv`);
    else {
      const r = T.computeEuer(SC.sales, { year, vat: settings.vat, rate: settings.rate });
      SC.download(kind === "journal" ? T.journalCsv(r) : T.summaryCsv(r), `sellcheck-${kind === "journal" ? "journal" : "summen"}-${year}.csv`);
    }
    $("x-msg").textContent = "Datei erstellt. Sie liegt in deinem Download-Ordner.";
  }
  $("x-report-dl").addEventListener("click", gated(async () => {
    const html = await window.SCReport.buildHtml(state.year);
    if (!html) { $("x-msg").textContent = "Für dieses Jahr gibt es keine Daten für einen Report."; return; }
    SC.download(html, `sellcheck-report-${state.year}.html`, "text/html;charset=utf-8");
    $("x-msg").textContent = "Report erstellt. Die Datei liegt in deinem Download-Ordner und lässt sich im Browser öffnen und drucken.";
  }));
  $("x-journal").addEventListener("click", gated(() => run("journal")));
  $("x-summary").addEventListener("click", gated(() => run("summary")));
  $("x-private").addEventListener("click", gated(() => run("private")));
  $("x-backup").addEventListener("click", gated(() => { $("t-export").click(); $("x-msg").textContent = "Sicherung erstellt. Sie liegt in deinem Download-Ordner."; }));

  /* ---------- Report per E-Mail ---------- */
  function summaryText() {
    const year = state.year;
    const business = state.mode === "business";
    const L = [`SellCheck: Zusammenfassung ${year}`, `Art: ${business ? "Gewerblich (Anlage EÜR)" : "Privat (Anlage SO prüfen)"}`, ""];
    const r = T.computeEuer(SC.sales, { year, vat: state.vat || "small", rate: state.rate });
    if (business) {
      L.push(`${state.vat === "regular" ? "Einnahmen netto" : "Betriebseinnahmen"}: ${money(r.revenueNet)}`, `Betriebsausgaben: ${money(r.expensesTotal)}`, `Gewinn / Verlust: ${money(r.profit)}`);
    } else {
      const pr = T.computePrivate(SC.sales, { year });
      L.push(`Nicht steuerbar: ${pr.freeCount}`, `Zu prüfen (höchstens 1 Jahr): ${pr.relevantCount}`, `Gewinn dieser Verkäufe: ${money(pr.totalProfit)}`);
    }
    L.push("", "Plattformen und Meldegrenze:");
    r.byPlatform.forEach((x) => {
      const ratio = Math.max(x.count / T.MELDE_COUNT, x.revenue / (T.MELDE_SUM * 100));
      const txt = !x.reported ? "keine Meldung" : ratio >= 1 ? "Grenze erreicht" : ratio >= 0.6 ? "nähert sich" : "weit entfernt";
      L.push(`- ${x.platform}: ${x.count} Verkäufe, ${money(x.revenue)}, ${txt}`);
    });
    L.push("", "Orientierung, keine Steuer- oder Rechtsberatung. Alle Angaben ohne Gewähr.");
    return L.join("\n");
  }

  async function mailPayload(lead) {
    const year = state.year;
    const business = state.mode === "business";
    const files = [];
    if (business) {
      const r = T.computeEuer(SC.sales, { year, vat: state.vat || "small", rate: state.rate });
      files.push({ name: `sellcheck-journal-${year}.csv`, type: "text/csv", content: T.journalCsv(r) }, { name: `sellcheck-summen-${year}.csv`, type: "text/csv", content: T.summaryCsv(r) });
    } else {
      files.push({ name: `sellcheck-anlage-so-${year}.csv`, type: "text/csv", content: T.privateCsv(T.computePrivate(SC.sales, { year })) });
    }
    const html = await window.SCReport.buildHtml(year);
    if (html) files.unshift({ name: `sellcheck-report-${year}.html`, type: "text/html", content: html });
    return { email: lead.email, type: "report", year, mode: state.mode, summary: summaryText(), files };
  }

  function prepareMailto() {
    const lead = window.SCGate && window.SCGate.lead();
    const a = $("x-mailto");
    if (!lead) { a.hidden = true; return; }
    a.href = window.SCGateLib.mailtoHref(lead.email, `SellCheck: Zusammenfassung ${state.year}`, summaryText());
    a.hidden = !a.href;
  }

  async function sendReportMail(auto) {
    const lead = window.SCGate && window.SCGate.lead();
    if (!lead) return;
    const cfg = window.SCGate.config();
    const msg = $("x-msg");
    if (!cfg.reportEndpoint) {
      prepareMailto();
      msg.textContent = "Der automatische Versand ist in dieser Vorabversion noch nicht eingerichtet. Mit „Zusammenfassung im Mailprogramm öffnen“ erstellst du die Nachricht an deine Adresse selbst.";
      return;
    }
    msg.textContent = "Report wird gesendet …";
    const res = await window.SCGate.sendReport(await mailPayload(lead));
    if (res.ok) {
      window.SCGate.markReportSent();
      msg.textContent = `Der Report wurde an ${lead.email} gesendet.`;
    } else {
      msg.textContent = "Der Report konnte nicht gesendet werden. Du kannst ihn weiterhin hier ansehen und herunterladen.";
    }
  }
  $("x-mail").addEventListener("click", () => sendReportMail(false));

  let autoTried = false; // Versand aus dem Formular höchstens einmal je Seitenaufruf anstoßen

  function updateGateStatus() {
    const note = $("gate-status");
    const lead = window.SCGate && window.SCGate.lead();
    note.replaceChildren();
    prepareMailto();
    if (!lead) return;
    note.append(document.createTextNode(`Freigeschaltet für ${lead.email}. `));
    const change = el("button", "Adresse ändern", "linklike");
    change.type = "button";
    change.addEventListener("click", () => { window.SCGate.clear(); showWizard(); scrollToStep(7, false); });
    note.append(change);
    if (lead.delivery === "demo") note.append(document.createTextNode(" Vorabversion: Die Adresse wurde nicht gespeichert oder gesendet."));
    else if (lead.delivery === "failed") note.append(document.createTextNode(" Die Adresse konnte nicht übermittelt werden. Das Ergebnis bleibt freigeschaltet."));
    if (lead.report && !lead.reportSent && view === "review" && !autoTried) { autoTried = true; sendReportMail(true); }
  }

  /* ---------- Start ---------- */
  fillYears();
  buildPlatformChips();
  syncInputs();
  preferPlatforms();
  save();
  SC.onRefresh(() => { if (view === "wizard") render(); else buildReview(); });
  SC.refresh(); // zeichnet Tracker und Überblick für das gewählte Jahr neu und ruft render()
  const first = render();

  if (location.hash === "#review" && first.canReview) showReview();
  else if (first.active > 1 && first.active <= 7) setTimeout(() => scrollToStep(first.active, false), 150);
})();
