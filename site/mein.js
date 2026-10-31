// Oberfläche von mein.html („Mein SellCheck“): Übersicht, Artikel, Meldegrenze, Konto. Logik ohne DOM steht in konto-lib.js, Netz in konto-net.js.
// Nutzerdaten nur über textContent und setAttribute mit festen Namen, kein innerHTML, kein Inline-Skript. Ziele nach dem Laden sind fest (anmelden.html).
(function () {
  "use strict";
  const A = window.SCAuth, K = window.SCKonto, Net = window.SCKontoNet, P = window.SCParse, T = window.SCTax, cfg = window.SC_AUTH;
  const $ = (id) => document.getElementById(id);
  const client = A.createClient({
    url: cfg.supabaseUrl, anonKey: cfg.supabaseAnonKey, storage: window.localStorage,
    redirectTo: new URL("bestaetigt.html", window.location.href).href,
  });
  const store = Net.createStore({ url: cfg.supabaseUrl, anonKey: cfg.supabaseAnonKey, client });

  const SYNC_MIN_MS = 60000;
  const MAX_EDGE = 1400, JPEG_QUALITY = 0.75;
  const state = { rows: new Map(), cursor: null, profile: null, year: new Date().getFullYear(), tab: "uebersicht", filter: "all", query: "", lastSync: 0, syncing: false, saving: false, editing: null, mode: "new", photo: null };
  const thumbs = new Map();   // Foto-Pfad -> blob:-Adresse für die Liste
  let observer = null;

  /* ---------- kleine Helfer ---------- */
  function msg(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.className = "auth-msg" + (kind ? " " + kind : "");
    el.hidden = !text;
  }
  const go = (target) => { window.location.href = target; };   // nur feste Ziele
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  const clear = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };
  const liveRows = () => [...state.rows.values()].filter((r) => !r.deleted_at);
  const today = () => { const n = new Date(); return new Date(n.getTime() - n.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
  const eurosInput = (cents) => (cents > 0 ? (cents / 100).toFixed(2).replace(".", ",") : "");
  function uuid() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    const b = window.crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
    const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  }
  function shortDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])).toLocaleDateString("de-DE", { day: "numeric", month: "short", timeZone: "UTC" }) : "";
  }

  /** Antwort der Netzschicht prüfen. true = Abbruch (abgelaufen oder Fehler, Meldung steht schon oben oder in `into`). */
  function failed(r, into) {
    if (r && r.expired) { go("anmelden.html#abgelaufen"); return true; }
    if (!r || !r.ok) { msg(into || $("msg"), (r && r.message) || "Das hat nicht geklappt. Versuche es später noch einmal.", "error"); return true; }
    return false;
  }

  /* ---------- Reiter ---------- */
  const tabButtons = () => [...document.querySelectorAll('[role="tab"]')];
  function setTab(name, o) {
    const tab = K.TABS.includes(name) ? name : "uebersicht";
    state.tab = tab;
    for (const b of tabButtons()) {
      const on = b.dataset.tab === tab;
      b.setAttribute("aria-selected", String(on));
      b.setAttribute("tabindex", on ? "0" : "-1");
      $("panel-" + b.dataset.tab).hidden = !on;
    }
    if (o && o.focus) $("tab-" + tab).focus();
    if (o && o.hash !== false && window.location.hash !== "#" + tab) {
      try { window.history.replaceState(null, "", "#" + tab); } catch { /* Adresszeile bleibt, wie sie ist */ }
    }
  }
  function wireTabs() {
    for (const b of tabButtons()) b.addEventListener("click", () => setTab(b.dataset.tab, { focus: false }));
    document.querySelector('[role="tablist"]').addEventListener("keydown", (e) => {
      const list = tabButtons(), i = list.findIndex((b) => b.getAttribute("aria-selected") === "true");
      let n = -1;
      if (e.key === "ArrowRight") n = (i + 1) % list.length;
      else if (e.key === "ArrowLeft") n = (i - 1 + list.length) % list.length;
      else if (e.key === "Home") n = 0;
      else if (e.key === "End") n = list.length - 1;
      if (n < 0) return;
      e.preventDefault();
      setTab(list[n].dataset.tab, { focus: true });
    });
    window.addEventListener("hashchange", () => setTab(K.tabFromHash(window.location.hash), { hash: false }));
    document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.goto, { focus: true })));
  }

  /* ---------- Übersicht und Meldegrenze ---------- */
  function renderYears() {
    const years = K.yearsOf(state.rows.size ? [...state.rows.values()] : [], new Date().getFullYear());
    if (!years.includes(state.year)) state.year = years[0];
    for (const sel of document.querySelectorAll("select[data-year]")) {
      clear(sel);
      for (const y of years) { const o = el("option", "", String(y)); o.value = String(y); sel.appendChild(o); }
      sel.value = String(state.year);
      sel.parentNode.hidden = years.length < 2;   // wie in der App: Auswahl nur bei mehr als einem Jahr
    }
  }

  function kpi(title, value, note) {
    const d = el("div", "kpi"), dd = el("dd");
    d.appendChild(el("dt", "", title));
    dd.appendChild(el("span", "v", value));
    dd.appendChild(el("span", "n", note));
    d.appendChild(dd);
    return d;
  }

  const barLevel = (pct) => (pct >= 100 ? "red" : pct >= Math.round(T.MELDE_WARN * 100) ? "yellow" : "green");
  function meterRow(title, value, pct) {
    const row = el("div", "meter-row"), line = el("div", "line");
    line.appendChild(el("span", "", title));
    line.appendChild(el("b", "", value));
    row.appendChild(line);
    const bar = el("progress", barLevel(pct));
    bar.setAttribute("max", "100"); bar.setAttribute("value", String(pct));
    bar.setAttribute("aria-label", title + " " + value);
    row.appendChild(bar);
    return row;
  }
  /** Karte einer Plattform wie PlatformCard in der App: Stufe immer mit Text, Balken nur zusätzlich. */
  function platformCard(p, into, heading) {
    if (heading) into.appendChild(el("h3", "", heading));
    const top = el("div", "plat-top");
    top.appendChild(el(heading ? "p" : "h3", "", p.platform));
    top.appendChild(el("span", "lvl " + (p.reported ? p.level : "none"), K.LEVEL_LABEL[p.reported ? p.level : "none"]));
    into.appendChild(top);
    if (p.reported) {
      into.appendChild(meterRow("Verkäufe", p.count + " von " + T.MELDE_COUNT, K.ratioPct(p.count, T.MELDE_COUNT)));
      into.appendChild(meterRow("Umsatz", K.euro(p.revenue) + " von " + K.euro(T.MELDE_SUM * 100), K.ratioPct(p.revenue, T.MELDE_SUM * 100)));
      into.appendChild(el("p", "hint", K.LEVEL_HINT[p.level] || K.LEVEL_HINT.green));
    } else into.appendChild(el("p", "hint", K.unreportedText(p)));
  }

  function renderOverview() {
    const all = liveRows(), empty = all.length === 0;
    $("ov-empty").hidden = !empty;
    $("ov-content").hidden = empty;
    if (empty) return;
    const y = state.year, s = K.yearStats(all, y, state.profile), st = K.stockStats(all, Date.now());
    const kp = $("kpis");
    clear(kp);
    kp.appendChild(kpi("Umsatz " + y, K.euro(s.revenue), s.vat > 0 ? K.sales(s.sold) + ", brutto" : K.sales(s.sold)));
    kp.appendChild(kpi("Gewinn " + y, K.euro(s.profit), s.vat > 0 ? "nach Einkauf, Kosten und " + K.euro(s.vat) + " USt" : "nach Einkauf und Kosten"));
    kp.appendChild(kpi("Im Lager", st.count + " Artikel", K.euro(st.valueCents) + (st.stale > 0 ? ", " + st.stale + " Ladenhüter" : "")));
    kp.appendChild(kpi("Ø Gewinn je Verkauf", s.sold === 0 ? "–" : K.euro(Math.trunc(s.profit / s.sold)), s.vat > 0 ? "nach USt, vor Einkommensteuer" : "vor Steuern"));
    const box = $("ov-limit");
    clear(box);
    const top = s.platforms.find((p) => p.count > 0 || p.revenue > 0);
    if (top) platformCard(top, box, "Meldegrenze");
    else { box.appendChild(el("h3", "", "Meldegrenze")); box.appendChild(el("p", "muted", "Für " + y + " gibt es noch keine Verkäufe.")); }
    $("ov-limit-link").hidden = !top;
  }

  function renderLimit() {
    const s = K.yearStats(liveRows(), state.year, state.profile), list = $("lim-list");
    clear(list);
    const active = s.platforms.filter((p) => p.count > 0 || p.revenue > 0);
    if (!active.length) { const c = el("div", "plat-card"); c.appendChild(el("p", "muted", "Für " + state.year + " gibt es noch keine Verkäufe.")); list.appendChild(c); }
    for (const p of active) { const c = el("div", "plat-card"); platformCard(p, c); list.appendChild(c); }
    const idle = s.platforms.filter((p) => p.count === 0 && p.revenue === 0 && p.reported).map((p) => p.platform);
    $("lim-idle").hidden = !(idle.length && active.length);
    $("lim-idle").textContent = "Ohne Verkäufe: " + idle.join(", ");
  }

  /* ---------- Fotos ---------- */
  /** Vorschaubilder laden erst, wenn sie sichtbar werden (Lazy Loading: loading="lazy" greift bei blob:-Bildern nicht, das Foto kommt per Anfrage). */
  function ensureObserver() {
    if (observer || typeof IntersectionObserver === "undefined") return;
    observer = new IntersectionObserver((entries) => {
      for (const en of entries) if (en.isIntersecting) { observer.unobserve(en.target); loadThumb(en.target); }
    }, { rootMargin: "120px" });
  }
  async function blobUrl(path) {
    if (thumbs.has(path)) return thumbs.get(path);
    const r = await store.photoBlob(path);
    if (r.expired) { go("anmelden.html#abgelaufen"); return null; }
    if (!r.ok) return null;
    const url = URL.createObjectURL(r.blob);
    thumbs.set(path, url);
    return url;
  }
  async function loadThumb(img) {
    const url = await blobUrl(img.dataset.path);
    if (url && img.isConnected) img.setAttribute("src", url);
  }

  /* ---------- Artikelliste ---------- */
  function emptyTexts(total) {
    if (total === 0) return ["Noch keine Artikel", "Klicke auf „Artikel hinzufügen“ und erfasse deinen ersten Artikel, oder öffne „Importieren und exportieren“."];
    if (state.query) return ["Nichts gefunden", "Ändere die Suche."];
    return state.filter === "stock" ? ["Kein Artikel im Lager", "Alles verkauft. Neue Einkäufe erfasst du über „Artikel hinzufügen“."] : ["Nichts gefunden", "Ändere Filter oder Suche."];
  }
  function articleRow(r, now) {
    const sold = r.is_sold !== false, li = el("li"), b = el("button", "art-row");
    b.type = "button"; b.setAttribute("data-id", r.id);
    const th = el("span", "thumb");
    if (r.photo_path) {
      const img = el("img"); img.setAttribute("alt", ""); img.setAttribute("data-path", r.photo_path);
      th.appendChild(img);
      if (thumbs.has(r.photo_path)) img.setAttribute("src", thumbs.get(r.photo_path));
      else if (observer) observer.observe(img); else loadThumb(img);
    }
    b.appendChild(th);
    const main = el("span", "art-main");
    main.appendChild(el("span", "art-name", r.name));
    const parts = [r.platform];
    if (!sold) parts.push(K.ageText(K.stockDays(r, now)));
    if (sold && r.sale_date) parts.push(shortDate(r.sale_date));
    if (r.receipt_path) parts.push("Beleg");
    main.appendChild(el("span", "art-sub", parts.join(", ")));
    if (!sold && K.stockDays(r, now) >= K.STALE_DAYS) main.appendChild(el("span", "art-stale", "Schon länger im Lager"));
    b.appendChild(main);
    const side = el("span", "art-side");
    if (sold) {
      const p = K.rowProfit(r, state.profile);
      side.appendChild(el("span", "v " + (p >= 0 ? "pos" : "neg"), K.euro(p)));
      side.appendChild(el("span", "n", "Gewinn"));
    } else {
      side.appendChild(el("span", "v", K.euro(r.buy_cents)));
      side.appendChild(el("span", "n", "im Lager"));
    }
    b.appendChild(side);
    li.appendChild(b);
    return li;
  }
  function renderList() {
    ensureObserver();
    const now = Date.now(), all = liveRows(), shown = K.filterRows(all, { query: state.query, filter: state.filter }, now);
    const ul = $("list");
    clear(ul);
    for (const r of shown) ul.appendChild(articleRow(r, now));
    const none = shown.length === 0;
    $("list-empty").hidden = !none;
    ul.hidden = none;
    if (none) { const t = emptyTexts(all.length); $("empty-title").textContent = t[0]; $("empty-text").textContent = t[1]; }
    const st = K.stockStats(all, now), head = $("stock-head");
    head.hidden = !(state.filter === "stock" && st.count > 0);
    if (!head.hidden) {
      head.querySelector(".stock-line").textContent = st.count + " Artikel im Lager, " + K.euro(st.valueCents) + " gebunden";
      const stale = head.querySelector(".stock-stale");
      stale.textContent = st.stale > 0 ? st.stale + " liegen " + K.STALE_DAYS + " Tage oder länger" : "";
      stale.hidden = st.stale === 0;
    }
  }

  function renderAll() { renderYears(); renderOverview(); renderLimit(); renderList(); }

  /* ---------- Formular ---------- */
  const dlg = () => $("art-form").closest("dialog");
  const F = { name: "f-name", buy: "f-buy", sell: "f-sell", cost: "f-cost" };
  const status = () => document.querySelector('input[name="status"]:checked').value;
  function syncFormRows() {
    const sold = status() === "sold";
    $("row-sell").hidden = !sold; $("row-sale-date").hidden = !sold; $("row-profit").hidden = !sold;
    $("row-buy-date").hidden = !$("f-has-buy-date").checked;
    updateProfit();
  }
  function updateProfit() {
    const n = (id) => { const v = P.parseNum($(id).value); return Number.isFinite(v) && v >= 0 ? Math.round(v * 100) : 0; };
    const out = $("f-profit"), sell = n("f-sell");
    if (status() !== "sold" || !(sell > 0)) { out.textContent = "–"; out.className = "num"; return; }
    const p = K.rowProfit({ sell_cents: sell, buy_cents: n("f-buy"), cost_cents: n("f-cost") }, state.profile);
    out.textContent = K.euro(p); out.className = "num " + (p >= 0 ? "pos" : "neg");
  }

  /** Foto- und Beleg-Zustand des offenen Formulars: bytes = neu gewählt (JPEG), removed = Entfernen gewählt, preview = blob:-Adresse. */
  function newPhotoState() { return { photo: { bytes: null, removed: false, preview: null }, receipt: { bytes: null, removed: false, preview: null } }; }
  const KIND = { photo: { field: "pf-photo", file: "f-photo", col: "photo_path", api: "foto" }, receipt: { field: "pf-receipt", file: "f-receipt", col: "receipt_path", api: "beleg" } };
  function showPreview(kind, url) {
    const s = state.photo[kind], c = KIND[kind], img = $(c.field).querySelector("img");
    if (s.preview) URL.revokeObjectURL(s.preview);
    s.preview = url || null;
    if (url) { img.setAttribute("src", url); img.hidden = false; } else { img.removeAttribute("src"); img.hidden = true; }
    $(c.field).querySelector("[data-remove-photo]").hidden = !url;
  }
  async function loadExistingPreview(kind, path, token) {
    const r = await store.photoBlob(path);
    if (r.expired) { go("anmelden.html#abgelaufen"); return; }
    if (!r.ok || token !== state.photo) return;   // Formular wurde inzwischen geschlossen oder gewechselt
    showPreview(kind, URL.createObjectURL(r.blob));
  }

  /** Bild lesen und auf längste Kante MAX_EDGE als JPEG (Qualität 0,75) bringen. */
  async function toJpeg(file) {
    let src, w, h, cleanup = () => {};
    if (typeof createImageBitmap === "function") {
      try { src = await createImageBitmap(file); w = src.width; h = src.height; cleanup = () => src.close && src.close(); } catch { src = null; }
    }
    if (!src) {
      const url = URL.createObjectURL(file), img = new Image();
      try {
        await new Promise((ok, bad) => { img.onload = ok; img.onerror = bad; img.src = url; });
      } finally { URL.revokeObjectURL(url); }
      src = img; w = img.naturalWidth; h = img.naturalHeight;
    }
    const size = K.fitSize(w, h, MAX_EDGE), canvas = document.createElement("canvas");
    canvas.width = size.width; canvas.height = size.height;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, size.width, size.height);
    ctx.drawImage(src, 0, 0, size.width, size.height);
    cleanup();
    const blob = await new Promise((ok) => canvas.toBlob(ok, "image/jpeg", JPEG_QUALITY));
    if (!blob) throw new Error("kein Bild");
    return { bytes: new Uint8Array(await blob.arrayBuffer()), blob };
  }
  function wirePhotoField(kind) {
    const c = KIND[kind], input = $(c.file);
    input.addEventListener("change", async () => {
      const f = input.files && input.files[0];
      if (!f) return;
      SCField.clear(input);
      try {
        const j = await toJpeg(f);
        state.photo[kind].bytes = j.bytes; state.photo[kind].removed = false;
        showPreview(kind, URL.createObjectURL(j.blob));
      } catch { SCField.show(input, "Dieses Foto konnte nicht gelesen werden.", false); }
      input.value = "";
    });
    $(c.field).querySelector("[data-remove-photo]").addEventListener("click", () => {
      state.photo[kind].bytes = null; state.photo[kind].removed = true;
      showPreview(kind, null);
    });
  }

  function fillPlatforms(current) {
    const sel = $("f-platform"), names = K.PLATFORMS.slice();
    if (current && !names.includes(current)) names.push(current);
    clear(sel);
    for (const n of names) { const o = el("option", "", n); o.value = n; sel.appendChild(o); }
    sel.value = current || names[0];
  }
  function releasePreviews() {
    if (state.photo) for (const kind of Object.keys(KIND)) if (state.photo[kind].preview) URL.revokeObjectURL(state.photo[kind].preview);
  }
  function openForm(row) {
    releasePreviews();
    state.editing = row || null;
    state.photo = newPhotoState();
    const f = $("art-form");
    f.reset();
    for (const id of Object.values(F)) SCField.clear($(id));
    for (const id of ["f-photo", "f-receipt"]) SCField.clear($(id));
    msg($("form-error"), ""); msg($("form-saved"), "");
    $("confirm-delete").hidden = true;
    $("form-title").textContent = row ? "Artikel bearbeiten" : "Erfassen";
    $("f-delete").hidden = !row;
    $("f-save-next").hidden = !!row;
    fillPlatforms(row ? row.platform : "Vinted");
    if (row) {
      const sold = row.is_sold !== false;
      document.querySelector('input[name="status"][value="' + (sold ? "sold" : "stock") + '"]').checked = true;
      $("f-name").value = row.name || "";
      $("f-buy").value = eurosInput(row.buy_cents); $("f-sell").value = eurosInput(row.sell_cents); $("f-cost").value = eurosInput(row.cost_cents);
      $("f-sale-date").value = row.sale_date || "";
      $("f-has-buy-date").checked = !!row.buy_date; $("f-buy-date").value = row.buy_date || "";
      $("f-notes").value = row.notes || "";
    } else $("f-sale-date").value = today();
    for (const kind of Object.keys(KIND)) {
      showPreview(kind, null);
      const path = row && row[KIND[kind].col];
      if (path) loadExistingPreview(kind, path, state.photo);
    }
    syncFormRows();
    const d = dlg();
    if (!d.open) { if (typeof d.showModal === "function") d.showModal(); else d.setAttribute("open", ""); }
    $("f-name").focus();
  }
  function closeForm() {
    const d = dlg();
    if (d.open) d.close();
  }
  function onClosed() {
    releasePreviews();
    state.photo = null; state.editing = null;
  }

  function formValues() {
    return {
      sold: status() === "sold", name: $("f-name").value, platform: $("f-platform").value,
      buy: $("f-buy").value, sell: $("f-sell").value, cost: $("f-cost").value,
      saleDate: $("f-sale-date").value, hasBuyDate: $("f-has-buy-date").checked, buyDate: $("f-buy-date").value, notes: $("f-notes").value,
    };
  }
  function setBusy(on) {
    state.saving = on;
    for (const id of ["f-save", "f-save-next", "f-cancel", "f-delete"]) $(id).disabled = on;
  }

  /**
   * Alte Fotos erst löschen, wenn die Zeile im Konto nachgelesen den neuen Pfad trägt. Hat ein anderes Gerät inzwischen später geändert,
   * verwirft der Server unsere Änderung, und das alte Foto wird dort noch gebraucht. Gibt true zurück, wenn der Stand neu geholt werden muss.
   */
  async function cleanupPhotos(row, old) {
    const v = await store.loadByIds([row.id]);
    if (v.expired) { go("anmelden.html#abgelaufen"); return false; }
    const server = v.ok ? v.rows.find((x) => x.id === row.id) : null;
    const c = K.photoCleanup(old, server, row);
    if (c.remove.length) store.deletePhotos(c.remove).then((d) => { if (d && d.expired) go("anmelden.html#abgelaufen"); });
    return server != null && c.keep.length > 0;
  }
  async function resyncNotice() {   // aktuellen Stand holen, die Meldung erst danach (der Abgleich leert die Meldungszeile)
    state.lastSync = 0;
    await sync();
    if (state.lastSync) msg($("msg"), "Dieser Artikel wurde inzwischen auf einem anderen Gerät geändert und bleibt erhalten.");
  }

  /** Speichern: neue Fotos zuerst hochladen, dann die Zeile, danach erst die alten Fotos löschen. Gibt true zurück, wenn alles im Konto ist. */
  async function save(andContinue) {
    if (state.saving) return;
    msg($("form-error"), "");
    const res = K.formToRow(formValues(), state.editing, { now: new Date(), newId: uuid }, P.parseNum);
    if (!res.ok) {
      let first = true;
      for (const k of Object.keys(F)) if (res.errors[k]) { SCField.show($(F[k]), res.errors[k], first); first = false; }
      return;
    }
    const row = res.row, old = [];
    let resync = false;
    setBusy(true);
    try {
      for (const kind of Object.keys(KIND)) {
        const c = KIND[kind], s = state.photo[kind], before = state.editing && state.editing[c.col];
        if (s.bytes) {
          const up = await store.uploadPhoto(row.id, c.api, s.bytes);
          if (failed(up, $("form-error"))) return;
          if (before && before !== up.path) old.push({ col: c.col, path: before });
          row[c.col] = up.path;
        } else if (s.removed && before) { old.push({ col: c.col, path: before }); row[c.col] = null; }
      }
      const r = await store.save([row]);
      if (failed(r, $("form-error"))) return;
      state.rows.set(row.id, { ...(state.editing || {}), ...row });
      if (old.length) resync = await cleanupPhotos(row, old);
      renderAll();
      if (andContinue) {
        const keepSold = status(), keepPlatform = row.platform;
        openForm(null);
        document.querySelector('input[name="status"][value="' + keepSold + '"]').checked = true;
        $("f-platform").value = keepPlatform;
        syncFormRows();
        msg($("form-saved"), "„" + row.name + "“ gesichert", "ok");
      } else closeForm();
    } finally { setBusy(false); }
    if (resync) await resyncNotice();
  }

  /**
   * Löschen: Zeile markieren, dann im Konto nachlesen. Die Fotos werden erst gelöscht, wenn die Zeile dort wirklich deleted_at hat (wie BackupService.swift):
   * Hat ein anderes Gerät den Artikel inzwischen neuer geändert, verwirft der Server die Löschung und die Fotos müssen bleiben.
   */
  async function removeArticle() {
    const row = state.editing;
    if (!row || state.saving) return;
    let resync = false;
    setBusy(true);
    try {
      const r = await store.remove(row.id, new Date());
      if (failed(r, $("form-error"))) return;
      state.rows.delete(row.id);
      const paths = [row.photo_path, row.receipt_path].filter(Boolean);
      const v = await store.loadByIds([row.id]);
      if (v.expired) { go("anmelden.html#abgelaufen"); return; }
      const server = v.ok ? v.rows.find((x) => x.id === row.id) : null;
      if (server && !server.deleted_at) resync = true;
      else if (server && paths.length) store.deletePhotos(paths).then((d) => { if (d && d.expired) go("anmelden.html#abgelaufen"); });   // ohne Bestätigung bleiben die Fotos liegen
      renderAll();
      closeForm();
    } finally { setBusy(false); }
    if (resync) {   // aktuellen Stand holen, die Meldung erst danach (der Abgleich leert die Meldungszeile)
      state.lastSync = 0;
      await sync();
      if (state.lastSync) msg($("msg"), "Dieser Artikel wurde inzwischen auf einem anderen Gerät geändert und bleibt erhalten.");
    }
  }

  function wireForm() {
    const form = $("art-form");
    form.addEventListener("submit", (e) => { e.preventDefault(); save(false); });
    $("f-save-next").addEventListener("click", () => save(true));
    $("f-cancel").addEventListener("click", closeForm);
    $("f-delete").addEventListener("click", () => { $("confirm-delete").hidden = false; $("f-delete-no").focus(); });
    $("f-delete-no").addEventListener("click", () => { $("confirm-delete").hidden = true; $("f-delete").focus(); });
    $("f-delete-yes").addEventListener("click", removeArticle);
    dlg().addEventListener("close", onClosed);
    document.querySelectorAll('input[name="status"]').forEach((r) => r.addEventListener("change", syncFormRows));
    $("f-has-buy-date").addEventListener("change", syncFormRows);
    for (const id of ["f-buy", "f-sell", "f-cost"]) $(id).addEventListener("input", updateProfit);
    wirePhotoField("photo"); wirePhotoField("receipt");
  }

  /* ---------- Importieren, Übernehmen, Exportieren ---------- */
  const IO_PLATFORMS = [...T.REPORTED_PLATFORMS, "Flohmarkt / bar", "Sonstige"];
  const TOOLS_KEYS = ["sellcheck.sales.v1", "vintcheck.sales.v1"];
  const MAX_FILE_BYTES = 5 * 1024 * 1024;
  const io = { queue: [], file: null, a: null, plan: null, tools: null, busy: false };

  /** Einträge der Gratis-Tools aus diesem Browser (nur lesen, nie ändern). */
  function toolsEntries() {
    try {
      const raw = TOOLS_KEYS.map((k) => window.localStorage.getItem(k)).find(Boolean);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.map(T.sanitizeEntry).filter(Boolean) : [];
    } catch { return []; }
  }
  const ioOpt = () => ({ now: new Date(), newId: uuid });
  const ioMsg = (t, kind) => msg($("io-msg"), t, kind);
  function ioShowPlan(label, plan, extra) {
    io.plan = plan;
    const p = $("io-preview");
    p.textContent = (extra ? extra + " " : "") + plan.rows.length + (plan.rows.length === 1 ? " neuer Artikel" : " neue Artikel") + ", " + plan.present + " " + (plan.present === 1 ? "ist" : "sind") + " schon im Konto.";
    p.hidden = false;
    $("io-go").disabled = plan.rows.length === 0;
    $("io-actions").hidden = false;
    $("io-go").textContent = "Artikel ins Konto übernehmen";
    if (label) $("io-file-name").textContent = label;
  }
  function ioReset() {
    io.queue = []; io.file = null; io.a = null; io.plan = null; io.tools = null;
    for (const id of ["io-ask", "io-preview", "io-actions"]) $(id).hidden = true;
    ioMsg("");
  }
  function ioPreview() {
    const a = io.a;
    if (!a) return;
    const e = P.entriesFrom(a, { dateOrder: $("io-dateorder").value, platform: $("io-platform").value, positiveOnly: $("io-positive").checked, keyword: $("io-keyword").value, platforms: IO_PLATFORMS });
    const s = e.stats, parts = [s.ok + " von " + s.total + " Zeilen importierbar"];
    if (s.filtered) parts.push(s.filtered + " per Typ-Filter übersprungen");
    if (s.keyword) parts.push(s.keyword + " ohne Stichwort");
    if (s.noAmount) parts.push(s.noAmount + " ohne gültigen Betrag (z. B. Erstattungen)");
    if (s.noDate) parts.push(s.noDate + " ohne lesbares Datum");
    const warn = [];
    if (a.currencies.length) warn.push("Die Datei enthält andere Währungen (" + a.currencies.join(", ") + "). SellCheck rechnet nicht um, alle Beträge würden als Euro gezählt. Importiere nur die Euro-Zeilen oder rechne vorher um.");
    const missing = e.entries.filter((x) => x.needsBuy).length;
    if (missing) warn.push("Hinweis: Die Datei enthält keine Einkaufspreise. Dein Gewinn wirkt zu hoch, bis du sie nachträgst (" + missing + " Einträge).");
    msg($("io-warn"), warn.join(" "), warn.length ? "error" : "");
    ioShowPlan(null, K.planTakeover(e.entries, liveRows(), ioOpt()), parts.join(", ") + ".");
  }
  async function ioNextFile() {
    while (io.queue.length) {
      const file = io.queue.shift();
      io.file = file;
      const label = file.name + (io.queue.length ? " (noch " + io.queue.length + " weitere)" : "");
      if (file.size > MAX_FILE_BYTES) { ioMsg(file.name + ": Die Datei ist größer als 5 MB. Bitte teile sie nach Jahren auf.", "error"); continue; }
      if (/\.(xlsx|xls|numbers|pdf|zip)$/i.test(file.name)) { ioMsg(file.name + ": Dieses Format kann ich nicht lesen. Speichere die Tabelle bitte als CSV (in Excel über „Speichern unter“ mit dem Dateityp CSV).", "error"); continue; }
      let text;
      try { text = P.decode(await file.arrayBuffer()); } catch { ioMsg(file.name + ": Die Datei konnte nicht gelesen werden.", "error"); continue; }
      const a = P.analyze(text, { maxRows: K.MAX_IMPORT_ROWS });
      if (!a.ok) { ioMsg(file.name + ": " + a.message, "error"); continue; }
      io.a = a;
      ioMsg("");
      $("io-dateorder").value = a.dateOrder;
      $("io-ask-date").hidden = !a.ambiguous;
      $("io-platform").value = "";
      $("io-positive").closest("div").hidden = false;
      $("io-keyword").value = a.keyword;
      $("io-ask-keyword").hidden = !a.bankLike;
      $("io-positive").checked = !a.own;
      $("io-file-name").textContent = label;
      $("io-ask").hidden = false;
      ioPreview();
      // Plattform nur erfragen, wenn sie weder in der Datei steht noch aus dem Namen klar ist (wie in den Tools)
      $("io-ask-platform").hidden = !P.entriesFrom(a, { platforms: IO_PLATFORMS, positiveOnly: !a.own, keyword: a.keyword }).entries.some((x) => x.platform === "Sonstige");
      return;
    }
    if (!io.a) { $("io-ask").hidden = true; $("io-preview").hidden = true; $("io-actions").hidden = true; }
  }
  async function ioGo() {
    if (io.busy) return;
    if (!io.tools) ioPreview();
    const rows = io.plan ? io.plan.rows : [];
    if (!rows.length) return;
    io.busy = true; $("io-go").disabled = true;
    try {
      const r = await store.save(rows);
      if (failed(r, $("io-msg"))) return;
      for (const x of rows) state.rows.set(x.id, x);
      renderAll();
      ioMsg(rows.length + (rows.length === 1 ? " Artikel übernommen." : " Artikel übernommen."), "ok");
      io.plan = null;
      if (io.tools) { io.tools = null; $("io-preview").hidden = true; $("io-actions").hidden = true; $("io-ask").hidden = true; return; }
      io.a = null;
      $("io-preview").hidden = true; $("io-actions").hidden = true; $("io-ask").hidden = true;
      if (io.queue.length) { const done = $("io-msg").textContent; await ioNextFile(); if (io.a) ioMsg(done, "ok"); }
    } finally { io.busy = false; $("io-go").disabled = !(io.plan && io.plan.rows.length); }
  }
  async function ioTakeover() {
    ioReset();
    state.lastSync = 0; await sync();   // zuerst den Stand im Konto holen, damit nichts doppelt angelegt wird
    const entries = toolsEntries();
    io.tools = entries;
    $("io-ask").hidden = false;
    for (const id of ["io-ask-date", "io-ask-platform", "io-ask-keyword", "io-warn"]) $(id).hidden = true;
    $("io-positive").closest("div").hidden = true;
    ioShowPlan("Einträge aus den Gratis-Tools (" + entries.length + ")", K.planTakeover(entries, liveRows(), ioOpt()));
  }
  function ioExport() {
    const blob = new Blob([K.exportCsv([...state.rows.values()], state.profile)], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.setAttribute("href", URL.createObjectURL(blob));
    a.setAttribute("download", K.exportName(new Date()));
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.getAttribute("href")), 1000);
  }
  function wireIo() {
    const sel = $("io-platform");
    const none = el("option", "", "Bitte wählen …"); none.value = ""; sel.appendChild(none);
    for (const n of IO_PLATFORMS) { const o = el("option", "", n); o.value = n; sel.appendChild(o); }
    $("io-take").addEventListener("click", ioTakeover);
    $("io-export").addEventListener("click", ioExport);
    $("io-go").addEventListener("click", ioGo);
    $("io-cancel").addEventListener("click", ioReset);
    $("io-file").addEventListener("change", (e) => {
      const files = [...e.target.files];
      e.target.value = "";   // dieselbe Datei später erneut wählbar
      if (!files.length) return;
      ioReset();
      io.queue = files;
      ioNextFile();
    });
    for (const id of ["io-dateorder", "io-platform", "io-positive"]) $(id).addEventListener("input", ioPreview);
    $("io-keyword").addEventListener("input", ioPreview);
    $("io").addEventListener("toggle", () => { $("io-takeover").hidden = toolsEntries().length === 0; });
  }
  const showTakeover = () => { $("io-takeover").hidden = toolsEntries().length === 0; };

  /* ---------- Laden und Abgleich ---------- */
  async function load() {
    const p = await store.loadProfile();
    if (failed(p)) return false;
    state.profile = p.profile;
    const a = await store.loadAll();
    if (failed(a)) return false;
    state.rows = new Map(a.rows.map((r) => [r.id, r]));
    state.cursor = a.cursor;
    state.lastSync = Date.now();
    return true;
  }
  async function sync() {
    if (state.syncing || state.saving || Date.now() - state.lastSync < SYNC_MIN_MS) return;
    state.syncing = true;
    try {
      const r = await store.loadChanges(state.cursor);
      if (failed(r)) return;   // zuletzt geladene Daten bleiben sichtbar
      msg($("msg"), "");
      state.rows = K.mergeChanges(state.rows, r.rows);
      state.cursor = r.cursor;
      state.lastSync = Date.now();
      renderAll();
    } finally { state.syncing = false; }
  }

  function wireControls() {
    for (const sel of document.querySelectorAll("select[data-year]")) sel.addEventListener("change", () => { state.year = +sel.value; renderYears(); renderOverview(); renderLimit(); });
    $("search").addEventListener("input", () => { state.query = $("search").value; renderList(); });
    document.querySelectorAll('input[name="filter"]').forEach((r) => r.addEventListener("change", () => { state.filter = r.value; renderList(); }));
    document.querySelectorAll("[data-add]").forEach((b) => b.addEventListener("click", () => openForm(null)));
    $("list").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-id]");
      const row = b && state.rows.get(b.getAttribute("data-id"));
      if (row) openForm(row);
    });
    $("logout").addEventListener("click", async () => { await client.signOut(); go("anmelden.html"); });
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") sync(); });
    window.addEventListener("pagehide", () => { for (const u of thumbs.values()) URL.revokeObjectURL(u); thumbs.clear(); });
  }

  async function init() {
    const g = await client.getSession();
    if (!g.session) return go(g.expired ? "anmelden.html#abgelaufen" : "anmelden.html");
    $("who").textContent = g.session.email;
    wireTabs(); wireControls(); wireForm(); wireIo(); showTakeover();
    if (g.offline) msg($("msg"), "Keine Verbindung zum Server. Prüfe dein Internet und versuche es noch einmal.", "error");
    if (!(await load())) {
      const loading = $("loading");
      loading.textContent = "Deine Artikel konnten nicht geladen werden. ";
      const retry = el("button", "linklike", "Noch einmal versuchen");
      retry.type = "button";
      retry.addEventListener("click", () => { window.location.reload(); });
      loading.appendChild(retry);
      return;
    }
    msg($("msg"), "");
    $("loading").hidden = true;
    $("mine").hidden = false;
    renderAll();
    setTab(K.tabFromHash(window.location.hash), { hash: false });
  }

  init();
})();
