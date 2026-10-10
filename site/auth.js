// Seitenübergreifend: schützt Tools/Report und passt das Menü an (Anmelden / Abmelden).
(function () {
  "use strict";
  const A = window.SCAuth;
  const cfg = Object.assign({ required: true, supabaseUrl: "", supabaseAnonKey: "", redirectAfterLogin: "tools.html" }, window.SC_AUTH || {});
  const mode = cfg.supabaseUrl && cfg.supabaseAnonKey ? "supabase" : "demo";
  let session = null;
  try { session = A.getSession(window.localStorage, Date.now()); } catch { /* Speicher gesperrt */ }
  // Eine Demo-Sitzung gilt nicht, wenn inzwischen echte Konten aktiviert wurden (und umgekehrt).
  if (session && session.provider !== mode) session = null;
  window.SC_AUTH_STATE = { mode, session, cfg };

  const guarded = document.documentElement.dataset.auth === "required";
  if (guarded && cfg.required && !session) {
    const here = location.pathname.split("/").pop() + location.search;
    location.replace("login.html?next=" + encodeURIComponent(A.safeNext(here, "tools.html")));
    return;
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".auth-guest").forEach((e) => (e.hidden = !!session));
    document.querySelectorAll(".auth-user").forEach((e) => (e.hidden = !session));
    // Gibt es im Menü schon einen Tools-Link, braucht es den zusätzlichen nicht.
    document.querySelectorAll('.nav a.auth-user[href="tools.html"]').forEach((e) => {
      if (document.querySelector('.nav a:not(.auth-user)[href="tools.html"]')) e.hidden = true;
    });
    const out = document.getElementById("logout-btn");
    if (out && session) {
      out.title = "Angemeldet als " + session.email;
      out.addEventListener("click", async function () {
        out.disabled = true;
        try {
          if (session.provider === "supabase" && mode === "supabase") {
            await A.createSupabase({ url: cfg.supabaseUrl, anonKey: cfg.supabaseAnonKey, fetch: window.fetch.bind(window) }).signOut(session);
          }
        } catch { /* Abmelden lokal trotzdem */ }
        A.clearSession(window.localStorage);
        location.href = "index.html";
      });
    }
  });
})();
