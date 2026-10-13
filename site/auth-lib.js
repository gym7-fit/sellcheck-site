// Anmelde-Logik ohne DOM (testbar in Node und Browser). Browser: window.SCAuth
//
// Zwei Betriebsarten:
//  - "supabase": echte Konten über Supabase Auth (E-Mail und Passwort), sobald URL und Anon-Key konfiguriert sind.
//  - "demo": Konten nur in diesem Browser (localStorage). Kein echter Schutz, nur zum Ausprobieren des Ablaufs.
//
// Wichtig: Diese Seite ist statisch. Eine Anmeldung im Browser schützt die Oberfläche, nicht die Daten:
// Alles, was im Browser liegt, kann der Besitzer des Geräts lesen. Echter Schutz entsteht erst mit Daten auf einem Server.
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SCAuth = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const SESSION_KEY = "sellcheck.session.v1";
  const ACCOUNTS_KEY = "sellcheck.demo.accounts.v1";
  const ATTEMPTS_KEY = "sellcheck.demo.attempts.v1";
  const PW_MIN = 10;
  const PW_MAX = 128;
  const DEMO_ITERATIONS = 600000; // OWASP-Empfehlung für PBKDF2-HMAC-SHA256
  const SESSION_MS = 7 * 24 * 3600 * 1000;
  const MAX_ATTEMPTS = 5;
  const LOCK_MS = 60 * 1000;
  const MAX_ACCOUNTS = 20;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  const COMMON = ["passwort123", "password123", "1234567890", "0123456789", "qwertzuiop", "qwertyuiop", "passwortpasswort", "iloveyou123", "1111111111"];

  /* ---------- Eingaben prüfen ---------- */
  function validateEmail(raw) {
    const v = String(raw == null ? "" : raw).trim().toLowerCase();
    if (!v) return { ok: false, error: "Bitte gib deine E-Mail-Adresse ein." };
    if (v.length > 254 || !EMAIL_RE.test(v)) return { ok: false, error: "Bitte gib eine gültige E-Mail-Adresse ein." };
    return { ok: true, value: v };
  }

  function validatePassword(pw, email) {
    const p = String(pw == null ? "" : pw);
    if (p.length < PW_MIN) return { ok: false, error: `Das Passwort braucht mindestens ${PW_MIN} Zeichen.` };
    if (p.length > PW_MAX) return { ok: false, error: `Das Passwort darf höchstens ${PW_MAX} Zeichen haben.` };
    if (/^\d+$/.test(p)) return { ok: false, error: "Das Passwort darf nicht nur aus Ziffern bestehen." };
    if (new Set(p).size < 4) return { ok: false, error: "Das Passwort ist zu einfach. Nutze mehr verschiedene Zeichen." };
    if (COMMON.includes(p.toLowerCase())) return { ok: false, error: "Dieses Passwort ist zu bekannt. Bitte wähle ein anderes." };
    if (email && p.toLowerCase() === String(email).toLowerCase()) return { ok: false, error: "Das Passwort darf nicht deiner E-Mail-Adresse entsprechen." };
    return { ok: true };
  }

  /* ---------- Hilfen ---------- */
  const b64 = (bytes) => btoa(String.fromCharCode(...bytes));
  const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  function timingSafeEqual(a, b) {
    if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
    let d = 0;
    for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return d === 0;
  }
  const readJson = (storage, key, fallback) => {
    try {
      const v = JSON.parse(storage.getItem(key) || "null");
      return v && typeof v === "object" ? v : fallback;
    } catch {
      return fallback;
    }
  };
  const writeJson = (storage, key, v) => {
    try {
      storage.setItem(key, JSON.stringify(v));
      return true;
    } catch {
      return false;
    }
  };

  async function pbkdf2(password, salt, iterations, cryptoImpl) {
    const enc = new TextEncoder();
    const key = await cryptoImpl.subtle.importKey("raw", enc.encode(String(password).normalize("NFKC")), "PBKDF2", false, ["deriveBits"]);
    const bits = await cryptoImpl.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256);
    return new Uint8Array(bits);
  }

  /* ---------- Sitzung ---------- */
  function getSession(storage, now) {
    const s = readJson(storage, SESSION_KEY, null);
    if (!s || (s.provider !== "demo" && s.provider !== "supabase")) return null;
    if (typeof s.email !== "string" || typeof s.exp !== "number" || s.exp <= now) {
      try { storage.removeItem(SESSION_KEY); } catch { /* ignorieren */ }
      return null;
    }
    if (s.provider === "supabase" && typeof s.accessToken !== "string") return null;
    return s;
  }
  const saveSession = (storage, s) => writeJson(storage, SESSION_KEY, s);
  function clearSession(storage) {
    try { storage.removeItem(SESSION_KEY); } catch { /* ignorieren */ }
  }

  // Nur diese Ziele sind nach der Anmeldung erlaubt (kein offener Weiterleitungs-Missbrauch).
  function safeNext(raw, fallback) {
    const v = String(raw == null ? "" : raw);
    return /^(tools|report)\.html(\?y=\d{4})?$/.test(v) ? v : fallback || "tools.html";
  }

  /* ---------- Demo-Modus (nur lokal) ---------- */
  function createDemoAuth(opts) {
    const storage = opts.storage;
    const cryptoImpl = opts.crypto;
    const now = opts.now || (() => Date.now());
    const iterations = opts.iterations || DEMO_ITERATIONS;
    const random = opts.random || ((n) => cryptoImpl.getRandomValues(new Uint8Array(n)));

    const accounts = () => readJson(storage, ACCOUNTS_KEY, {});
    const attempts = () => readJson(storage, ATTEMPTS_KEY, {});

    async function register(emailRaw, password) {
      const e = validateEmail(emailRaw);
      if (!e.ok) return { ok: false, code: "email", message: e.error };
      const p = validatePassword(password, e.value);
      if (!p.ok) return { ok: false, code: "password", message: p.error };
      const acc = accounts();
      if (acc[e.value]) return { ok: false, code: "exists", message: "Mit dieser E-Mail-Adresse gibt es schon ein Konto. Bitte melde dich an." };
      if (Object.keys(acc).length >= MAX_ACCOUNTS) return { ok: false, code: "limit", message: "In diesem Browser sind zu viele Demo-Konten angelegt." };
      const salt = random(16);
      const hash = await pbkdf2(password, salt, iterations, cryptoImpl);
      acc[e.value] = { salt: b64(salt), hash: b64(hash), iter: iterations, created: now() };
      if (!writeJson(storage, ACCOUNTS_KEY, acc)) return { ok: false, code: "storage", message: "Das Konto konnte nicht gespeichert werden (Speicher voll oder gesperrt)." };
      return { ok: true, email: e.value };
    }

    async function login(emailRaw, password) {
      const e = validateEmail(emailRaw);
      if (!e.ok) return { ok: false, code: "email", message: e.error };
      const att = attempts();
      const a = att[e.value] || { n: 0, until: 0 };
      if (a.until > now()) {
        const sec = Math.ceil((a.until - now()) / 1000);
        return { ok: false, code: "locked", message: `Zu viele Versuche. Bitte warte ${sec} Sekunden.` };
      }
      const acc = accounts()[e.value];
      // Auch ohne Konto rechnen, damit die Antwortzeit nichts verrät.
      const salt = acc ? unb64(acc.salt) : random(16);
      const hash = b64(await pbkdf2(password, salt, acc ? acc.iter || iterations : iterations, cryptoImpl));
      if (!acc || !timingSafeEqual(hash, acc.hash)) {
        a.n = (a.n || 0) + 1;
        if (a.n >= MAX_ATTEMPTS) { a.until = now() + LOCK_MS; a.n = 0; }
        att[e.value] = a;
        writeJson(storage, ATTEMPTS_KEY, att);
        return { ok: false, code: "credentials", message: "E-Mail oder Passwort stimmt nicht." };
      }
      delete att[e.value];
      writeJson(storage, ATTEMPTS_KEY, att);
      const session = { provider: "demo", email: e.value, exp: now() + SESSION_MS };
      saveSession(storage, session);
      return { ok: true, session };
    }

    return { register, login, logout: () => clearSession(storage), accountCount: () => Object.keys(accounts()).length };
  }

  /* ---------- Supabase Auth (echte Konten) ---------- */
  function decodeJwt(token) {
    try {
      const part = String(token).split(".")[1];
      const json = atob(part.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(part.length / 4) * 4, "="));
      const o = JSON.parse(json);
      return o && typeof o === "object" ? o : null;
    } catch {
      return null;
    }
  }

  function parseHash(hash) {
    const h = String(hash || "").replace(/^#/, "");
    if (!h) return {};
    const q = new URLSearchParams(h);
    return {
      accessToken: q.get("access_token") || "",
      refreshToken: q.get("refresh_token") || "",
      expiresIn: Number(q.get("expires_in")) || 0,
      type: q.get("type") || "",
      error: q.get("error_description") || q.get("error") || "",
    };
  }

  function mapSupabaseError(status, data) {
    const code = String((data && (data.error_code || data.code)) || "").toLowerCase();
    const msg = String((data && (data.msg || data.message || data.error_description || data.error)) || "").toLowerCase();
    const has = (...k) => k.some((x) => code.includes(x) || msg.includes(x));
    if (has("invalid_credentials", "invalid login")) return { code: "credentials", message: "E-Mail oder Passwort stimmt nicht." };
    if (has("email_not_confirmed", "not confirmed")) return { code: "unconfirmed", message: "Bitte bestätige zuerst deine E-Mail-Adresse. Wir haben dir einen Link geschickt." };
    if (has("user_already_exists", "email_exists", "already registered")) return { code: "exists", message: "Mit dieser E-Mail-Adresse gibt es schon ein Konto. Bitte melde dich an." };
    if (has("weak_password", "password should")) return { code: "password", message: "Das Passwort ist zu schwach. Nutze mindestens 10 Zeichen mit verschiedenen Zeichen." };
    if (has("rate_limit", "too many")) return { code: "rate", message: "Zu viele Versuche. Bitte warte einen Moment und versuche es erneut." };
    if (has("signup_disabled", "signups not allowed")) return { code: "disabled", message: "Neue Registrierungen sind im Moment nicht möglich." };
    if (status === 0) return { code: "network", message: "Keine Verbindung zum Anmeldedienst. Bitte prüfe deine Internetverbindung." };
    return { code: "unknown", message: "Die Aktion konnte nicht ausgeführt werden. Bitte versuche es später erneut." };
  }

  function createSupabase(opts) {
    const base = String(opts.url || "").replace(/\/+$/, "");
    if (!/^https:\/\/[a-z0-9.-]+$/i.test(base)) throw new Error("Supabase-URL muss mit https:// beginnen.");
    const key = String(opts.anonKey || "");
    if (!key) throw new Error("Supabase-Anon-Key fehlt.");
    const doFetch = opts.fetch;
    const now = opts.now || (() => Date.now());

    async function request(path, { method = "POST", body, token, query } = {}) {
      const url = base + path + (query ? "?" + new URLSearchParams(query).toString() : "");
      const headers = { apikey: key, "Content-Type": "application/json" };
      if (token) headers.Authorization = "Bearer " + token;
      const ctl = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timer = ctl ? setTimeout(() => ctl.abort(), 15000) : null;
      try {
        const res = await doFetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined, credentials: "omit", referrerPolicy: "no-referrer", signal: ctl ? ctl.signal : undefined });
        let data = null;
        try { data = await res.json(); } catch { /* leere Antwort */ }
        return { status: res.status, ok: res.ok, data };
      } catch {
        return { status: 0, ok: false, data: null };
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    function toSession(data, fallbackEmail) {
      if (!data || typeof data.access_token !== "string") return null;
      const claims = decodeJwt(data.access_token) || {};
      const fromExpires = data.expires_in ? now() + Number(data.expires_in) * 1000 : 0;
      const exp = claims.exp ? claims.exp * 1000 : fromExpires;
      if (!exp || exp <= now()) return null;
      return {
        provider: "supabase",
        email: String((data.user && data.user.email) || claims.email || fallbackEmail || "").toLowerCase(),
        exp,
        accessToken: data.access_token,
        refreshToken: typeof data.refresh_token === "string" ? data.refresh_token : "",
      };
    }

    return {
      async signUp(emailRaw, password, redirectTo) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, code: "email", message: e.error };
        const p = validatePassword(password, e.value);
        if (!p.ok) return { ok: false, code: "password", message: p.error };
        const r = await request("/auth/v1/signup", { body: { email: e.value, password }, query: redirectTo ? { redirect_to: redirectTo } : undefined });
        if (!r.ok) return { ok: false, ...mapSupabaseError(r.status, r.data) };
        const session = toSession(r.data, e.value);
        // Mit E-Mail-Bestätigung kommt keine Sitzung zurück: Der Nutzer muss erst den Link in der Mail öffnen.
        return { ok: true, email: e.value, needsConfirmation: !session };
      },
      async signIn(emailRaw, password) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, code: "email", message: e.error };
        if (!password) return { ok: false, code: "password", message: "Bitte gib dein Passwort ein." };
        const r = await request("/auth/v1/token", { query: { grant_type: "password" }, body: { email: e.value, password } });
        if (!r.ok) return { ok: false, ...mapSupabaseError(r.status, r.data) };
        const session = toSession(r.data, e.value);
        if (!session) return { ok: false, code: "unknown", message: "Die Anmeldung konnte nicht abgeschlossen werden." };
        return { ok: true, session };
      },
      async refresh(session) {
        if (!session || !session.refreshToken) return null;
        const r = await request("/auth/v1/token", { query: { grant_type: "refresh_token" }, body: { refresh_token: session.refreshToken } });
        return r.ok ? toSession(r.data, session.email) : null;
      },
      async signOut(session) {
        if (session && session.accessToken) await request("/auth/v1/logout", { token: session.accessToken });
      },
      async recover(emailRaw, redirectTo) {
        const e = validateEmail(emailRaw);
        if (!e.ok) return { ok: false, code: "email", message: e.error };
        const r = await request("/auth/v1/recover", { body: { email: e.value }, query: redirectTo ? { redirect_to: redirectTo } : undefined });
        // Immer dieselbe Antwort, damit niemand herausfinden kann, wer ein Konto hat.
        if (!r.ok && r.status === 0) return { ok: false, ...mapSupabaseError(0, null) };
        return { ok: true };
      },
      async updatePassword(session, password) {
        const p = validatePassword(password);
        if (!p.ok) return { ok: false, code: "password", message: p.error };
        const r = await request("/auth/v1/user", { method: "PUT", token: session.accessToken, body: { password } });
        return r.ok ? { ok: true } : { ok: false, ...mapSupabaseError(r.status, r.data) };
      },
      sessionFromHash(hash) {
        const h = parseHash(hash);
        if (h.error) return { ok: false, message: "Der Link ist abgelaufen oder ungültig. Bitte fordere einen neuen an." };
        if (!h.accessToken) return { ok: false, none: true };
        const session = toSession({ access_token: h.accessToken, refresh_token: h.refreshToken, expires_in: h.expiresIn }, "");
        if (!session) return { ok: false, message: "Der Link ist abgelaufen oder ungültig. Bitte fordere einen neuen an." };
        return { ok: true, session, type: h.type };
      },
    };
  }

  return {
    SESSION_KEY, ACCOUNTS_KEY, PW_MIN, PW_MAX, DEMO_ITERATIONS, SESSION_MS, MAX_ATTEMPTS, LOCK_MS,
    validateEmail, validatePassword, timingSafeEqual, getSession, saveSession, clearSession, safeNext,
    createDemoAuth, createSupabase, decodeJwt, parseHash, mapSupabaseError,
  };
});
