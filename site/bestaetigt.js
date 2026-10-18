// Seite hinter dem Button in der Bestätigungs-Mail: Supabase hat das Konto schon bestätigt und leitet hierher.
// Die Seite öffnet die App über sellcheck://bestaetigt. Tokens im Adress-Fragment werden nicht benutzt und sofort entfernt.
(function () {
  var hash = location.hash.replace(/^#/, "");
  var failed = /(^|&)error(_code|_description)?=/.test(hash) || /(^|[?&])error=/.test(location.search);
  if (hash || location.search) history.replaceState(null, "", location.pathname);
  if (failed) {
    document.getElementById("ok").hidden = true;
    document.getElementById("fehler").hidden = false;
    document.getElementById("titel").textContent = "Der Link funktioniert nicht mehr.";
    return;
  }
  setTimeout(function () { location.href = "sellcheck://bestaetigt"; }, 400);
})();
