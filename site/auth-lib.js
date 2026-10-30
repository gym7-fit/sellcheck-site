// Passwort-Regeln und Zugang zum Konto (Supabase) für die Seiten „Mein SellCheck“. Ohne DOM, testbar in Node. Browser: window.SCAuth.
// Verhalten und Texte wie die App: sellcheck-app/SellCheck/Logic/{AuthLogic,PasswordPolicy}.swift und Auth/AuthService.swift.
// Es gibt nur echte Konten (kein Demo-Modus). Adresse und öffentlicher Schlüssel kommen als Parameter (Seite: auth-config.js, Tests: Test-Server).
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCAuth = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SESSION_KEY = "sellcheck.session.v1";
  const MIN_LENGTH = 10, MAX_LENGTH = 72;
  const REFRESH_SKEW_MS = 60000;
  const COMMON = new Set(["abc", "abcdef", "abcdefg", "admin", "administrator", "amazon", "andreas", "apple", "asdf", "asdfgh", "baseball", "basketball", "batman", "bayern", "benutzer", "berlin", "changeme", "cheese", "computer", "daniel", "default", "deutschland", "dortmund", "dragon", "ebay", "engel", "etsy", "facebook", "football", "freedom", "freiheit", "fruehling", "fussball", "gast", "geheim", "germany", "ginger", "gluecklich", "google", "guest", "hallo", "hallowelt", "hamburg", "handy", "happy", "harley", "hase", "hasi", "hello", "helloworld", "herbst", "ichliebedich", "iloveyou", "instagram", "internet", "iphone", "kennwort", "kleinanzeigen", "letmein", "liebe", "login", "master", "matrix", "mausi", "meinpasswort", "michael", "mond", "monkey", "muenchen", "mypassword", "nicole", "ninja", "nothing", "pass", "passwd", "password", "passwort", "passwort", "pepper", "pokemon", "princess", "prinzessin", "qwert", "qwerty", "qwertz", "root", "samsung", "sandra", "schalke", "schatz", "schatzi", "secret", "sellcheck", "shadow", "sommer", "sonne", "spiderman", "starwars", "stefan", "sterne", "summer", "sunshine", "superman", "test", "testen", "testtest", "thomas", "tiktok", "topsecret", "trustno", "trustnoone", "user", "verkaufen", "vintage", "vinted", "welcome", "whatever", "whatsapp", "willkommen", "winter", "yxcvbn", "zxcvbn"]);
  const WEAK_CORE = ["password", "passwort", "qwertz", "qwerty", "letmein", "iloveyou", "willkommen", "admin", "sellcheck", "geheim"];
  const KEYBOARD_ROWS = ["qwertzuiop", "asdfghjkl", "yxcvbnm", "qwertyuiop", "zxcvbnm", "1234567890", "0987654321"];
  const LEET = { "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "ä": "a", "ö": "o", "ü": "u" };
  const isLetter = (c) => /^\p{L}$/u.test(c);
  const chars = (s) => Array.from(String(s == null ? "" : s));

  /* ---------- Eingaben ---------- */
  function validateEmail(raw) {
    const v = String(raw == null ? "" : raw).trim().toLowerCase();
    const ok = v.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
    return ok ? { ok: true, value: v } : { ok: false, error: "Das ist keine gültige E-Mail-Adresse. Beispiel: du@beispiel.de" };
  }

  /* ---------- Passwort-Regeln (wie PasswordPolicy.swift) ---------- */
  function fold(p) {
    return chars(String(p).toLowerCase()).map((c) => LEET[c] || c).filter(isLetter).join("");
  }

  function hasSequence(p) {
    const lower = String(p).toLowerCase();
    const cps = Array.from(lower).map((c) => c.codePointAt(0));
    for (let i = 0; i + 3 < cps.length; i++) {
      const d1 = cps[i + 1] - cps[i], d2 = cps[i + 2] - cps[i + 1], d3 = cps[i + 3] - cps[i + 2];
      if (Math.abs(d1) === 1 && d1 === d2 && d2 === d3) return true;
    }
    for (const row of KEYBOARD_ROWS) {
      for (const r of [row, Array.from(row).reverse().join("")]) {
        for (let i = 0; i + 4 <= r.length; i++) if (lower.includes(r.slice(i, i + 4))) return true;
      }
    }
    return false;
  }

  function hasRepeat(p) {
    let run = 1, prev = null;
    for (const c of chars(p)) {
      if (c === prev) { run++; if (run >= 3) return true; } else run = 1;
      prev = c;
    }
    return false;
  }

  function isRepeatedBlock(p) {
    const c = chars(p);
    if (c.length < 6) return false;
    for (let size = 1; size <= Math.floor(c.length / 2); size++) {
      if (c.length % size) continue;
      const block = c.slice(0, size).join("");
      let all = true;
      for (let i = 0; i < c.length / size; i++) if (c.slice(i * size, (i + 1) * size).join("") !== block) { all = false; break; }
      if (all) return true;
    }
    return false;
  }

  function commonWord(p) {
    const lower = String(p).toLowerCase();
    let core = chars(lower);
    while (core.length && !isLetter(core[core.length - 1])) core.pop();
    while (core.length && !isLetter(core[0])) core.shift();
    const s = core.join("");
    return COMMON.has(s) || COMMON.has(fold(s));
  }

  function containsPersonal(folded, email, names) {
    const parts = (names || []).slice();
    const local = String(email || "").split("@")[0];
    if (local) parts.push(local);
    parts.push("sellcheck");
    return parts.some((raw) => { const f = fold(raw); return f.length >= 3 && folded.includes(f); });
  }

  function problems(p, email, names) {
    const out = [];
    const folded = fold(p);
    const letters = chars(String(p).toLowerCase()).filter(isLetter).join("");
    if (COMMON.has(letters) || COMMON.has(folded) || commonWord(p)) out.push("Dieses Passwort ist zu bekannt. Wähle etwas Eigenes.");
    else {
      const w = WEAK_CORE.find((x) => folded.includes(x));
      if (w && w.length / Math.max(folded.length, 1) >= 0.5) out.push("Das Passwort besteht fast nur aus einem bekannten Wort. Wähle etwas Eigenes.");
    }
    if (hasSequence(p)) out.push("Zahlen- oder Tastaturfolgen wie 1234, abcd oder qwertz sind zu leicht zu erraten.");
    if (hasRepeat(p)) out.push("Mehr als zwei gleiche Zeichen hintereinander sind zu leicht zu erraten.");
    if (isRepeatedBlock(p)) out.push("Ein sich wiederholender Block ist zu leicht zu erraten.");
    if (containsPersonal(folded, email, names)) out.push("Das Passwort darf deinen Namen oder deine E-Mail-Adresse nicht enthalten.");
    return out;
  }

  /** Regeln mit Haken (für die Liste unter dem Feld) und zusätzliche Verbote; gültig, wenn alles erfüllt ist. */
  function evaluatePassword(p, email, names) {
    p = String(p == null ? "" : p);
    const n = chars(p).length;
    const rules = [
      { id: "length", text: "Mindestens " + MIN_LENGTH + " Zeichen", error: "Das Passwort braucht mindestens " + MIN_LENGTH + " Zeichen. Noch " + Math.max(0, MIN_LENGTH - n) + ".", ok: n >= MIN_LENGTH && n <= MAX_LENGTH },
      { id: "upper", text: "Ein Großbuchstabe", error: "Das Passwort braucht einen Großbuchstaben.", ok: /\p{Lu}/u.test(p) },
      { id: "special", text: "Ein Sonderzeichen, zum Beispiel ! ? . - _ #", error: "Das Passwort braucht ein Sonderzeichen, zum Beispiel ! ? . - _ #.", ok: /[^\p{L}\p{N}\s]/u.test(p) },
    ];
    const probs = p ? problems(p, email, names) : [];
    return { rules, problems: probs, valid: rules.every((r) => r.ok) && probs.length === 0 };
  }

  /** Eine Meldung wie AuthLogic.passwordError: leer bei leerem Feld oder gültigem Passwort. */
  function passwordError(p, email, names) {
    if (!p) return "";
    const r = evaluatePassword(p, email, names);
    if (r.valid) return "";
    if (chars(p).length > MAX_LENGTH) return "Höchstens " + MAX_LENGTH + " Zeichen.";
    const rule = r.rules.find((x) => !x.ok);
    return rule ? rule.error : r.problems[0];
  }

  /* ---------- Antworten des Dienstes in verständliches Deutsch (wie AuthLogic.errorMessage) ---------- */
  function errorMessage(status, data, context) {
    const code = String((data && (data.error_code || data.code)) || "");
    switch (code) {
      case "invalid_credentials": return context === "signIn" ? "E-Mail oder Passwort stimmt nicht. Prüfe beides oder setze das Passwort zurück." : "Das hat nicht geklappt. Prüfe die Eingaben und versuche es noch einmal.";
      case "email_not_confirmed": return "Bestätige zuerst deine E-Mail-Adresse. Wir haben dir einen Link geschickt.";
      case "weak_password": return "Das Passwort ist zu schwach. Nimm mindestens " + MIN_LENGTH + " Zeichen mit Großbuchstabe und Sonderzeichen, und kein bekanntes Passwort.";
      case "user_already_exists": case "email_exists": return "Zu dieser Adresse gibt es schon ein Konto. Melde dich an.";
      case "same_password": return "Das neue Passwort muss anders sein als das alte.";
      case "otp_expired": return "Der Code ist falsch oder abgelaufen. Fordere einen neuen Code an.";
      case "otp_disabled": return "Die Anmeldung per E-Mail ist gerade nicht verfügbar.";
      case "over_email_send_rate_limit": case "over_request_rate_limit": return "Zu viele Anfragen. Warte eine Minute und versuche es noch einmal.";
      case "email_address_invalid": return "Diese E-Mail-Adresse wird nicht akzeptiert. Prüfe die Schreibweise.";
      case "signup_disabled": return "Neue Konten sind gerade nicht möglich.";
      default: break;
    }
    if (status === 429) return "Zu viele Anfragen. Warte eine Minute und versuche es noch einmal.";
    if ([400, 401, 403, 422].includes(status)) return "Das hat nicht geklappt. Prüfe E-Mail-Adresse und Code und versuche es noch einmal.";
    if (status >= 500) return "Der Server hat gerade ein Problem. Versuche es später noch einmal.";
    return "Das hat nicht geklappt (Fehler " + status + "). Versuche es später noch einmal.";
  }
  const NETWORK = "Keine Verbindung zum Server. Prüfe dein Internet und versuche es noch einmal.";

  /** Ziffern aus dem Code der E-Mail (6 bis 10 Stellen, Leerzeichen und Striche werden entfernt). */
  const normalizeCode = (s) => String(s == null ? "" : s).replace(/\D/g, "");
  const validCode = (s) => { const n = normalizeCode(s).length; return n >= 6 && n <= 10; };

  /** Angaben bei der Registrierung, die ins Konto gehen (wie SignupProfile.metadata() der App). */
  function signupMetadata(p, now) {
    const iso = new Date(now == null ? Date.now() : now).toISOString().replace(/\.\d{3}Z$/, "Z");
    const clip = (s) => String(s == null ? "" : s).trim().slice(0, 60);
    const m = {};
    if (clip(p.firstName)) m.first_name = clip(p.firstName);
    if (clip(p.lastName)) m.last_name = clip(p.lastName);
    const business = p.sellerMode === "business";
    m.seller_mode = business ? "business" : "private";
    if (business) { m.vat_mode = "small"; m.vat_rate = 19; }
    if (p.privacyAccepted) m.privacy_accepted_at = iso;
    m.marketing_opt_in = !!p.marketingOptIn;
    if (p.marketingOptIn) m.marketing_opt_in_at = iso;
    return m;
  }

  /* ---------- Sitzung im Browser ---------- */
  function readSession(storage) {
    try {
      const o = JSON.parse(storage.getItem(SESSION_KEY) || "null");
      if (o && typeof o.accessToken === "string" && typeof o.refreshToken === "string" && typeof o.expiresAt === "number" && typeof o.userId === "string") return o;
    } catch { /* kaputter Eintrag zählt als keine Sitzung */ }
    return null;
  }
  function saveSession(storage, s) { try { storage.setItem(SESSION_KEY, JSON.stringify(s)); } catch { /* voller oder gesperrter Speicher */ } }
  function clearSession(storage) { try { storage.removeItem(SESSION_KEY); } catch { /* nichts zu tun */ } }

  function sessionFromResponse(data, now) {
    if (!data || typeof data.access_token !== "string" || typeof data.refresh_token !== "string" || !data.user || typeof data.user.id !== "string") return null;
    const expiresAt = typeof data.expires_at === "number" ? data.expires_at * 1000 : now + (Number(data.expires_in) || 3600) * 1000;
    return { accessToken: data.access_token, refreshToken: data.refresh_token, expiresAt, userId: data.user.id, email: String(data.user.email || "").toLowerCase() };
  }

  /* ---------- Zugang zum Dienst ---------- */
  function createClient(opts) {
    const base = String(opts.url || "").replace(/\/+$/, "");
    if (!/^https?:\/\/[a-z0-9.:\-]+$/i.test(base)) throw new Error("Adresse des Dienstes fehlt oder ist ungültig.");
    const key = String(opts.anonKey || "");
    if (!key) throw new Error("Öffentlicher Schlüssel fehlt.");
    const doFetch = opts.fetch || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : null);
    const storage = opts.storage;
    const now = opts.now || (() => Date.now());
    const redirectTo = opts.redirectTo || "";

    async function request(path, { method = "POST", body, token, query } = {}) {
      const url = base + path + (query ? "?" + new URLSearchParams(query).toString() : "");
      const headers = { apikey: key, "Content-Type": "application/json", Authorization: "Bearer " + (token || key) };
      try {
        const res = await doFetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), credentials: "omit", referrerPolicy: "no-referrer" });
        let data = null;
        try { data = await res.json(); } catch { /* leere Antwort */ }
        return { status: res.status, ok: res.ok, data };
      } catch {
        return { status: 0, ok: false, data: null };
      }
    }
    const fail = (r, context) => ({ ok: false, message: r.status === 0 ? NETWORK : errorMessage(r.status, r.data, context), code: r.data && (r.data.error_code || r.data.code) || "" });

    const redirectQuery = redirectTo ? { redirect_to: redirectTo } : undefined;

    return {
      async signIn(emailRaw, password) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, message: e.error };
        if (!password) return { ok: false, message: "Gib dein Passwort ein." };
        const r = await request("/auth/v1/token", { query: { grant_type: "password" }, body: { email: e.value, password } });
        if (!r.ok) return fail(r, "signIn");
        const s = sessionFromResponse(r.data, now());
        if (!s) return { ok: false, message: "Die Antwort des Servers war unvollständig. Versuche es noch einmal." };
        saveSession(storage, s);
        return { ok: true, session: s };
      },

      async signUp(emailRaw, password, profile) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, message: e.error };
        const names = [profile && profile.firstName, profile && profile.lastName].filter(Boolean);
        const msg = passwordError(password, e.value, names);
        if (msg || !evaluatePassword(password, e.value, names).valid) return { ok: false, message: msg || "Das Passwort erfüllt die Regeln nicht." };
        const r = await request("/auth/v1/signup", { query: redirectQuery, body: { email: e.value, password, data: signupMetadata(profile || {}, now()) } });
        if (!r.ok) return fail(r, "signUp");
        const s = sessionFromResponse(r.data, now());
        if (s) { saveSession(storage, s); return { ok: true, session: s, email: e.value }; }
        return { ok: true, needsConfirmation: true, email: e.value };
      },

      async resendConfirmation(emailRaw) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, message: e.error };
        const r = await request("/auth/v1/resend", { query: redirectQuery, body: { type: "signup", email: e.value } });
        return r.ok ? { ok: true } : fail(r, "other");
      },

      /** Schritt 1 beim Zurücksetzen: Code anfordern. Immer dieselbe Antwort, egal ob es das Konto gibt. */
      async requestReset(emailRaw) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, message: e.error };
        const r = await request("/auth/v1/recover", { body: { email: e.value } });
        if (r.status === 0) return { ok: false, message: NETWORK };
        if (r.status === 429 || (r.data && /rate_limit/.test(String(r.data.error_code || "")))) return fail(r, "reset");
        return { ok: true, email: e.value };
      },

      /** Schritt 2: Code beim Server prüfen. Erst danach kommt das neue Passwort. Die Sitzung bleibt im Speicher der Seite. */
      async verifyResetCode(emailRaw, codeRaw) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, message: e.error };
        if (!validCode(codeRaw)) return { ok: false, message: "Der Code besteht nur aus Ziffern. Du findest ihn in der E-Mail." };
        const r = await request("/auth/v1/verify", { body: { type: "recovery", email: e.value, token: normalizeCode(codeRaw) } });
        if (!r.ok) return fail(r, "reset");
        const s = sessionFromResponse(r.data, now());
        if (!s) return { ok: false, message: "Die Antwort des Servers war unvollständig. Versuche es noch einmal." };
        return { ok: true, session: s };
      },

      /** Schritt 3: neues Passwort setzen (mit den Regeln) und danach angemeldet sein. */
      async completeReset(session, password, names) {
        const msg = passwordError(password, session.email, names || []);
        if (msg || !evaluatePassword(password, session.email, names || []).valid) return { ok: false, message: msg || "Das Passwort erfüllt die Regeln nicht." };
        const r = await request("/auth/v1/user", { method: "PUT", token: session.accessToken, body: { password } });
        if (!r.ok) return fail(r, "reset");
        saveSession(storage, session);
        return { ok: true, session };
      },

      /** Gültige Sitzung oder null. Erneuert 60 Sekunden vor Ablauf. Ist die Erneuerung abgelaufen: Sitzung löschen und { expired: true }. */
      async getSession() {
        const s = readSession(storage);
        if (!s) return { session: null };
        if (s.expiresAt - now() > REFRESH_SKEW_MS) return { session: s };
        const r = await request("/auth/v1/token", { query: { grant_type: "refresh_token" }, body: { refresh_token: s.refreshToken } });
        if (r.status === 0) return s.expiresAt > now() ? { session: s, offline: true } : { session: null, offline: true };
        const n = r.ok ? sessionFromResponse(r.data, now()) : null;
        if (!n) { clearSession(storage); return { session: null, expired: true }; }
        saveSession(storage, n);
        return { session: n };
      },

      /** Abmelden: Der Eintrag wird in jedem Fall gelöscht, auch wenn der Server nicht antwortet. */
      async signOut() {
        const s = readSession(storage);
        clearSession(storage);
        if (s) await request("/auth/v1/logout", { token: s.accessToken });
      },
    };
  }

  return { SESSION_KEY, MIN_LENGTH, MAX_LENGTH, validateEmail, evaluatePassword, passwordError, errorMessage, normalizeCode, validCode, signupMetadata, readSession, clearSession, createClient };
});
