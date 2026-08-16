#!/usr/bin/env python3
"""
Erzeugt hamburg.json (App-Format) aus hamburg-daten.json (Master, Website-Format).

    hamburg-daten.json  ← EINZIGE Quelle: hier neue Restaurants eintragen
    hamburg.json        ← abgeleitet, NICHT von Hand bearbeiten
    index.html          ← lädt hamburg-daten.json per fetch

Läuft automatisch per GitHub Action bei jeder Änderung an hamburg-daten.json
(.github/workflows/hamburg.yml). Lokal: python3 baue_hamburg.py

Die Bewertungslogik (zugangGrade / scoreOf) ist 1:1 aus index.html portiert –
Website und App bewerten identisch. Nur Standardbibliothek.
"""
import json, re, unicodedata
from pathlib import Path

HIER = Path(__file__).resolve().parent
MASTER = HIER / "hamburg-daten.json"
ZIEL = HIER / "hamburg.json"


# --- Bewertung wie index.html -------------------------------------------------

def zugang_grade(r):
    if r.get("zg"):
        return r["zg"]                        # expliziter Wert (z. B. OSM)
    t = (r.get("zugang") or "").lower()
    if not t or "detailnotiz" in t:
        return "unknown"
    if "beschwerlich" in t or "durch die küche" in t:
        return "part"
    if any(w in t for w in ("einfach", "gut", "barrierefrei", "rampe", "fahrstuhl", "aufzug")):
        return "full"
    return "part"


def score_of(r):
    g = zugang_grade(r)
    if g == "unknown" and r.get("wc") == "unknown":
        return None                           # zu wenig Infos → kein Rating
    wc = {"yes": 4, "limited": 2}.get(r.get("wc"), 0)
    zg = {"full": 3, "part": 1.5}.get(g, 0)
    pl = 2 if r.get("sitzen") else 0
    st = {"tested": 1, "web": 0.5}.get(r.get("src"), 0)
    return round((wc + zg + pl + st) * 10) / 10


# --- Mapping Website-Format → App-Format (Models/Restaurant.swift) -------------

WC = {"yes": "barrierefrei", "limited": "eingeschraenkt", "no": "nein"}
ZUGANG = {"full": "stufenlos", "part": "eingeschraenkt"}
QUELLE = {"tested": "selbst_getestet", "web": "recherchiert"}


def slug(name):
    s = unicodedata.normalize("NFKD", name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
                              .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def zu_app(r):
    notiz = " · ".join(f"{k}: {r[f]}" for k, f in (("Zugang", "zugang"), ("Sitzen", "sitzen"), ("Toilette", "toilette"))
                       if r.get(f))
    s = score_of(r)
    return {
        "id": "hh-" + slug(r["name"]),
        "name": r["name"],
        "stadt": "Hamburg",
        "district": r.get("district"),
        "lat": r["lat"],
        "lon": r["lon"],
        "quelle": QUELLE.get(r.get("src"), "recherchiert"),
        "wc": WC.get(r.get("wc"), "unbekannt"),
        "zugang": ZUGANG.get(zugang_grade(r), "unbekannt"),
        "platz": True if r.get("sitzen") else None,
        "score": int(s) if s is not None and float(s).is_integer() else s,
        "notiz": notiz or None,
        "adresse": r.get("adresse"),
    }


def main():
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    app = [zu_app(r) for r in master]
    ids = [a["id"] for a in app]
    doppelt = {i for i in ids if ids.count(i) > 1}
    if doppelt:
        raise SystemExit(f"doppelte IDs: {doppelt}")
    ZIEL.write_text(json.dumps(app, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{ZIEL.name}: {len(app)} Einträge aus {MASTER.name}")


if __name__ == "__main__":
    main()
