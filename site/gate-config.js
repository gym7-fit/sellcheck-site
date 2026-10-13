// Freischaltung per E-Mail: Einstellungen. Diese Datei darf öffentlich sein.
// Solange beide Endpunkte leer sind, wird NICHTS gesendet (Vorabversion): Die Adresse schaltet das Ergebnis
// nur lokal frei, und der Report lässt sich per mailto-Link an die eigene Adresse vorbereiten.
// Anschluss und rechtliche Punkte: docs/EMAIL-ZUGANG.md
window.SC_GATE = {
  // https://… Endpunkt des E-Mail-Dienstes (Double-Opt-In für Tipps und Tricks). Host in der CSP (connect-src) freigeben.
  leadEndpoint: "",
  // https://… Endpunkt, der den Report per E-Mail an die angegebene Adresse versendet.
  reportEndpoint: "",
};
