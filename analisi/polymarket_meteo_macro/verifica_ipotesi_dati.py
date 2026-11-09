"""Verifica dell'ipotesi esplorativa (regole.md, approvata il 9/10/2026), parte che scarica i dati.

Eventi daily-temperature risolti dal 10/10/2026 al 6/11/2026 (mai usati nel Test 2). Stessa lettura degli eventi e stesso
momento di decisione del Test 2: mezzanotte locale che apre il giorno dell'evento; prezzo = ultimo punto dello storico
CLOB nelle 12 ore prima. Il fuso orario si ricava come nel Test 2 (Open-Meteo, timezone=auto, coordinate OurAirports).
Uscita: eventi_verifica.csv.gz (un esito per riga). Il conto lo fa verifica_ipotesi.py.
Va lanciato dal workflow "Analisi una tantum": dalla rete della sessione cloud le fonti non rispondono.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
import test2_storico as t2  # noqa: E402  stesso codice del Test 2

t2.INIZIO, t2.FINE = date(2026, 10, 10), date(2026, 11, 6)


def main():
    t0 = time.time()
    eventi, scartati = t2.eventi_meteo()
    print(f'eventi chiusi validi {len(eventi)}, scartati (formato) {len(scartati)}', flush=True)
    mappa = t2.aeroporti()
    gruppi = {}
    for e in eventi:
        gruppi.setdefault((e['icao'], e['unita']), set()).add(e['giorno'])
    prev, fusi, senza = {}, {}, []
    for (icao, unita), giorni in gruppi.items():
        if icao not in mappa:
            senza.append(icao)
            continue
        try:
            prev[(icao, unita)], fusi[icao] = t2.previsioni(icao, *mappa[icao], unita, giorni)
        except Exception as ex:
            senza.append(f'{icao} ({str(ex)[:60]})')
        time.sleep(0.3)
    print(f'aeroporti {len(gruppi)}, senza coordinate o fuso: {senza}', flush=True)
    lavori = []
    for e in eventi:
        if not fusi.get(e['icao']):
            continue
        g = date.fromisoformat(e['giorno'])
        e['decisione'] = datetime(g.year, g.month, g.day, tzinfo=ZoneInfo(fusi[e['icao']])).timestamp()
        e['fuso'] = fusi[e['icao']]
        e['prev_ok'] = prev.get((e['icao'], e['unita']), {}).get(e['giorno']) is not None
        lavori.extend((e, x) for x in e['esiti'])
    print(f'prezzi da leggere: {len(lavori)}', flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        prezzi = list(ex.map(lambda w: t2.prezzo_a(w[1]['token'], w[0]['decisione']), lavori))
    righe = [dict(id=e['id'], giorno=e['giorno'], icao=e['icao'], serie=e['serie'], titolo=e['titolo'], tipo=e['tipo'],
                  unita=e['unita'], fuso=e['fuso'], decisione=int(e['decisione']), prev_ok=e['prev_ok'],
                  esito=x['titolo'], lo=x['lo'], hi=x['hi'], token=str(x['token']), p=p, vince=x['vince'])
             for (e, x), p in zip(lavori, prezzi)]
    d = pd.DataFrame(righe)
    d.to_csv(QUI / 'eventi_verifica.csv.gz', index=False, compression='gzip')
    print(f'esiti salvati {len(d)}, con prezzo {d.p.notna().sum()}, eventi {d.id.nunique()}; '
          f'durata {(time.time() - t0) / 60:.1f} minuti', flush=True)


if __name__ == '__main__':
    main()
