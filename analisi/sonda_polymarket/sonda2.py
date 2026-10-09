"""Seconda sonda (9/10/2026): mercati giornalieri di temperatura, serie macro ricorrenti, Open-Meteo."""
import json
import time
from collections import Counter
from pathlib import Path

import requests

QUI = Path(__file__).resolve().parent
OUT = QUI / 'campioni2'
OUT.mkdir(exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'archivio-vincenti/1.0 (ricerca personale)'
G = 'https://gamma-api.polymarket.com'
C = 'https://clob.polymarket.com'
RIGHE = []


def log(t):
    print(t, flush=True)
    RIGHE.append(str(t))


def gj(url, **kw):
    r = S.get(url, timeout=90, **kw)
    r.raise_for_status()
    return r.json()


def pagine(slug, chiuso, massimo=20000):
    tutti = []
    for off in range(0, massimo, 100):
        try:
            r = gj(f'{G}/events?tag_slug={slug}&closed={chiuso}&limit=100&offset={off}')
        except Exception as e:
            log(f'  errore pagina {off}: {e}')
            break
        if not isinstance(r, list) or not r:
            break
        tutti.extend(r)
        time.sleep(0.25)
    return tutti


# 1. temperatura giornaliera: aperti e chiusi
for chiuso in ('false', 'true'):
    ev = pagine('daily-temperature', chiuso)
    fini = sorted(e.get('endDate') or '' for e in ev)
    serie = Counter(e.get('seriesSlug') for e in ev)
    log(f'daily-temperature chiuso={chiuso}: {len(ev)} eventi, fine da {fini[:1]} a {fini[-1:]}; serie: {len(serie)}')
    log('  serie piu frequenti: ' + ', '.join(f'{k}:{v}' for k, v in serie.most_common(60)))
    tit = Counter(' '.join((e.get('title') or '').split()[:2]) for e in ev)
    log('  tipi di titolo: ' + str(tit.most_common(8)))
    (OUT / f'daily_temperature_{"chiusi" if chiuso == "true" else "aperti"}_campione.json').write_text(json.dumps(ev[:4], indent=1))
    # elenco compatto di tutti gli eventi (per pianificare il test)
    compatto = [dict(id=e.get('id'), titolo=e.get('title'), serie=e.get('seriesSlug'), fine=e.get('endDate'),
                     inizio=e.get('startDate'), creato=e.get('createdAt'), volume=e.get('volume'),
                     fonte=e.get('resolutionSource'), mercati=len(e.get('markets') or [])) for e in ev]
    (OUT / f'daily_temperature_{"chiusi" if chiuso == "true" else "aperti"}_elenco.json').write_text(json.dumps(compatto))
    if ev:
        e = ev[0] if chiuso == 'false' else ev[-1]
        log(f'  esempio: {e.get("title")} | fonte: {e.get("resolutionSource")}')
        log(f'  descrizione evento: {(e.get("description") or "")[:900]}')
        for m in (e.get('markets') or [])[:12]:
            log(f'    {m.get("groupItemTitle")} | {m.get("question")} | esito {m.get("outcomePrices")} | best {m.get("bestBid")}/{m.get("bestAsk")} '
                f'| ricompense {m.get("rewardsMinSize")}/{m.get("rewardsMaxSpread")} {m.get("clobRewards")} | fee {m.get("feeSchedule")} {m.get("feesEnabled")} '
                f'| volume {m.get("volume")} | chiusura {m.get("closedTime")}')
        if chiuso == 'true':
            # storico prezzi di un evento chiuso recente
            recenti = sorted(ev, key=lambda x: x.get('endDate') or '')[-30:]
            e = recenti[0]
            log(f'  storico per: {e.get("title")} fine {e.get("endDate")} creato {e.get("createdAt")}')
            for m in (e.get('markets') or [])[:3]:
                ids = m.get('clobTokenIds')
                ids = json.loads(ids) if isinstance(ids, str) else ids
                for fid in (1, 10, 60):
                    try:
                        h = gj(f'{C}/prices-history?market={ids[0]}&startTs=1700000000&fidelity={fid}')
                        st = h.get('history') or []
                        log(f'    {m.get("groupItemTitle")} fidelity={fid}: {len(st)} punti, da {st[:1]} a {st[-1:]}')
                    except Exception as ex:
                        log(f'    errore storico: {ex}')

# 2. macro ricorrenti: serie e quantità di eventi chiusi
for slug in ('macro-indicators', 'jobs-report', 'cpi', 'fed', 'fed-rates', 'inflation', 'gdp', 'economy'):
    ev = pagine(slug, 'true', 3000)
    serie = Counter(e.get('seriesSlug') for e in ev)
    log(f'{slug} chiusi: {len(ev)}; serie: ' + ', '.join(f'{k}:{v}' for k, v in serie.most_common(15)))
    log('  titoli recenti: ' + ' | '.join((e.get('title') or '') for e in sorted(ev, key=lambda x: x.get('endDate') or '')[-12:]))
    aperti = pagine(slug, 'false', 2000)
    log(f'{slug} aperti: {len(aperti)}; es.: ' + ' | '.join((e.get('title') or '') for e in aperti[:15]))

# 3. Open-Meteo
for nome, url in [
    ('previous_runs', 'https://previous-runs-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87&hourly=temperature_2m,'
     'temperature_2m_previous_day1,temperature_2m_previous_day2&temperature_unit=fahrenheit&timezone=America/New_York'
     '&start_date=2026-09-01&end_date=2026-09-02'),
    ('previous_runs_2024', 'https://previous-runs-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87&hourly='
     'temperature_2m_previous_day1&temperature_unit=fahrenheit&start_date=2024-06-01&end_date=2024-06-01'),
    ('historical_forecast', 'https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=40.78&longitude=-73.87'
     '&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=America/New_York&start_date=2026-04-01&end_date=2026-04-03'),
    ('ensemble', 'https://ensemble-api.open-meteo.com/v1/ensemble?latitude=40.78&longitude=-73.87&daily=temperature_2m_max'
     '&models=gfs_seamless&temperature_unit=fahrenheit&forecast_days=2'),
    ('archivio_era5', 'https://archive-api.open-meteo.com/v1/archive?latitude=40.78&longitude=-73.87&daily=temperature_2m_max'
     '&temperature_unit=fahrenheit&start_date=2026-04-01&end_date=2026-04-03'),
]:
    try:
        r = S.get(url, timeout=60)
        log(f'open-meteo {nome}: HTTP {r.status_code}; {r.text[:700]}')
    except Exception as e:
        log(f'open-meteo {nome}: ERRORE {e}')

(QUI / 'risultati2.txt').write_text('\n'.join(RIGHE))
