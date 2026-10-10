// Anmeldung: Einstellungen. Diese Datei darf öffentlich sein (der Anon-Key ist kein Geheimnis).
// Mehr dazu: docs/AUTH-SETUP.md
window.SC_AUTH = {
  // true: Tools und Report nur nach Anmeldung. false: alles frei nutzbar, Anmeldung bleibt optional.
  required: true,

  // Echte Konten über Supabase Auth. Beides ausfüllen, dann ist der Demo-Modus aus.
  // WICHTIG: ein EIGENES Supabase-Projekt für SellCheck verwenden, NICHT das der VITARO-Seiten.
  supabaseUrl: "",       // z. B. "https://abcdefgh.supabase.co"
  supabaseAnonKey: "",   // öffentlicher "anon"/"publishable" Key aus Project Settings → API

  // Wohin nach erfolgreicher Anmeldung (nur tools.html oder report.html erlaubt)
  redirectAfterLogin: "tools.html",
};
