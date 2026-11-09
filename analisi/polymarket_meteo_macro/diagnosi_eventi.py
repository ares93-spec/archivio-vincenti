"""Diagnosi una tantum (9/11/2026): perché la lettura del Test 2 scarta quasi tutti gli eventi meteo dal 10/10 al 6/11/2026.
Salva i campi utili di ogni evento (validi e scartati) in eventi_grezzi_verifica.json.gz, per il controllo in locale."""
import gzip
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
import test2_storico as t2  # noqa: E402

out, d, fine = {}, date(2026, 10, 10), date(2026, 11, 6)
while d <= fine:
    d2 = min(d + timedelta(days=3), fine)
    off = 0
    while True:
        url = (f'{t2.G}/events?tag_slug=daily-temperature&closed=true&limit=100&offset={off}'
               f'&end_date_min={d.isoformat()}T00:00:00Z&end_date_max={d2.isoformat()}T23:59:59Z')
        try:
            r = t2.gj(url)
        except Exception as ex:
            print('pagina non letta', d, off, ex)
            break
        if not isinstance(r, list) or not r:
            break
        for e in r:
            out[e.get('id')] = dict(
                id=e.get('id'), title=e.get('title'), endDate=e.get('endDate'), resolutionSource=e.get('resolutionSource'),
                seriesSlug=e.get('seriesSlug'), closed=e.get('closed'), valido=t2.compatta_meteo(e) is not None,
                markets=[{k: m.get(k) for k in ('groupItemTitle', 'clobTokenIds', 'outcomePrices', 'closedTime', 'closed',
                                                 'umaResolutionStatus', 'resolutionSource', 'question')}
                         for m in e.get('markets') or []])
        off += 100
        if len(r) < 100 or off >= 2000:
            break
        time.sleep(0.2)
    d = d2 + timedelta(days=1)
with gzip.open(QUI / 'eventi_grezzi_verifica.json.gz', 'wt') as f:
    json.dump(list(out.values()), f)
v = [e for e in out.values() if e['valido']]
s = [e for e in out.values() if not e['valido']]
print(f'eventi {len(out)}, validi {len(v)}, scartati {len(s)}')
for e in s[:8]:
    print(json.dumps({k: e[k] for k in ('title', 'resolutionSource', 'endDate')}), json.dumps(e['markets'][:2])[:600])
