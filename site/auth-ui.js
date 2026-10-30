// Bedienung der Seiten anmelden.html, registrieren.html und mein.html. Verhalten und Texte wie in der App.
// Keine Inline-Skripte, Nutzerdaten nur über textContent. Ziele nach der Anmeldung sind fest (mein.html, anmelden.html), nie aus der Adresszeile.
(function () {
  "use strict";
  const A = window.SCAuth, cfg = window.SC_AUTH;
  const $ = (id) => document.getElementById(id);
  const page = document.body.dataset.page;
  const client = A.createClient({
    url: cfg.supabaseUrl, anonKey: cfg.supabaseAnonKey, storage: window.localStorage,
    redirectTo: new URL("bestaetigt.html", window.location.href).href,
  });

  function msg(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.className = "auth-msg" + (kind ? " " + kind : "");
    el.hidden = !text;
  }
  const show = (id, on) => { const el = $(id); if (el) el.hidden = !on; };
  function busy(form, on) { const b = form.querySelector('button[type="submit"]'); if (b) b.disabled = on; }
  function go(target) { window.location.href = target; }   // nur feste Ziele

  function wirePasswordToggles() {
    document.querySelectorAll("[data-toggle-pw]").forEach((b) => b.addEventListener("click", () => {
      const input = $(b.dataset.togglePw), on = input.type === "password";
      input.type = on ? "text" : "password";
      b.textContent = on ? "Verbergen" : "Anzeigen";
      b.setAttribute("aria-pressed", String(on));
    }));
  }

  function renderRules(ul, pw, email, names) {
    const r = A.evaluatePassword(pw, email, names);
    ul.textContent = "";
    const add = (text, cls) => { const li = document.createElement("li"); li.textContent = text; li.className = cls; ul.appendChild(li); };
    r.rules.forEach((x) => add(x.text, x.ok ? "ok" : ""));
    r.problems.forEach((t) => add(t, "bad"));
    return r;
  }

  function cooldown(btn, label, seconds) {
    let n = seconds;
    btn.disabled = true;
    const tick = () => {
      if (n <= 0) { btn.disabled = false; btn.textContent = label; return; }
      btn.textContent = label + " in " + n + " s"; n--; setTimeout(tick, 1000);
    };
    tick();
  }

  /* ---------- anmelden.html ---------- */
  function initLogin() {
    const m = $("msg");
    if (window.location.hash === "#abgelaufen") msg(m, "Deine Anmeldung ist abgelaufen. Melde dich noch einmal an.", "error");
    let resetEmail = "", resetSession = null;
    const steps = ["step-login", "step-code", "step-new"];
    const only = (id) => steps.forEach((s) => show(s, s === id));

    client.getSession().then((r) => { if (r.session) go("mein.html"); });

    $("login-form").addEventListener("submit", async (e) => {
      e.preventDefault(); msg(m, "");
      const f = e.target; busy(f, true);
      const r = await client.signIn($("email").value, $("password").value);
      busy(f, false);
      if (!r.ok) return msg(m, r.message, "error");
      go("mein.html");
    });

    $("forgot").addEventListener("click", async () => {
      msg(m, "");
      const r = await client.requestReset($("email").value);
      if (!r.ok) return msg(m, r.message, "error");
      resetEmail = r.email;
      $("code-intro").textContent = "Wir haben einen Code an " + resetEmail + " geschickt. Gib ihn hier ein. Danach wählst du ein neues Passwort.";
      $("code").value = ""; only("step-code"); $("code").focus();
      cooldown($("resend-code"), "Neuen Code senden", 30);
    });

    $("resend-code").addEventListener("click", async () => {
      const r = await client.requestReset(resetEmail);
      if (!r.ok) return msg(m, r.message, "error");
      msg(m, "Code gesendet.", "ok"); cooldown($("resend-code"), "Neuen Code senden", 30);
    });

    $("back-login").addEventListener("click", () => { msg(m, ""); only("step-login"); });
    $("cancel-new").addEventListener("click", () => { resetSession = null; msg(m, ""); only("step-login"); });

    $("code-form").addEventListener("submit", async (e) => {
      e.preventDefault(); msg(m, "");
      const f = e.target; busy(f, true);
      const r = await client.verifyResetCode(resetEmail, $("code").value);
      busy(f, false);
      if (!r.ok) return msg(m, r.message, "error");
      resetSession = r.session;
      $("new-intro").textContent = "Wähle jetzt ein neues Passwort für " + resetEmail + ".";
      $("newpw").value = ""; $("newpw2").value = "";
      only("step-new"); refreshNew(); $("newpw").focus();
    });

    function refreshNew() {
      const p = $("newpw").value, q = $("newpw2").value;
      const r = renderRules($("newpw-rules"), p, resetEmail, []);
      $("new-submit").disabled = !(r.valid && p === q);
      if (q && p !== q) msg(m, "Die Passwörter stimmen nicht überein.", "error"); else if ($("msg").textContent === "Die Passwörter stimmen nicht überein.") msg(m, "");
    }
    $("newpw").addEventListener("input", refreshNew);
    $("newpw2").addEventListener("input", refreshNew);

    $("new-form").addEventListener("submit", async (e) => {
      e.preventDefault(); msg(m, "");
      if (!resetSession) return only("step-login");
      const f = e.target; busy(f, true);
      const r = await client.completeReset(resetSession, $("newpw").value, []);
      busy(f, false);
      if (!r.ok) return msg(m, r.message, "error");
      go("mein.html");
    });
  }

  /* ---------- registrieren.html ---------- */
  function initRegister() {
    const m = $("msg");
    const names = () => [$("first").value, $("last").value];
    const refresh = () => renderRules($("pw-rules"), $("password").value, $("email").value, names());
    ["password", "email", "first", "last"].forEach((id) => $(id).addEventListener("input", refresh));
    refresh();
    let sentTo = "";

    $("reg-form").addEventListener("submit", async (e) => {
      e.preventDefault(); msg(m, "");
      const first = $("first").value.trim(), last = $("last").value.trim();
      if (!first) return fail("Wie heißt du mit Vornamen?", "first");
      if (!last) return fail("Wie lautet dein Nachname?", "last");
      const em = A.validateEmail($("email").value);
      if (!em.ok) return fail(em.error, "email");
      if (!$("password").value) return fail("Wähle ein Passwort. Es muss die Regeln unten erfüllen.", "password");
      const pe = A.passwordError($("password").value, em.value, [first, last]);
      if (pe) return fail(pe, "password");
      if (!$("password2").value) return fail("Gib das Passwort noch einmal ein.", "password2");
      if ($("password2").value !== $("password").value) return fail("Die Passwörter stimmen nicht überein.", "password2");
      if (!$("privacy").checked) return fail("Bitte bestätige, dass du die Datenschutzerklärung gelesen hast.", "privacy");
      const f = e.target; busy(f, true);
      const r = await client.signUp(em.value, $("password").value, {
        firstName: first, lastName: last, sellerMode: document.querySelector('input[name="seller"]:checked').value,
        privacyAccepted: true, marketingOptIn: $("marketing").checked,
      });
      busy(f, false);
      if (!r.ok) return msg(m, r.message, "error");
      if (r.session) return go("mein.html");
      sentTo = r.email;
      $("sent-text").textContent = "Wir haben eine E-Mail an " + sentTo + " geschickt. Tippe darin auf „E-Mail-Adresse bestätigen“. Danach meldest du dich an. Schau auch im Spam-Ordner nach.";
      show("step-form", false); show("step-sent", true);
      $("password").value = ""; $("password2").value = "";
      cooldown($("resend"), "Mail erneut senden", 30);
    });
    function fail(text, id) { msg(m, text, "error"); const el = $(id); if (el) el.focus(); }

    $("resend").addEventListener("click", async () => {
      const r = await client.resendConfirmation(sentTo);
      msg($("msg-sent"), r.ok ? "Mail gesendet." : r.message, r.ok ? "ok" : "error");
      if (r.ok) cooldown($("resend"), "Mail erneut senden", 30);
    });
  }

  /* ---------- mein.html ---------- */
  async function initMine() {
    const r = await client.getSession();
    if (!r.session) return go(r.expired ? "anmelden.html#abgelaufen" : "anmelden.html");
    $("who").textContent = r.session.email;
    show("mine", true);
    if (r.offline) msg($("msg"), "Keine Verbindung zum Server. Prüfe dein Internet und versuche es noch einmal.", "error");
    $("logout").addEventListener("click", async () => { await client.signOut(); go("anmelden.html"); });
  }

  wirePasswordToggles();
  if (page === "anmelden") initLogin();
  else if (page === "registrieren") initRegister();
  else if (page === "mein") initMine();
})();
