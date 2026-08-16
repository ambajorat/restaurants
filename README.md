# restaurants.ploetzlich-querschnitt.de

Barrierefreie Restaurants – Website **und** Datenquelle der App „Barrierefrei unterwegs".

| Datei | Rolle |
|---|---|
| **`hamburg-daten.json`** | **Master.** Hier neue Restaurants eintragen (Website-Format: `name, district, lat, lon, src, wc, zugang, sitzen, toilette`). |
| `hamburg.json` | **Abgeleitet** (App-Format) – wird per GitHub Action automatisch aus dem Master gebaut. Nicht von Hand ändern. |
| `index.html` | Website; lädt `hamburg-daten.json` per `fetch`. Enthält keine Daten mehr. |
| `baue_hamburg.py` | Konverter Master → `hamburg.json` (Bewertungslogik identisch zur Website). |
| `barrierefreie-restaurants.json` | Bundesweiter OSM-Feed (wöchentlich vom VPS), für die App. |

Neues Restaurant eintragen = ein Eintrag in `hamburg-daten.json` + Push. Fertig – Website und App ziehen nach.
