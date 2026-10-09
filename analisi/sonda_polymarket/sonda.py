"""Sonda una tantum (9/10/2026): campioni reali delle fonti per i test Polymarket su meteo e macro.
Salva le risposte grezze (accorciate) in analisi/sonda_polymarket/campioni/ e un riassunto in risultati.txt."""
import json
import time
from pathlib import Path

import requests

QUI = Path(__file__).resolve().parent
OUT = QUI / 'campioni'
OUT.mkdir(exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'archivio-vincenti/1.0 (ricerca personale)'
G = 'https://gamma-api.polymarket.com'
C = 'https://clob.polymarket.com'
RIGHE = []


def log(t):
    print(t, flush=True)
    RIGHE.append(t)


def prendi(nome, url, metodo='GET', corpo=None, taglia=None):
    try:
        r = S.post(url, json=corpo, timeout=60) if metodo == 'POST' else S.get(url, timeout=60)
        testo = r.text
        log(f'{nome}: HTTP {r.status_code}, {len(testo)} caratteri')
        try:
            j = r.json()
        except Exception:
            (OUT / f'{nome}.txt').write_text(testo[:20000])
            return None
        da_salvare = j[:taglia] if (taglia and isinstance(j, list)) else j
        (OUT / f'{nome}.json').write_text(json.dumps(da_salvare, indent=1)[:400000])
        return j
    except Exception as e:
        log(f'{nome}: ERRORE {e}')
        return None


def chiavi(x):
    return sorted(x.keys()) if isinstance(x, dict) else type(x).__name__


# 1. etichette
tags = prendi('tags', f'{G}/tags?limit=1000', taglia=None) or []
interessanti = [t for t in tags if isinstance(t, dict) and any(k in (t.get('slug') or '').lower() for k in
                ('weather', 'temperat', 'climate', 'econom', 'fed', 'inflation', 'cpi', 'jobs', 'unemploy', 'gdp',
                 'rates', 'macro', 'finance', 'recession', 'payroll', 'fomc'))]
log('etichette interessanti: ' + ', '.join(f"{t.get('slug')}({t.get('id')})" for t in interessanti[:80]))

# 2. eventi aperti e chiusi per etichetta
for slug in ('weather', 'temperature', 'economy', 'economics', 'fed', 'fed-rates', 'inflation', 'cpi', 'jobs-report',
             'economic-policy', 'finance'):
    for chiuso in ('false', 'true'):
        ev = prendi(f'eventi_{slug}_{"chiusi" if chiuso == "true" else "aperti"}',
                    f'{G}/events?tag_slug={slug}&closed={chiuso}&limit=50&order=endDate&ascending=false', taglia=5)
        if isinstance(ev, list) and ev:
            e0 = ev[0]
            log(f'  {slug} chiuso={chiuso}: {len(ev)} eventi; es. "{e0.get("title")}" fine {e0.get("endDate")}; '
                f'mercati {len(e0.get("markets") or [])}; chiavi evento {chiavi(e0)[:40]}')
            m = (e0.get('markets') or [{}])[0]
            log(f'    chiavi mercato: {chiavi(m)}')
        time.sleep(0.5)

# 3. un mercato meteo aperto: libro e storico
ev = prendi('meteo_aperti_completi', f'{G}/events?tag_slug=weather&closed=false&limit=100', taglia=3) or []
token = None
for e in ev:
    for m in e.get('markets') or []:
        ids = m.get('clobTokenIds')
        ids = json.loads(ids) if isinstance(ids, str) else ids
        if ids and m.get('active') and not m.get('closed'):
            token, mercato = ids, m
            break
    if token:
        break
log(f'eventi meteo aperti: {len(ev)}; token scelto: {token}')
if token:
    log(f'  domanda: {mercato.get("question")}; descrizione: {(mercato.get("description") or "")[:600]}')
    prendi('libro', f'{C}/book?token_id={token[0]}')
    prendi('libri_post', f'{C}/books', 'POST', [{'token_id': t} for t in token])
    prendi('storico_aperto', f'{C}/prices-history?market={token[0]}&interval=1w&fidelity=60')
    prendi('mercato_clob', f'{C}/markets/{mercato.get("conditionId")}')

# 4. un mercato meteo chiuso: storico completo dei prezzi
evc = prendi('meteo_chiusi_completi', f'{G}/events?tag_slug=weather&closed=true&limit=100&order=endDate&ascending=false', taglia=3) or []
log(f'eventi meteo chiusi (prima pagina): {len(evc)}')
if evc:
    titoli = [e.get('title') for e in evc[:40]]
    log('  titoli: ' + ' | '.join(str(t) for t in titoli))
    for m in (evc[0].get('markets') or [])[:2]:
        ids = m.get('clobTokenIds')
        ids = json.loads(ids) if isinstance(ids, str) else ids
        log(f'  chiuso: {m.get("question")} prezzi esito {m.get("outcomePrices")} fine {m.get("endDate")} '
            f'chiusura {m.get("closedTime")}')
        if ids:
            h = prendi('storico_chiuso', f'{C}/prices-history?market={ids[0]}&interval=max&fidelity=60')
            if isinstance(h, dict):
                log(f'    punti storico: {len(h.get("history") or [])}')
            h2 = prendi('storico_chiuso_startts', f'{C}/prices-history?market={ids[0]}&startTs=1759000000&fidelity=60')
            break
# quante pagine di eventi meteo chiusi esistono
tot = 0
for off in range(0, 5000, 100):
    r = S.get(f'{G}/events?tag_slug=weather&closed=true&limit=100&offset={off}', timeout=60).json()
    if not r:
        break
    tot += len(r)
    ultimo = r[-1].get('endDate')
    time.sleep(0.3)
log(f'eventi meteo chiusi in totale (fino a 5.000): {tot}; il più vecchio letto finisce {ultimo if tot else None}')

# 5. Open-Meteo: previsioni emesse nei giorni precedenti (Previous Runs API) e storiche
prendi('openmeteo_previous_runs',
       'https://previous-runs-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87&hourly=temperature_2m,'
       'temperature_2m_previous_day1,temperature_2m_previous_day2&temperature_unit=fahrenheit&timezone=America/New_York'
       '&start_date=2026-09-01&end_date=2026-09-03')
prendi('openmeteo_historical_forecast',
       'https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87&daily=temperature_2m_max'
       '&temperature_unit=fahrenheit&timezone=America/New_York&start_date=2025-01-01&end_date=2025-01-05')
prendi('openmeteo_ensemble',
       'https://ensemble-api.open-meteo.com/v1/ensemble?latitude=40.78&longitude=-73.87&hourly=temperature_2m'
       '&models=gfs_seamless&temperature_unit=fahrenheit&forecast_days=2')
prendi('openmeteo_previous_runs_vecchio',
       'https://previous-runs-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87&hourly='
       'temperature_2m_previous_day1&temperature_unit=fahrenheit&start_date=2024-06-01&end_date=2024-06-02')

(QUI / 'risultati.txt').write_text('\n'.join(RIGHE))
