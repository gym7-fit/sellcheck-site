// Alle Daten bleiben im Browser (localStorage). Nutzereingaben werden nie als HTML eingefügt.
const LIMIT_COUNT = 30;
const LIMIT_SUM = 2000;
const STORE_KEY = "sellcheck.sales.v1";
const OLD_STORE_KEY = "vintcheck.sales.v1";

// reported: Plattform meldet ans BZSt (PStTG). Flohmarkt/bar und Sonstige haben keine Plattform-Meldung.
const PLATFORMS = [
  { name: "Vinted", reported: true },
  { name: "Kleinanzeigen", reported: true },
  { name: "eBay", reported: true },
  { name: "Etsy", reported: true },
  { name: "Amazon", reported: true },
  { name: "Flohmarkt / bar", reported: false },
  { name: "Sonstige", reported: false },
];
const isReported = (name) => (PLATFORMS.find((p) => p.name === name) || { reported: false }).reported;

const $ = (id) => document.getElementById(id);
const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
const pct = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
const num = (el) => {
  const v = parseFloat(el.value);
  return Number.isFinite(v) && v >= 0 ? v : 0;
};
const el = (tag, text, cls) => {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
};
const isSold = (s) => s.status !== "stock";
const profitOf = (s) => s.sell - s.buy - s.cost;

/* ---------- Speicher ---------- */
// Beschädigte oder fremde Einträge dürfen die Seite nicht lahmlegen: alles wird geprüft und begrenzt.
// Bereinigung beschädigter oder fremder Einträge: gemeinsam mit dem Steuer-Export (tax-lib.js).
const sanitize = SCTax.sanitizeEntry;
function loadSales() {
  try {
    const raw = localStorage.getItem(STORE_KEY) || localStorage.getItem(OLD_STORE_KEY) || "[]";
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data.map(sanitize).filter(Boolean) : [];
  } catch {
    return [];
  }
}
let storageOk = true;
function saveSales(list) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(list));
    storageOk = true;
    return true;
  } catch {
    storageOk = false;
    $("t-msg").textContent = "Speichern im Browser nicht möglich (voll oder privater Modus). Einträge gehen beim Neuladen verloren.";
    return false;
  }
}
let sales = loadSales();

/* ---------- Plattform-Auswahlen ---------- */
function fillSelect(sel, withAll) {
  const items = (withAll ? [{ name: "" }] : []).concat(PLATFORMS);
  sel.replaceChildren(
    ...items.map((p) => {
      const o = el("option", p.name || "Alle");
      o.value = p.name;
      return o;
    })
  );
}
fillSelect($("t-platform"), false);
fillSelect($("t-filter"), true);
fillSelect($("a-platform"), false);

/* ---------- Bewertung gegen die Meldegrenze ---------- */
function level(ratio) {
  return ratio >= 1 ? "red" : ratio >= 0.6 ? "yellow" : "green";
}
const LEVEL_TEXT = {
  green: "Grün: weit entfernt",
  yellow: "Gelb: nähert sich der Grenze",
  red: "Rot: Grenze erreicht",
};

/* ---------- 1. Ampel (manuell) ---------- */
function setBar(bar, ratio) {
  bar.style.width = Math.min(100, ratio * 100) + "%";
  bar.className = ratio >= 1 ? "red" : ratio >= 0.6 ? "yellow" : "";
}

function renderAmpel() {
  const count = num($("a-count"));
  const sum = num($("a-sum"));
  const rc = count / LIMIT_COUNT;
  const rs = sum / LIMIT_SUM;
  const worst = Math.max(rc, rs);

  const arc = $("a-gauge-arc");
  arc.setAttribute("stroke-dashoffset", String(100 - Math.min(1, worst) * 100));
  arc.setAttribute("class", "arc " + (worst >= 1 ? "red" : worst >= 0.6 ? "yellow" : ""));
  $("a-gauge-pct").textContent = pct.format(worst * 100) + " %";

  setBar($("a-count-bar"), rc);
  setBar($("a-sum-bar"), rs);
  $("a-count-txt").textContent = `${count} von ${LIMIT_COUNT} (${pct.format(rc * 100)} %)`;
  $("a-sum-txt").textContent = `${eur.format(sum)} von ${eur.format(LIMIT_SUM)} (${pct.format(rs * 100)} %)`;

  const box = $("a-result");
  const [title, text, cls] =
    worst >= 1
      ? ["Rot: Grenze erreicht", "Die Plattform meldet dich voraussichtlich ans BZSt. Das ist noch keine Steuerforderung. Halte Einkaufsbelege und Verkaufsdaten bereit und kläre bei Unsicherheit deinen Fall mit Finanzamt oder Steuerberatung.", "red"]
      : worst >= 0.6
      ? ["Gelb: Du näherst dich der Grenze", `Bei diesem Tempo erreichst du die Grenze voraussichtlich bald. Es fehlen noch ${Math.max(0, LIMIT_COUNT - count)} Verkäufe oder ${eur.format(Math.max(0, LIMIT_SUM - sum))}.`, "yellow"]
      : ["Grün: Weit entfernt", "Du liegst deutlich unter der Meldegrenze dieser Plattform. Für gelegentliches Ausmisten musst du dir in der Regel keine Sorgen machen.", "green"];
  box.className = "ampel " + cls;
  box.querySelector("strong").textContent = title;
  box.querySelector("div").textContent = text;
}
["a-count", "a-sum"].forEach((id) => $(id).addEventListener("input", renderAmpel));

$("a-from-tracker").addEventListener("click", () => {
  const year = $("o-year").value || String(new Date().getFullYear());
  const rows = sales.filter((s) => isSold(s) && s.date.startsWith(year) && s.platform === $("a-platform").value);
  $("a-count").value = rows.length;
  $("a-sum").value = rows.reduce((a, s) => a + s.sell, 0).toFixed(2);
  renderAmpel();
});

/* ---------- 2. Gewinn pro Artikel ---------- */
function renderProfit() {
  const buy = num($("g-buy"));
  const sell = num($("g-sell"));
  const cost = num($("g-ship")) + num($("g-other"));
  const profit = sell - buy - cost;
  $("g-profit").textContent = eur.format(profit);
  $("g-profit").className = "v " + (profit > 0 ? "pos" : profit < 0 ? "neg" : "");
  $("g-margin").textContent = sell > 0 ? pct.format((profit / sell) * 100) + " %" : "–";
  $("g-roi").textContent = buy > 0 ? pct.format((profit / buy) * 100) + " %" : "–";
}
["g-buy", "g-sell", "g-ship", "g-other"].forEach((id) => $(id).addEventListener("input", renderProfit));

/* ---------- Jahre ---------- */
$("t-date").valueAsDate = new Date();

function fillYears() {
  const current = new Date().getFullYear();
  const years = new Set([current, ...sales.map((s) => Number(s.date.slice(0, 4)))]);
  const sorted = [...years].sort((a, b) => b - a);
  ["t-year", "o-year"].forEach((id) => {
    const sel = $(id);
    const keep = sel.value;
    sel.replaceChildren(
      ...sorted.map((y) => {
        const o = el("option", String(y));
        o.value = String(y);
        return o;
      })
    );
    if (keep && years.has(Number(keep))) sel.value = keep;
  });
  $("o-year").value = $("t-year").value;
}

/* ---------- Plattform-Überblick ---------- */
function stat(value, label, cls) {
  const d = el("div", undefined, "stat");
  d.append(el("div", value, "v" + (cls ? " " + cls : "")), el("div", label, "l"));
  return d;
}

function renderOverview() {
  const year = $("o-year").value;
  const rows = sales.filter((s) => s.date.startsWith(year));
  const sold = rows.filter(isSold);
  const stock = rows.filter((s) => !isSold(s));

  const sum = sold.reduce((a, s) => a + s.sell, 0);
  const profit = sold.reduce((a, s) => a + profitOf(s), 0);
  const tied = stock.reduce((a, s) => a + s.buy, 0);
  const platformsUsed = new Set(rows.map((s) => s.platform)).size;

  $("o-total").replaceChildren(
    stat(String(sold.length), `Verkäufe auf ${platformsUsed} ${platformsUsed === 1 ? "Plattform" : "Plattformen"}`),
    stat(eur.format(sum), "Umsatz gesamt"),
    stat(eur.format(profit), "Gewinn gesamt", profit > 0 ? "pos" : profit < 0 ? "neg" : ""),
    stat(String(stock.length), `Im Bestand (gebunden: ${eur.format(tied)})`)
  );
  $("o-total").hidden = rows.length === 0;
  const missingBuy = sold.filter((s) => s.needsBuy && !(s.buy > 0)).length;
  $("o-hint").hidden = missingBuy === 0;
  if (missingBuy) $("o-hint").textContent = `Bei ${missingBuy} importierten Verkäufen fehlt der Einkaufspreis. Dein Gewinn wirkt deshalb zu hoch. Trage ihn im Tracker nach.`;
  $("o-empty").hidden = rows.length > 0;

  const names = [...PLATFORMS.map((p) => p.name), ...new Set(rows.map((s) => s.platform))].filter(
    (n, i, a) => a.indexOf(n) === i
  );
  const list = $("o-list");
  list.replaceChildren(
    ...names
      .map((name) => {
        const mine = sold.filter((s) => s.platform === name);
        const mineStock = stock.filter((s) => s.platform === name);
        if (!mine.length && !mineStock.length) return null;

        const psum = mine.reduce((a, s) => a + s.sell, 0);
        const pprofit = mine.reduce((a, s) => a + profitOf(s), 0);
        const rc = mine.length / LIMIT_COUNT;
        const rs = psum / LIMIT_SUM;
        const worst = Math.max(rc, rs);
        const reported = isReported(name);
        const lvl = reported ? level(worst) : "";

        const row = el("div", undefined, "plat-row " + lvl);
        const nameBox = el("div", name, "name");
        nameBox.append(
          el("small", reported ? `${mine.length} von ${LIMIT_COUNT} Verkäufen · ${eur.format(psum)} von ${eur.format(LIMIT_SUM)}` : `${mine.length} Verkäufe · ${eur.format(psum)}`)
        );
        const meter = el("div", undefined, "meter");
        const bar = el("div");
        if (reported) setBar(bar, worst);
        else bar.style.width = "0";
        meter.append(bar);
        const nums = el("div", undefined, "nums");
        nums.append(el("b", eur.format(pprofit), pprofit >= 0 ? "pos" : "neg"), document.createElement("br"), document.createTextNode("Gewinn"));
        const status = el(
          "div",
          reported
            ? `${LEVEL_TEXT[lvl]} (${pct.format(worst * 100)} %)` + (mineStock.length ? ` · ${mineStock.length} im Bestand` : "")
            : "Keine Plattform-Meldung" + (mineStock.length ? ` · ${mineStock.length} im Bestand` : ""),
          "status"
        );
        row.append(nameBox, meter, nums, status);
        return row;
      })
      .filter(Boolean)
  );
}

/* ---------- 3. Tracker ---------- */
function filteredRows() {
  const year = $("t-year").value;
  const plat = $("t-filter").value;
  return sales.filter((s) => s.date.startsWith(year) && (!plat || s.platform === plat));
}

function td(text, cls) {
  const c = el("td", text);
  if (cls) c.className = cls;
  return c;
}

// Importierte Einträge haben oft keinen Einkaufspreis: dort direkt eintragbar.
function buyCell(s) {
  if (!s.needsBuy) return td(eur.format(s.buy), "num");
  const c = el("td", undefined, "num");
  const inp = document.createElement("input");
  inp.type = "number";
  inp.min = "0";
  inp.step = "0.01";
  inp.className = "inline-num";
  inp.placeholder = "Einkauf";
  inp.value = s.buy > 0 ? String(s.buy) : "";
  inp.setAttribute("aria-label", `Einkaufspreis für ${s.name}`);
  inp.addEventListener("change", () => {
    s.buy = num(inp);
    saveSales(sales);
    refresh();
  });
  c.append(inp);
  return c;
}

function renderTracker() {
  const rows = filteredRows().sort((a, b) => b.date.localeCompare(a.date));
  const sold = rows.filter(isSold);
  const stock = rows.filter((s) => !isSold(s));

  const sum = sold.reduce((a, s) => a + s.sell, 0);
  const cost = sold.reduce((a, s) => a + s.buy + s.cost, 0);
  const profit = sum - cost;
  $("s-count").textContent = sold.length;
  $("s-sum").textContent = eur.format(sum);
  $("s-cost").textContent = eur.format(cost);
  $("s-profit").textContent = eur.format(profit);
  $("s-profit").className = "v " + (profit > 0 ? "pos" : profit < 0 ? "neg" : "");
  $("s-stock").textContent = stock.length;
  $("s-stockval").textContent = eur.format(stock.reduce((a, s) => a + s.buy, 0));

  const SHOW = 500;
  $("t-more").hidden = rows.length <= SHOW;
  if (rows.length > SHOW) $("t-more").textContent = `Angezeigt werden die neuesten ${SHOW} von ${rows.length} Einträgen. Auswertung und CSV-Export enthalten alle.`;
  $("t-body").replaceChildren(
    ...rows.slice(0, SHOW).map((s) => {
      const tr = document.createElement("tr");
      const sold = isSold(s);
      const p = profitOf(s);
      tr.append(
        td(new Date(s.date).toLocaleDateString("de-DE")),
        td(s.name),
        td(s.platform),
        td(sold ? "Verkauft" : "Bestand"),
        buyCell(s),
        td(sold ? eur.format(s.sell) : "–", "num"),
        td(eur.format(s.cost), "num"),
        td(sold ? eur.format(p) : "–", "num " + (sold ? (p >= 0 ? "pos" : "neg") : ""))
      );
      const act = document.createElement("td");
      const del = el("button", "Löschen", "btn danger small");
      del.type = "button";
      del.setAttribute("aria-label", `Eintrag ${s.name} löschen`);
      del.addEventListener("click", () => {
        sales = sales.filter((x) => x.id !== s.id);
        saveSales(sales);
        refresh();
      });
      const edit = el("button", "Bearbeiten", "btn secondary small");
      edit.type = "button";
      edit.setAttribute("aria-label", `Eintrag ${s.name} bearbeiten`);
      edit.addEventListener("click", () => openEdit(s));
      act.append(edit, document.createTextNode(" "), del);
      tr.append(act);
      return tr;
    })
  );
  $("t-empty").hidden = rows.length > 0;
}

const refreshListeners = [];
function refresh() {
  fillYears();
  renderTracker();
  renderOverview();
  refreshListeners.forEach((fn) => fn());
}

// Optionale Steuerangaben nur setzen, wenn sie gültig sind.
function optionalFields(buyDate, receipt, kind) {
  const o = {};
  if (SCTax.validIso(buyDate)) o.buyDate = buyDate;
  if (receipt.trim()) o.receipt = receipt.trim().slice(0, 60);
  if (kind === "everyday" || kind === "other") o.kind = kind;
  return o;
}

$("t-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = $("t-name").value.trim();
  const date = $("t-date").value;
  if (!name || !date) {
    $("t-msg").textContent = "Bitte Artikel und Datum angeben.";
    return;
  }
  const status = $("t-status").value;
  sales.push({
    id: Date.now() + Math.random().toString(36).slice(2, 6),
    name,
    date,
    platform: $("t-platform").value,
    buy: num($("t-buy")),
    sell: status === "stock" ? 0 : num($("t-sell")),
    cost: num($("t-cost")),
    status,
    ...optionalFields($("t-buydate").value, $("t-receipt").value, $("t-kind").value),
  });
  saveSales(sales);
  $("t-name").value = "";
  $("t-buydate").value = $("t-receipt").value = $("t-kind").value = "";
  $("t-buy").value = $("t-sell").value = $("t-cost").value = "0";
  if (storageOk) $("t-msg").textContent = "Gespeichert.";
  fillYears();
  $("t-year").value = date.slice(0, 4);
  $("o-year").value = date.slice(0, 4);
  renderTracker();
  renderOverview();
});
$("t-year").addEventListener("change", () => {
  $("o-year").value = $("t-year").value;
  renderTracker();
  renderOverview();
});
$("o-year").addEventListener("change", () => {
  $("t-year").value = $("o-year").value;
  renderTracker();
  renderOverview();
});
$("t-filter").addEventListener("change", renderTracker);

const KIND_LABEL = { everyday: "Gebrauchsgegenstand", other: "Sonstiges" };
$("t-export").addEventListener("click", () => {
  const T = SCTax;
  const rows = filteredRows().sort((a, b) => a.date.localeCompare(b.date));
  const head = ["Datum", "Artikel", "Plattform", "Status", "Einkauf", "Verkauf", "Kosten", "Gewinn", "Einkaufsdatum", "Belegnr", "Art"];
  const body = rows.map((s) => [
    T.cellT(s.date), T.cellT(s.name), T.cellT(s.platform), T.cellT(isSold(s) ? "Verkauft" : "Bestand"),
    T.cellN(T.cents(s.buy)), isSold(s) ? T.cellN(T.cents(s.sell)) : '""', T.cellN(T.cents(s.cost)),
    isSold(s) ? T.cellN(T.cents(s.sell) - T.cents(s.buy) - T.cents(s.cost)) : '""',
    T.cellT(s.buyDate || ""), T.cellT(s.receipt || ""), T.cellT(KIND_LABEL[s.kind] || ""),
  ]);
  download(T.toCsv(head, body), `sellcheck-verkaeufe-${$("t-year").value}.csv`);
});

function download(text, filename) {
  const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

$("t-clear").addEventListener("click", () => {
  if (!sales.length) return;
  if (confirm("Wirklich alle gespeicherten Einträge löschen? Das lässt sich nicht rückgängig machen.")) {
    sales = [];
    saveSales(sales);
    refresh();
  }
});


/* ---------- Eintrag bearbeiten ---------- */
const dlg = $("e-dialog");
fillSelect($("e-platform"), false);
let editing = null;
function openEdit(s) {
  editing = s;
  $("e-name").value = s.name;
  $("e-date").value = s.date;
  $("e-platform").value = s.platform;
  if (![...$("e-platform").options].some((o) => o.value === s.platform)) {
    const o = el("option", s.platform);
    o.value = s.platform;
    $("e-platform").append(o);
    $("e-platform").value = s.platform;
  }
  $("e-status").value = s.status === "stock" ? "stock" : "sold";
  $("e-buy").value = s.buy;
  $("e-sell").value = s.sell;
  $("e-cost").value = s.cost;
  $("e-buydate").value = s.buyDate || "";
  $("e-receipt").value = s.receipt || "";
  $("e-kind").value = s.kind || "";
  $("e-msg").textContent = "";
  if (typeof dlg.showModal === "function") dlg.showModal();
  else dlg.setAttribute("open", "");
  $("e-name").focus();
}
$("e-cancel").addEventListener("click", () => dlg.close());
$("e-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const name = $("e-name").value.trim();
  const date = $("e-date").value;
  if (!editing || !name || !SCTax.validIso(date)) {
    $("e-msg").textContent = "Bitte Artikel und ein gültiges Datum angeben.";
    return;
  }
  const status = $("e-status").value;
  const updated = {
    ...editing,
    name: name.slice(0, 80),
    date,
    platform: $("e-platform").value,
    status,
    buy: num($("e-buy")),
    sell: status === "stock" ? 0 : num($("e-sell")),
    cost: num($("e-cost")),
  };
  ["buyDate", "receipt", "kind"].forEach((k) => delete updated[k]);
  Object.assign(updated, optionalFields($("e-buydate").value, $("e-receipt").value, $("e-kind").value));
  if (updated.buy > 0) updated.needsBuy = editing.needsBuy; // bleibt bearbeitbar, solange es ein Import war
  const next = sales.map((x) => (x.id === editing.id ? updated : x));
  if (!SellCheck.commit(next)) {
    $("e-msg").textContent = "Speichern nicht möglich (Speicher voll oder gesperrt).";
    return;
  }
  dlg.close();
});

/* ---------- 4. Checkliste ---------- */
const SIGNALS = [
  "Ich kaufe Ware gezielt ein, um sie mit Gewinn weiterzuverkaufen.",
  "Ich verkaufe regelmäßig und dauerhaft, nicht nur beim Ausmisten.",
  "Ich biete viele gleiche oder neue Artikel an (Neuware, mehrere Stück desselben Produkts).",
  "Ich habe einen festen Ablauf: Einkauf, Lager, Fotos, Versand.",
  "Ich möchte mit dem Verkaufen Geld verdienen, nicht nur Platz schaffen.",
  "Ich habe mehr als 30 Verkäufe oder 2.000 € Einnahmen pro Jahr auf einer Plattform.",
  "Ich verkaufe auf mehreren Plattformen parallel mit hohem Aufwand.",
];

const list = $("c-list");
SIGNALS.forEach((text, i) => {
  const label = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.id = "sig" + i;
  label.append(cb, el("span", text));
  list.append(label);
});

function renderCheck() {
  const n = list.querySelectorAll("input:checked").length;
  const box = $("c-result");
  const [title, text, cls] =
    n >= 4
      ? ["Viele Merkmale treffen zu", "Bei diesem Bild lohnt sich eine persönliche Klärung mit Finanzamt oder Steuerberatung (Gewerbeanmeldung, Einkommen- und ggf. Umsatzsteuer). Bis dahin: alle Einkäufe und Verkäufe sauber dokumentieren, über alle Plattformen hinweg.", "red"]
      : n >= 2
      ? ["Einzelne Merkmale treffen zu", "Beobachte deine Entwicklung. Führe ab jetzt Buch über Einkäufe und Verkäufe und kläre im Zweifel frühzeitig, wie du eingestuft wirst.", "yellow"]
      : ["Kaum Merkmale", "Das klingt nach gelegentlichem privatem Verkauf. Behalte die Meldegrenzen im Blick, mehr ist meist nicht nötig.", "green"];
  box.className = "ampel " + cls;
  box.querySelector("strong").textContent = `${title} (${n} von ${SIGNALS.length})`;
  box.querySelector("div").textContent = text + " Das ist keine Einstufung und keine Steuerberatung.";
}
list.addEventListener("change", renderCheck);

/* ---------- Start ---------- */
renderAmpel();
renderProfit();
refresh();
renderCheck();

/* ---------- Schnittstelle für import.js ---------- */
window.SellCheck = {
  PLATFORMS,
  get sales() { return sales; },
  // Übernimmt eine neue Liste nur, wenn sie auch gespeichert werden konnte (sonst Rollback).
  commit(list) {
    const before = sales;
    sales = list;
    if (!saveSales(sales)) {
      sales = before;
      return false;
    }
    refresh();
    return true;
  },
  // Jüngster Import-Stapel (bleibt über Neuladen erhalten, weil die Stapel-ID im Eintrag steht).
  latestBatch() {
    const ids = [...new Set(sales.map((s) => s.batch).filter(Boolean))].sort((a, b) => Number(b.slice(1)) - Number(a.slice(1)));
    return ids.length ? ids[0] : null;
  },
  onRefresh(fn) { refreshListeners.push(fn); },
  download,
  showYear(y) {
    fillYears();
    $("t-year").value = y;
    $("o-year").value = y;
    renderTracker();
    renderOverview();
  },
};
