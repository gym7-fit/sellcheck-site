"""Lädt die Auswahl aus VSCO-2-CE (CC0) nach samples/. Liste: samples_list.txt (120 Dateien, ca. 273 MB: gehaltene Streicher, Klavier, Pauke), samples_list_extra.txt (141 Dateien, ca. 69 MB: kurze Streicher, Schlagzeug, Becken)."""
import os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
base="https://raw.githubusercontent.com/sgossner/VSCO-2-CE/master/"
here=os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
paths=[l.strip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),(sys.argv[1] if len(sys.argv) > 1 else "samples_list.txt"))) if l.strip()]
def get(p):
    dest=os.path.join(here,p)
    if os.path.exists(dest) and os.path.getsize(dest)>1000: return 0
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    url=base+urllib.parse.quote(p)
    for k in range(3):
        try:
            with urllib.request.urlopen(url,timeout=60) as r, open(dest,"wb") as f: f.write(r.read())
            return os.path.getsize(dest)
        except Exception as ex:
            err=ex
    print("FEHLER",p,err); return -1
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(get,paths))
print("geladen:",sum(1 for r in res if r>0),"übersprungen:",sum(1 for r in res if r==0),"Fehler:",sum(1 for r in res if r<0),"Summe MB: %.0f"%(sum(r for r in res if r>0)/1e6))
