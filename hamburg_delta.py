#!/usr/bin/env python3
"""Wochendatei der claude.ai-Aufgabe (Delta-Array `hamburg-neue-vorschlaege.json`)
gegen den Master `hamburg-daten.json` abgleichen und anhängen.

  python3 hamburg_delta.py                 # neueste Wochendatei suchen, nur prüfen (Trockenlauf)
  python3 hamburg_delta.py --uebernehmen   # prüfen, anhängen, committen, pushen
  python3 hamburg_delta.py PFAD [--uebernehmen]

Prüfungen: Felder wie im Master, wc/zg gültig, Koordinaten in der Hamburg-Box,
Dubletten gegen den Master (ähnlicher Name ODER gleicher Name-Kern < 150 m).
Offene Supabase-Vorschläge müssen nicht geprüft werden – beim späteren
„Übernehmen" im OSM-Push-Tool warnt hamburg_liste.dublette() gegen den Master.
"""
from __future__ import annotations
import json, math, re, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent
MASTER = REPO / "hamburg-daten.json"
SESSIONS = Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions"
BOX = (53.39, 9.73, 53.74, 10.33)          # s, w, n, o
PFLICHT = {"name", "district", "lat", "lon", "src", "wc", "zugang", "sitzen", "toilette"}
ERLAUBT = PFLICHT | {"zg"}
WC = {"yes", "limited", "no", "unknown"}
ZG = {"full", "part", "none"}
FUELL = {"restaurant", "cafe", "café", "bar", "bistro", "im", "am", "das", "der", "die", "und", "&", "hamburg"}


def tokens(name: str) -> set:
    s = name.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"\(.*?\)", " ", s)                      # Klammerzusatz (Stadtteil) weg
    return {t for t in re.findall(r"[a-z0-9]+", s) if t not in FUELL and len(t) > 1}


def gleicher_name(a: str, b: str) -> bool:
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb) and (ta <= tb or tb <= ta)


def abstand_m(a, b) -> float:
    dlat = (a["lat"] - b["lat"]) * 111_000
    dlon = (a["lon"] - b["lon"]) * 111_000 * math.cos(math.radians(53.55))
    return math.hypot(dlat, dlon)


def neueste_wochendatei() -> Path | None:
    kandidaten = sorted(SESSIONS.glob("**/outputs/hamburg-neue-vorschlaege.json"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    return kandidaten[0] if kandidaten else None


def pruefe(neu: list, master: list) -> tuple[list, list]:
    ok, abgelehnt = [], []
    for e in neu:
        fehler = []
        felder = set(e)
        if not PFLICHT <= felder: fehler.append(f"fehlende Felder {sorted(PFLICHT - felder)}")
        if felder - ERLAUBT: fehler.append(f"fremde Felder {sorted(felder - ERLAUBT)}")
        if e.get("wc") not in WC: fehler.append(f"wc={e.get('wc')!r}")
        if "zg" in e and e["zg"] not in ZG: fehler.append(f"zg={e['zg']!r}")
        if e.get("src") not in {"web", "tested"}: fehler.append(f"src={e.get('src')!r}")
        try:
            if not (BOX[0] <= float(e["lat"]) <= BOX[2] and BOX[1] <= float(e["lon"]) <= BOX[3]):
                fehler.append("Koordinate außerhalb Hamburg")
        except (KeyError, TypeError, ValueError):
            fehler.append("Koordinate fehlt/ungültig")
        if not fehler:
            for m in master + ok:
                if gleicher_name(e["name"], m["name"]) or (
                        tokens(e["name"]) & tokens(m["name"]) and abstand_m(e, m) < 150):
                    fehler.append(f"Dublette zu „{m['name']}“")
                    break
        (abgelehnt if fehler else ok).append((e, fehler))
    return [e for e, _ in ok], abgelehnt


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    uebernehmen = "--uebernehmen" in sys.argv
    pfad = Path(args[0]) if args else neueste_wochendatei()
    if not pfad or not pfad.exists():
        sys.exit("Keine Wochendatei gefunden – Pfad angeben.")
    alter_tage = (time.time() - pfad.stat().st_mtime) / 86400
    print(f"Wochendatei: {pfad}  ({alter_tage:.1f} Tage alt)")
    neu = json.loads(pfad.read_text())
    if not isinstance(neu, list):
        sys.exit("Erwartet ein JSON-Array mit neuen Objekten (Delta), keine Komplettdatei.")
    master = json.loads(MASTER.read_text())
    if len(neu) > 40:
        sys.exit(f"{len(neu)} Objekte – das sieht nach einer Komplettdatei aus, nicht nach einem Delta. Abbruch.")

    ok, abgelehnt = pruefe(neu, master)
    print(f"Master: {len(master)} Einträge · Wochendatei: {len(neu)} · übernehmbar: {len(ok)} · abgelehnt: {len(abgelehnt)}")
    for e in ok:
        print(f"  + {e['name']} ({e['district']}) wc={e['wc']}" + (f" zg={e['zg']}" if "zg" in e else ""))
    for e, fehler in abgelehnt:
        print(f"  - {e.get('name')}: {'; '.join(fehler)}")
    if not uebernehmen:
        print("\nTrockenlauf – mit --uebernehmen anhängen, committen und pushen.")
        return
    if not ok:
        print("Nichts zu übernehmen."); return

    subprocess.run(["git", "-C", str(REPO), "pull", "-q", "--rebase", "origin", "main"], check=True)
    master = json.loads(MASTER.read_text())           # nach dem Pull frisch lesen
    ok, _ = pruefe(ok, master)
    master.extend(ok)
    MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=1) + "\n")
    offen_wc = sum(1 for e in ok if e["wc"] == "unknown")
    msg = f"Hamburg: {len(ok)} neue Einträge aus der Wochensuche" + (f" ({offen_wc} WC noch zu prüfen)" if offen_wc else "")
    subprocess.run(["git", "-C", str(REPO), "add", "hamburg-daten.json"], check=True)
    subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-m", msg], check=True)
    subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"], check=True)
    print(f"\n{msg} → gepusht, Action baut hamburg.json (~1 Min). Jetzt {len(master)} Einträge.")


if __name__ == "__main__":
    main()
