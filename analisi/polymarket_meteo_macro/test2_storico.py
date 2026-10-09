"""Test 2 (regole in regole.md, fissate il 9/10/2026): modello meteo contro prezzo di mercato su eventi risolti,
più la calibrazione dei prezzi su meteo e macro. Solo dati pubblici, nessuna operatività.

Uscite: risultati_test2.txt (resoconto), eventi_meteo.csv.gz e prezzi_macro.csv.gz (dati compatti per ricontrollare)."""
import io
import json
import math
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from scipy.stats import norm

QUI = Path(__file__).resolve().parent
G = 'https://gamma-api.polymarket.com'
C = 'https://clob.polymarket.com'
SEME = 20261009
MAX_EVENTI = 2500
INIZIO, FINE = date(2025, 12, 1), date(2026, 10, 8)
S = requests.Session()
S.headers['User-Agent'] = 'archivio-vincenti/1.0 (ricerca personale)'
RIGHE = []


def log(t=''):
    print(t, flush=True)
    RIGHE.append(str(t))


def gj(url, tentativi=5):
    ultimo = None
    for i in range(tentativi):
        try:
            r = S.get(url, timeout=90)
            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            ultimo = e
            time.sleep(2 * (i + 1))
    raise ultimo if ultimo else RuntimeError('429 ripetuti')


# ---------------------------------------------------------------------------------------------------------
# esiti: "15°C or below", "16°C", "88-89°F", "96°F or higher", "-2°C"
RX_ESITO = re.compile(r'^\s*(-?\d+)(?:\s*-\s*(-?\d+))?\s*°\s*([CF])\s*(or below|or lower|or higher|or above)?', re.I)
MESI = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                    'september', 'october', 'november', 'december'], 1)}


def leggi_esito(t):
    m = RX_ESITO.match(t or '')
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) is not None else a
    unita = m.group(3).upper()
    coda = (m.group(4) or '').lower()
    if coda in ('or below', 'or lower'):
        return (-math.inf, a, unita)
    if coda in ('or higher', 'or above'):
        return (a, math.inf, unita)
    return (a, b, unita)


def compatta_meteo(e):
    titolo = e.get('title') or ''
    tipo = 'max' if titolo.lower().startswith('highest') else ('min' if titolo.lower().startswith('lowest') else None)
    m = re.search(r' on ([A-Za-z]+) (\d{1,2})\??$', titolo.strip())
    fonte = e.get('resolutionSource') or ''
    icao = fonte.rstrip('/').split('/')[-1].upper() if 'wunderground' in fonte else None
    if not tipo or not m or not icao or m.group(1).lower() not in MESI:
        return None
    anno = int((e.get('endDate') or '2026')[:4])
    try:
        giorno = date(anno, MESI[m.group(1).lower()], int(m.group(2)))
    except ValueError:
        return None
    esiti = []
    for mk in e.get('markets') or []:
        es = leggi_esito(mk.get('groupItemTitle'))
        ids = mk.get('clobTokenIds')
        ids = json.loads(ids) if isinstance(ids, str) else ids
        prezzi = mk.get('outcomePrices')
        prezzi = json.loads(prezzi) if isinstance(prezzi, str) else prezzi
        if not es or not ids or not prezzi:
            return None
        esiti.append(dict(lo=es[0], hi=es[1], unita=es[2], token=ids[0], vince=str(prezzi[0]) == '1',
                          titolo=mk.get('groupItemTitle'), chiusura=mk.get('closedTime')))
    if len(esiti) < 3 or sum(x['vince'] for x in esiti) != 1 or len({x['unita'] for x in esiti}) != 1:
        return None
    return dict(id=e.get('id'), titolo=titolo, tipo=tipo, giorno=giorno.isoformat(), icao=icao,
                serie=e.get('seriesSlug'), unita=esiti[0]['unita'], esiti=sorted(esiti, key=lambda x: x['lo']))


def eventi_meteo():
    tutti = {}
    d = INIZIO
    while d <= FINE:
        d2 = min(d + timedelta(days=3), FINE)
        off = 0
        while True:
            url = (f'{G}/events?tag_slug=daily-temperature&closed=true&limit=100&offset={off}'
                   f'&end_date_min={d.isoformat()}T00:00:00Z&end_date_max={d2.isoformat()}T23:59:59Z')
            try:
                r = gj(url)
            except Exception as ex:
                log(f'  pagina non letta {d}..{d2} offset {off}: {ex}')
                break
            if not isinstance(r, list) or not r:
                break
            for e in r:
                c = compatta_meteo(e)
                if c:
                    tutti[c['id']] = c
                else:
                    tutti.setdefault('scartati', []).append(e.get('title'))
            off += 100
            if len(r) < 100 or off >= 2000:
                break
            time.sleep(0.2)
        d = d2 + timedelta(days=1)
    scartati = tutti.pop('scartati', [])
    return list(tutti.values()), scartati


# ---------------------------------------------------------------------------------------------------------
def aeroporti():
    r = S.get('https://davidmegginson.github.io/ourairports-data/airports.csv', timeout=120)
    r.raise_for_status()
    a = pd.read_csv(io.StringIO(r.text), usecols=['ident', 'gps_code', 'icao_code', 'latitude_deg', 'longitude_deg'],
                    dtype=str)
    mappa = {}
    for col in ('ident', 'gps_code', 'icao_code'):
        for _, x in a.dropna(subset=[col]).iterrows():
            mappa.setdefault(x[col].upper(), (float(x.latitude_deg), float(x.longitude_deg)))
    return mappa


def previsioni(icao, lat, lon, unita, giorni):
    """Massima e minima del giorno locale dalla previsione emessa il giorno prima. Restituisce ({giorno: (max, min)}, fuso)."""
    g0, g1 = min(giorni), max(giorni)
    url = ('https://previous-runs-api.open-meteo.com/v1/forecast?latitude={:.4f}&longitude={:.4f}'
           '&hourly=temperature_2m_previous_day1&timezone=auto&temperature_unit={}&start_date={}&end_date={}').format(
        lat, lon, 'fahrenheit' if unita == 'F' else 'celsius', g0, g1)
    j = gj(url)
    h = pd.DataFrame({'t': pd.to_datetime(j['hourly']['time']), 'v': j['hourly']['temperature_2m_previous_day1']})
    h['g'] = h.t.dt.date.astype(str)
    agg = h.dropna().groupby('g').v.agg(['max', 'min', 'count'])
    agg = agg[agg['count'] >= 20]
    return {g: (r['max'], r['min']) for g, r in agg.iterrows()}, j.get('timezone')


def prezzo_a(token, ts):
    """Ultimo prezzo dello storico CLOB nelle 12 ore prima di ts (secondi UTC)."""
    try:
        h = gj(f'{C}/prices-history?market={token}&startTs={int(ts - 12 * 3600)}&endTs={int(ts)}&fidelity=10')
        st = [x for x in (h.get('history') or []) if x.get('t', 0) <= ts]
        return float(st[-1]['p']) if st else None
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------
def prob_modello(esiti, centro, sigma):
    p = []
    for x in esiti:
        a = -math.inf if x['lo'] == -math.inf else x['lo'] - 0.5
        b = math.inf if x['hi'] == math.inf else x['hi'] + 0.5
        p.append(norm.cdf(b, centro, sigma) - norm.cdf(a, centro, sigma))
    p = np.clip(np.array(p), 1e-4, 1)
    return p / p.sum()


def brier(p, y):
    return float(((p - y) ** 2).sum())


def calibrazione(df, etichetta):
    fasce = [0, .05, .15, .30, .50, .70, .85, .95, 1.0001]
    df = df.dropna(subset=['p'])
    df = df.assign(fascia=pd.cut(df.p, fasce, right=False))
    log(f'\nCalibrazione {etichetta} (prezzi grezzi degli esiti SÌ; n = esiti)')
    log(f'{"fascia":>14} {"n":>6} {"prezzo medio":>13} {"freq. reale":>12} {"err.std":>8} {"diff/err":>9}')
    for f, g in df.groupby('fascia', observed=True):
        n = len(g)
        fr = g.y.mean()
        se = math.sqrt(max(fr * (1 - fr), 1e-9) / n)
        log(f'{str(f):>14} {n:>6} {g.p.mean():>13.4f} {fr:>12.4f} {se:>8.4f} {(fr - g.p.mean()) / se:>9.2f}')


# ---------------------------------------------------------------------------------------------------------
def test_meteo():
    log('=== TEST 2, METEO: modello contro mercato ===')
    eventi, scartati = eventi_meteo()
    log(f'eventi chiusi letti e validi: {len(eventi)}; scartati (formato non riconosciuto): {len(scartati)}; '
        f'es. scartati: {scartati[:5]}')
    if len(eventi) > MAX_EVENTI:
        random.Random(SEME).shuffle(eventi)
        eventi = eventi[:MAX_EVENTI]
        log(f'campione casuale di {MAX_EVENTI} eventi (seme {SEME})')
    mappa = aeroporti()
    # previsioni per aeroporto e unità
    gruppi = {}
    for e in eventi:
        gruppi.setdefault((e['icao'], e['unita']), set()).add(e['giorno'])
    prev, fusi, senza = {}, {}, []
    for (icao, unita), giorni in gruppi.items():
        if icao not in mappa:
            senza.append(icao)
            continue
        try:
            prev[(icao, unita)], fusi[icao] = previsioni(icao, *mappa[icao], unita, giorni)
        except Exception as ex:
            senza.append(f'{icao} ({str(ex)[:60]})')
        time.sleep(0.3)
    log(f'aeroporti: {len(gruppi)}; senza coordinate o previsioni: {senza}')
    # momento della decisione e prezzi
    lavori = []
    for e in eventi:
        f = prev.get((e['icao'], e['unita']), {}).get(e['giorno'])
        if f is None or not fusi.get(e['icao']):
            continue
        g = date.fromisoformat(e['giorno'])
        t = datetime(g.year, g.month, g.day, tzinfo=ZoneInfo(fusi[e['icao']])).timestamp()
        e['previsione'] = f[0] if e['tipo'] == 'max' else f[1]
        e['decisione'] = t
        for x in e['esiti']:
            lavori.append((e, x))
    log(f'eventi con previsione: {len({id(e) for e, _ in lavori})}; prezzi da leggere: {len(lavori)}')
    with ThreadPoolExecutor(max_workers=8) as ex:
        prezzi = list(ex.map(lambda ex_: prezzo_a(ex_[1]['token'], ex_[0]['decisione']), lavori))
    for (e, x), p in zip(lavori, prezzi):
        x['p'] = p
    validi = []
    for e in eventi:
        if 'previsione' not in e:
            continue
        mancanti = sum(x.get('p') is None for x in e['esiti'])
        if mancanti > 2:
            continue
        validi.append(e)
    log(f'eventi validi (al massimo 2 prezzi mancanti): {len(validi)}')
    if len(validi) < 50:
        log('troppo pochi eventi validi: test non eseguibile')
        return
    validi.sort(key=lambda e: e['giorno'])
    meta = len(validi) // 2
    adde, veri = validi[:meta], validi[meta:]
    log(f'addestramento: {len(adde)} eventi ({adde[0]["giorno"]} - {adde[-1]["giorno"]}); '
        f'verifica: {len(veri)} eventi ({veri[0]["giorno"]} - {veri[-1]["giorno"]})')
    # distorsione e sigma
    res = {}
    for e in adde:
        w = [x for x in e['esiti'] if x['vince']][0]
        if math.isinf(w['lo']) or math.isinf(w['hi']):
            continue
        res.setdefault((e['icao'], e['tipo']), []).append((w['lo'] + w['hi']) / 2 - e['previsione'])
        res.setdefault(('*', e['tipo'], e['unita']), []).append((w['lo'] + w['hi']) / 2 - e['previsione'])

    def parametri(e):
        r = res.get((e['icao'], e['tipo']), [])
        if len(r) < 15:
            r = res.get(('*', e['tipo'], e['unita']), [0.0])
        return float(np.mean(r)), max(float(np.std(r, ddof=1)) if len(r) > 1 else 3.0, 1.0)

    for chiave in sorted(k for k in res if k[0] == '*'):
        r = res[chiave]
        log(f'  globale {chiave[1]} {chiave[2]}: n={len(r)}, distorsione {np.mean(r):+.2f}, sigma {np.std(r, ddof=1):.2f}')
    righe = []
    for e in veri:
        y = np.array([1.0 if x['vince'] else 0.0 for x in e['esiti']])
        pm = np.array([x['p'] if x.get('p') is not None else np.nan for x in e['esiti']])
        pm = np.where(np.isnan(pm), 0.0, pm)
        if pm.sum() <= 0:
            continue
        pm = np.clip(pm / pm.sum(), 1e-4, 1)
        pm = pm / pm.sum()
        b, s = parametri(e)
        pmod = prob_modello(e['esiti'], e['previsione'] + b, s)
        pmix = (pm + pmod) / 2
        iw = int(np.argmax(y))
        righe.append(dict(giorno=e['giorno'], icao=e['icao'], tipo=e['tipo'], unita=e['unita'], esiti=len(y),
                          brier_mercato=brier(pm, y), brier_modello=brier(pmod, y), brier_mix=brier(pmix, y),
                          ll_mercato=-math.log(pm[iw]), ll_modello=-math.log(pmod[iw]), ll_mix=-math.log(pmix[iw]),
                          p_vincente_mercato=pm[iw], p_vincente_modello=pmod[iw], sigma=s, distorsione=b))
    d = pd.DataFrame(righe)
    d.to_csv(QUI / 'verifica_meteo.csv.gz', index=False, compression='gzip')
    log(f'\nVerifica: {len(d)} eventi')
    for col in ('brier', 'll'):
        log(f'  {col}: mercato {d[col + "_mercato"].mean():.4f} | modello {d[col + "_modello"].mean():.4f} | '
            f'miscela 50/50 {d[col + "_mix"].mean():.4f}')
    diff = (d.brier_modello - d.brier_mercato).values
    rng = np.random.default_rng(SEME)
    boot = np.array([diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(10000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    log(f'  differenza Brier modello - mercato: {diff.mean():+.4f} (IC95% bootstrap {lo:+.4f} / {hi:+.4f})')
    diffm = (d.brier_mix - d.brier_mercato).values
    bootm = np.array([diffm[rng.integers(0, len(diffm), len(diffm))].mean() for _ in range(10000)])
    lom, him = np.percentile(bootm, [2.5, 97.5])
    log(f'  differenza Brier miscela - mercato: {diffm.mean():+.4f} (IC95% bootstrap {lom:+.4f} / {him:+.4f})')
    citta = d.groupby('icao').filter(lambda g: len(g) >= 20).groupby('icao').apply(
        lambda g: (g.brier_modello.mean() < g.brier_mercato.mean()), include_groups=False)
    log(f'  città con almeno 20 eventi di verifica: {len(citta)}; il modello batte il mercato in {int(citta.sum())}')
    c1 = hi < 0
    c2 = len(citta) > 0 and citta.sum() >= math.ceil(2 * len(citta) / 3)
    log(f'\nCRITERIO 1 (Brier migliore con IC che esclude zero): {"SUPERATO" if c1 else "NON SUPERATO"}')
    log(f'CRITERIO 2 (almeno 2/3 delle città): {"SUPERATO" if c2 else "NON SUPERATO"}')
    log(f'VERDETTO TEST 2 METEO: {"SUPERATO" if (c1 and c2) else "NON SUPERATO"}')
    log(f'Miscela 50/50 migliore del mercato con IC che esclude zero: {"SÌ" if him < 0 else "NO"}')
    log('\nDettaglio per tipo e unità (Brier medio)')
    log(d.groupby(['tipo', 'unita'])[['brier_mercato', 'brier_modello', 'brier_mix']].agg(['mean', 'count']).round(4).to_string())
    log('\nDettaglio per città (verifica)')
    log(d.groupby('icao')[['brier_mercato', 'brier_modello']].mean().round(4).assign(
        n=d.groupby('icao').size()).sort_values('n', ascending=False).to_string())
    # calibrazione meteo su tutti gli eventi validi
    cal = [dict(p=x.get('p'), y=1.0 if x['vince'] else 0.0) for e in validi for x in e['esiti']]
    calibrazione(pd.DataFrame(cal), 'meteo (tutti gli eventi validi, alla mezzanotte locale che apre il giorno)')
    # dati compatti
    comp = [dict(id=e['id'], giorno=e['giorno'], icao=e['icao'], tipo=e['tipo'], unita=e['unita'],
                 previsione=e['previsione'], esito=x['titolo'], lo=x['lo'], hi=x['hi'], p=x.get('p'), vince=x['vince'])
            for e in validi for x in e['esiti']]
    pd.DataFrame(comp).to_csv(QUI / 'eventi_meteo.csv.gz', index=False, compression='gzip')


# ---------------------------------------------------------------------------------------------------------
SERIE_MACRO = {'us-monthly-inflation', 'us-annual-inflation', 'core-cpi', 'core-cpi-mom', 'jobs-added', 'unemployment',
               'fed-interest-rates', 'fomc', 'core-pce-mom', 'core-pce-yoy', 'ppi-yoy', 'weekly-jobless-claims',
               'gdp-quarterly'}


def test_macro():
    log('\n=== CALIBRAZIONE MACRO ===')
    eventi = {}
    for slug in ('macro-indicators', 'inflation', 'cpi', 'jobs-report', 'fed', 'fed-rates', 'gdp', 'economy'):
        for off in range(0, 3000, 100):
            try:
                r = gj(f'{G}/events?tag_slug={slug}&closed=true&limit=100&offset={off}')
            except Exception:
                break
            if not isinstance(r, list) or not r:
                break
            for e in r:
                if e.get('seriesSlug') in SERIE_MACRO:
                    eventi[e['id']] = e
            time.sleep(0.2)
    log(f'eventi macro chiusi nelle serie scelte: {len(eventi)}')
    righe = []
    lavori = []
    for e in eventi.values():
        chiusure = []
        for mk in e.get('markets') or []:
            try:
                chiusure.append(pd.Timestamp(mk.get('closedTime')).timestamp())
            except Exception:
                pass
        if not chiusure:
            continue
        t = min(chiusure) - 24 * 3600
        for mk in e.get('markets') or []:
            ids = mk.get('clobTokenIds')
            ids = json.loads(ids) if isinstance(ids, str) else ids
            pr = mk.get('outcomePrices')
            pr = json.loads(pr) if isinstance(pr, str) else pr
            if ids and pr and str(pr[0]) in ('0', '1'):
                lavori.append((e, mk, ids[0], t, float(pr[0])))
    with ThreadPoolExecutor(max_workers=8) as ex:
        prezzi = list(ex.map(lambda w: prezzo_a(w[2], w[3]), lavori))
    for (e, mk, tok, t, y), p in zip(lavori, prezzi):
        righe.append(dict(serie=e.get('seriesSlug'), evento=e.get('title'), esito=mk.get('groupItemTitle') or mk.get('question'),
                          p=p, y=y, decisione=datetime.fromtimestamp(t, timezone.utc).isoformat()))
    d = pd.DataFrame(righe)
    d.to_csv(QUI / 'prezzi_macro.csv.gz', index=False, compression='gzip')
    log(f'esiti con prezzo 24 ore prima: {d.p.notna().sum()} su {len(d)}')
    log('esiti per serie: ' + ', '.join(f'{k}:{v}' for k, v in d.dropna(subset=["p"]).serie.value_counts().items()))
    calibrazione(d, 'macro (24 ore prima della prima chiusura dell\'evento)')
    dd = d.dropna(subset=['p'])
    b = ((dd.p - dd.y) ** 2).groupby(dd.serie).mean().round(4)
    log('\nBrier medio per esito, per serie:\n' + b.to_string())


if __name__ == '__main__':
    t0 = time.time()
    for f in (test_meteo, test_macro):
        try:
            f()
        except Exception as ex:
            import traceback
            log(f'ERRORE in {f.__name__}: {ex}')
            log(traceback.format_exc())
    log(f'\ndurata: {(time.time() - t0) / 60:.1f} minuti')
    (QUI / 'risultati_test2.txt').write_text('\n'.join(RIGHE))
