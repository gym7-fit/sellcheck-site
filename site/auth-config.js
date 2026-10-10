// Anmeldung: Einstellungen. Diese Datei darf öffentlich sein (der Anon-Key ist kein Geheimnis).
// Mehr dazu: docs/AUTH-SETUP.md
window.SC_AUTH = {
  // true: Tools und Report nur nach Anmeldung. false: alles frei nutzbar, Anmeldung bleibt optional.
  required: true,

  // Echte Konten über Supabase Auth. Beides ausfüllen, dann ist der Demo-Modus aus.
  // WICHTIG: ein EIGENES Supabase-Projekt für SellCheck verwenden, NICHT das der VITARO-Seiten.
  supabaseUrl: "https://xjogkqttzfsgjeqhkndf.supabase.co",
  supabaseAnonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhqb2drcXR0emZzZ2plcWhrbmRmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE2NzU2OTEsImV4cCI6MjEwNzI1MTY5MX0.LSe8DIWQ4Ib02QHtHND_MkJiWfLeA-qEXTH_0v5f3L8", // öffentlicher "anon"-Key (kein Geheimnis)

  // Wohin nach erfolgreicher Anmeldung (nur tools.html oder report.html erlaubt)
  redirectAfterLogin: "tools.html",
};
