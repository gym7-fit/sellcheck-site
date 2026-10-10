// Wartelisten-Formulare (Härtung: https-Pflicht, Einwilligung, Honeypot, Abkühlzeit, Timeout).
// Solange FORM_ENDPOINT leer ist, wird NICHTS gespeichert oder gesendet (Demo-Modus).
// Vor dem Livegang:
//  1. Endpunkt eines EU-E-Mail-Dienstes mit Double-Opt-In eintragen (muss mit https:// beginnen).
//  2. Denselben Host in der CSP (Datei _headers, Zeile connect-src) freigeben.
//  3. Datenschutzerklärung und Impressum ausfüllen.
const FORM_ENDPOINT = "";

const COOLDOWN_MS = 5000;
const TIMEOUT_MS = 10000;
const CONSENT_TEXT = "Ich möchte per E-Mail über den Start informiert werden.";
let lastSent = 0;

function endpointOk() {
  try {
    return new URL(FORM_ENDPOINT).protocol === "https:";
  } catch {
    return false;
  }
}

document.querySelectorAll("form.waitlist").forEach((form) => {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const note = form.querySelector(".form-note");
    const email = form.email.value.trim();
    if (email.length > 254 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      note.textContent = "Bitte gib eine gültige E-Mail-Adresse ein.";
      return;
    }
    if (!form.consent.checked) {
      note.textContent = "Bitte bestätige zuerst deine Einwilligung.";
      return;
    }
    // Honeypot: Menschen sehen das Feld nicht. Bots füllen es und bekommen eine unauffällige "Danke"-Antwort.
    if (form.website.value) {
      note.textContent = "Danke!";
      return;
    }
    if (!FORM_ENDPOINT) {
      note.textContent = "Demo-Modus: Das Formular ist noch nicht angeschlossen, es wurde nichts gespeichert.";
      return;
    }
    if (!endpointOk()) {
      console.error("FORM_ENDPOINT muss eine https://-Adresse sein.");
      note.textContent = "Das Formular ist falsch eingerichtet. Bitte später noch einmal versuchen.";
      return;
    }
    if (Date.now() - lastSent < COOLDOWN_MS) {
      note.textContent = "Bitte einen Moment warten.";
      return;
    }
    lastSent = Date.now();
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    try {
      const res = await fetch(FORM_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: form.dataset.source, consent: true, consentText: CONSENT_TEXT, consentAt: new Date().toISOString() }),
        credentials: "omit",
        referrerPolicy: "no-referrer",
        redirect: "error",
        signal: ctl.signal,
      });
      if (!res.ok) throw new Error(res.status);
      form.reset();
      note.textContent = "Danke! Bitte bestätige noch den Link in der E-Mail, die wir dir schicken.";
    } catch {
      note.textContent = "Das hat leider nicht geklappt. Bitte versuche es später noch einmal.";
    } finally {
      clearTimeout(timer);
    }
  });
});
