// Formulare auf login.html und register.html.
(function () {
  "use strict";
  const A = window.SCAuth;
  const state = window.SC_AUTH_STATE;
  const cfg = state.cfg;
  const mode = state.mode;
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const target = A.safeNext(params.get("next"), A.safeNext(cfg.redirectAfterLogin, "tools.html"));
  const loginUrl = new URL("login.html", location.href).href;

  const client = mode === "supabase" ? A.createSupabase({ url: cfg.supabaseUrl, anonKey: cfg.supabaseAnonKey, fetch: window.fetch.bind(window) }) : null;
  const demo = A.createDemoAuth({ storage: window.localStorage, crypto: window.crypto });

  function say(kind, text) {
    const m = $("auth-msg");
    m.className = "auth-msg " + kind;
    m.textContent = text;
    m.hidden = false;
  }
  const clear = () => { const m = $("auth-msg"); if (m) m.hidden = true; };
  function busy(form, on) {
    form.querySelectorAll("button, input").forEach((e) => { if (on) { e.dataset.was = e.disabled ? "1" : ""; e.disabled = true; } else e.disabled = e.dataset.was === "1"; });
    form.setAttribute("aria-busy", on ? "true" : "false");
  }
  function finish(session) {
    A.saveSession(window.localStorage, session);
    location.replace(target);
  }

  if (mode === "demo" && $("demo-note")) $("demo-note").hidden = false;

  // Passwort anzeigen
  document.querySelectorAll("[data-toggle-pw]").forEach((b) => {
    b.addEventListener("click", () => {
      const f = $(b.dataset.togglePw);
      const show = f.type === "password";
      f.type = show ? "text" : "password";
      b.textContent = show ? "Verbergen" : "Anzeigen";
      b.setAttribute("aria-pressed", show ? "true" : "false");
    });
  });

  /* ---------- Anmeldeseite ---------- */
  const loginForm = $("login-form");
  if (loginForm) {
    // Bereits angemeldet: direkt weiter.
    if (state.session && !location.hash) { location.replace(target); return; }

    if (params.get("registered") === "1") say("ok", mode === "demo" ? "Dein Konto ist angelegt. Melde dich jetzt an." : "Dein Konto ist angelegt. Melde dich jetzt an.");
    if (params.get("registered") === "confirm") say("ok", "Wir haben dir eine E-Mail gesendet. Bestätige darin deine Adresse und melde dich danach an.");

    // Rückkehr über den Link aus einer E-Mail (Bestätigung oder Passwort-Reset).
    let recoverySession = null;
    if (client && location.hash.length > 1) {
      const r = client.sessionFromHash(location.hash);
      history.replaceState(null, "", location.pathname + location.search);
      if (r.ok && r.type === "recovery") {
        recoverySession = r.session;
        loginForm.hidden = true;
        $("reset-link-wrap").hidden = true;
        $("newpw-form").hidden = false;
        $("auth-title").textContent = "Neues Passwort setzen";
      } else if (r.ok) {
        finish(r.session);
        return;
      } else if (!r.none) {
        say("error", r.message);
      }
    }

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clear();
      busy(loginForm, true);
      try {
        const email = $("email").value;
        const pw = $("password").value;
        const r = client ? await client.signIn(email, pw) : await demo.login(email, pw);
        if (r.ok) finish(r.session);
        else { say("error", r.message); $("password").value = ""; $("password").focus(); }
      } catch {
        say("error", "Die Aktion konnte nicht ausgeführt werden. Bitte versuche es erneut.");
      } finally {
        busy(loginForm, false);
      }
    });

    // Passwort vergessen
    const resetForm = $("reset-form");
    $("reset-toggle").addEventListener("click", () => {
      clear();
      if (!client) { say("info", "Im Demo-Modus gibt es kein Zurücksetzen per E-Mail. Lege ein neues Demo-Konto mit einer anderen Adresse an."); return; }
      resetForm.hidden = !resetForm.hidden;
      if (!resetForm.hidden) { $("reset-email").value = $("email").value; $("reset-email").focus(); }
    });
    resetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clear();
      busy(resetForm, true);
      const r = await client.recover($("reset-email").value, loginUrl);
      busy(resetForm, false);
      if (r.ok) say("ok", "Wenn es zu dieser Adresse ein Konto gibt, haben wir dir eine E-Mail mit einem Link geschickt.");
      else say("error", r.message);
    });

    $("newpw-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      clear();
      const a = $("newpw").value, b = $("newpw2").value;
      if (a !== b) { say("error", "Die beiden Passwörter stimmen nicht überein."); return; }
      busy($("newpw-form"), true);
      const r = await client.updatePassword(recoverySession, a);
      busy($("newpw-form"), false);
      if (r.ok) finish(recoverySession);
      else say("error", r.message);
    });
  }

  /* ---------- Registrierung ---------- */
  const regForm = $("register-form");
  if (regForm) {
    if (state.session) { location.replace(target); return; }
    const pw = $("password");
    const hint = $("pw-hint");
    pw.addEventListener("input", () => {
      const n = pw.value.length;
      hint.textContent = n === 0 ? `Mindestens ${A.PW_MIN} Zeichen.` : n < A.PW_MIN ? `Noch ${A.PW_MIN - n} Zeichen.` : "Länge ist in Ordnung.";
      hint.className = "small " + (n >= A.PW_MIN ? "pos" : "muted");
    });

    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clear();
      if (pw.value !== $("password2").value) { say("error", "Die beiden Passwörter stimmen nicht überein."); $("password2").focus(); return; }
      if (!$("consent").checked) { say("error", "Bitte bestätige die Datenschutzhinweise."); $("consent").focus(); return; }
      busy(regForm, true);
      try {
        if (client) {
          const r = await client.signUp($("email").value, pw.value, loginUrl);
          if (!r.ok) { say("error", r.message); return; }
          if (r.needsConfirmation) {
            regForm.hidden = true;
            $("auth-title").textContent = "Bitte E-Mail bestätigen";
            $("done").hidden = false;
            $("done-text").textContent = `Wir haben eine E-Mail an ${r.email} geschickt. Klicke darin auf den Link, danach kannst du dich anmelden.`;
          } else {
            location.replace("login.html?registered=1");
          }
        } else {
          const r = await demo.register($("email").value, pw.value);
          if (!r.ok) { say("error", r.message); return; }
          location.replace("login.html?registered=1");
        }
      } catch {
        say("error", "Die Aktion konnte nicht ausgeführt werden. Bitte versuche es erneut.");
      } finally {
        busy(regForm, false);
      }
    });
  }
})();
