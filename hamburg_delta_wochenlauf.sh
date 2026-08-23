#!/bin/zsh
# Wochenlauf (launchd, Mo 9:00): Wochendatei prüfen (Trockenlauf) und das Ergebnis
# als macOS-Mitteilung zeigen. Übernommen wird NICHT automatisch – das bleibt
#   python3 ~/restaurants-repo/hamburg_delta.py --uebernehmen
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
LOG=~/restaurants-repo/hamburg_delta.log
OUT=$(/usr/bin/python3 ~/restaurants-repo/hamburg_delta.py 2>&1)
RC=$?
{ echo "=== $(date '+%Y-%m-%d %H:%M')"; echo "$OUT"; } >> "$LOG"
ALTER=$(echo "$OUT" | grep -o '([0-9.]* Tage alt)' | grep -o '[0-9.]*' | head -1)
ZUS=$(echo "$OUT" | grep '^Master:' | sed 's/ · /, /g')
if [ $RC -ne 0 ]; then
  MSG="Abgleich fehlgeschlagen – siehe hamburg_delta.log"
elif [ -n "$ALTER" ] && [ "${ALTER%%.*}" -ge 8 ]; then
  MSG="Keine neue Wochendatei (letzte ist ${ALTER%%.*} Tage alt)"
else
  N=$(echo "$OUT" | grep -o 'übernehmbar: [0-9]*' | grep -o '[0-9]*')
  if [ "${N:-0}" -gt 0 ]; then
    MSG="$N neue Hamburg-Einträge übernehmbar – Terminal: hamburg_delta.py --uebernehmen"
  else
    MSG="Nichts Neues übernehmbar ($ZUS)"
  fi
fi
/usr/bin/osascript -e "display notification \"$MSG\" with title \"Hamburg-Liste: Wochenabgleich\""
