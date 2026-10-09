"""Test 1 (regole in regole.md): fotografia dei libri ordini dei mercati meteo e macro di Polymarket ogni 10 minuti.

Gira per circa 5 ore e 40 minuti (un job di GitHub Actions dura al massimo 6 ore); il workflow lo rilancia ogni 6 ore.
Si ferma da solo dopo il 6/11/2026. Salva in dati_test/libri/<anno>/:
  <inizio>_libri.csv.gz    una riga per esito SÌ e fotografia, solo quando il libro è cambiato (campo hash)
  <inizio>_scambi.csv.gz   scambi nuovi dei mercati seguiti (Data API)
  <inizio>_mercati.csv.gz  elenco dei mercati con parametri dei premi e commissioni (aggiornato ogni ora)
"""
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

RADICE = Path(__file__).resolve().parents[2]
USCITA = RADICE / 'dati_test' / 'libri'
G = 'https://gamma-api.polymarket.com'
C = 'https://clob.polymarket.com'
D = 'https://data-api.polymarket.com'
FINE_TEST = datetime(2026, 11, 6, 23, 59, tzinfo=timezone.utc)
DURATA = 5 * 3600 + 40 * 60
PASSO = 600                  # 10 minuti (5 minuti pesavano circa 17 MB al giorno)
CITTA = ('nyc', 'london', 'seoul', 'miami', 'chicago', 'dallas', 'atlanta', 'toronto', 'paris', 'tokyo',
         'buenos-aires', 'seattle')
NOMI_CITTA = ('NYC', 'New York', 'London', 'Seoul', 'Miami', 'Chicago', 'Dallas', 'Atlanta', 'Toronto', 'Paris',
              'Tokyo', 'Buenos Aires', 'Seattle')
SERIE_MACRO = {'us-monthly-inflation', 'us-annual-inflation', 'core-cpi', 'core-cpi-mom', 'jobs-added', 'unemployment',
               'fed-interest-rates', 'fomc', 'core-pce-mom', 'core-pce-yoy', 'ppi-yoy', 'weekly-jobless-claims',
               'gdp-quarterly'}
S = requests.Session()
S.headers['User-Agent'] = 'archivio-vincenti/1.0 (ricerca personale)'


def gj(url, metodo='GET', corpo=None, tentativi=4):
    ultimo = None
    for i in range(tentativi):
        try:
            r = S.post(url, json=corpo, timeout=60) if metodo == 'POST' else S.get(url, timeout=60)
            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            ultimo = e
            time.sleep(2 * (i + 1))
    raise ultimo if ultimo else RuntimeError('429 ripetuti')


def eventi(slug, chiuso='false', massimo=2000):
    out = []
    for off in range(0, massimo, 100):
        try:
            r = gj(f'{G}/events?tag_slug={slug}&closed={chiuso}&limit=100&offset={off}')
        except Exception:
            break
        if not isinstance(r, list) or not r:
            break
        out.extend(r)
        if len(r) < 100:
            break
        time.sleep(0.2)
    return out


def scegli_mercati(adesso):
    """Elenco dei mercati da fotografare: meteo delle 12 città entro 48 ore, macro entro 45 giorni."""
    scelti = []
    limite_meteo = adesso + timedelta(hours=48)
    for e in eventi('daily-temperature'):
        serie = (e.get('seriesSlug') or '').lower()
        titolo = e.get('title') or ''
        if not (any(serie.startswith(c + '-') for c in CITTA) or any(f' in {n} ' in titolo for n in NOMI_CITTA)):
            continue
        try:
            fine = datetime.fromisoformat((e.get('endDate') or '').replace('Z', '+00:00'))
        except ValueError:
            continue
        if fine > limite_meteo:
            continue
        scelti.extend(('meteo', e, m) for m in e.get('markets') or [])
    visti = set()
    limite_macro = adesso + timedelta(days=45)
    for slug in ('macro-indicators', 'inflation', 'jobs-report', 'fed-rates', 'gdp'):
        for e in eventi(slug, massimo=600):
            if e.get('seriesSlug') not in SERIE_MACRO or e.get('id') in visti:
                continue
            visti.add(e.get('id'))
            try:
                fine = datetime.fromisoformat((e.get('endDate') or '').replace('Z', '+00:00'))
            except ValueError:
                continue
            if fine > limite_macro:
                continue
            scelti.extend(('macro', e, m) for m in e.get('markets') or [])
    righe = []
    for tipo, e, m in scelti:
        if m.get('closed') or not m.get('acceptingOrders', True):
            continue
        ids = m.get('clobTokenIds')
        ids = json.loads(ids) if isinstance(ids, str) else ids
        if not ids:
            continue
        premi = m.get('clobRewards') or []
        tasso = sum(float(p.get('rewardsDailyRate') or 0) for p in premi if isinstance(p, dict))
        righe.append(dict(tipo=tipo, evento_id=e.get('id'), evento=e.get('title'), serie=e.get('seriesSlug'),
                          fine_evento=e.get('endDate'), neg_risk=e.get('negRisk'), mercato_id=m.get('id'),
                          condizione=m.get('conditionId'), token_si=ids[0], esito=m.get('groupItemTitle') or m.get('question'),
                          premi_min=m.get('rewardsMinSize'), premi_spread=m.get('rewardsMaxSpread'), premi_giorno=tasso,
                          commissioni=json.dumps(m.get('feeSchedule')), volume=m.get('volumeNum') or m.get('volume'),
                          liquidita=m.get('liquidityNum'), tick=m.get('orderPriceMinTickSize'), minimo=m.get('orderMinSize')))
    return pd.DataFrame(righe)


def livelli(lista, verso):
    """Livelli ordinati dal migliore: verso='bid' prezzi decrescenti, 'ask' crescenti."""
    out = []
    for x in lista or []:
        try:
            out.append((float(x['price']), float(x['size'])))
        except (KeyError, TypeError, ValueError):
            pass
    return sorted(out, key=lambda t: -t[0] if verso == 'bid' else t[0])


def riga_libro(b, meta, ora):
    bid, ask = livelli(b.get('bids'), 'bid'), livelli(b.get('asks'), 'ask')
    bb = bid[0][0] if bid else None
    ba = ask[0][0] if ask else None
    mid = (bb + ba) / 2 if bb is not None and ba is not None else None
    r = dict(ora=ora, id=meta.get('id'), bid=bb, ask=ba,
             bid_size=bid[0][1] if bid else None, ask_size=ask[0][1] if ask else None)
    for i in range(1, 3):
        r[f'bid{i + 1}'] = f'{bid[i][0]}:{bid[i][1]}' if len(bid) > i else None
        r[f'ask{i + 1}'] = f'{ask[i][0]}:{ask[i][1]}' if len(ask) > i else None
    if mid is not None:
        spread_premi = (float(meta.get('premi_spread') or 0) / 100) or 0.03
        for nome, ampiezza in (('2c', 0.02), ('premi', spread_premi)):
            r[f'prof_bid_{nome}'] = round(sum(s for p, s in bid if p >= mid - ampiezza), 2)
            r[f'prof_ask_{nome}'] = round(sum(s for p, s in ask if p <= mid + ampiezza), 2)
    return r


def main():
    adesso = datetime.now(timezone.utc)
    if adesso > FINE_TEST:
        print('Test 1 concluso il 6/11/2026: niente da fare.')
        return 0
    inizio = time.time()
    nome = adesso.strftime('%Y-%m-%d_%H%M')
    cartella = USCITA / str(adesso.year)
    cartella.mkdir(parents=True, exist_ok=True)
    libri, scambi, mercati_tutti = [], [], []
    ultimo_hash, visti_scambi, numeri = {}, set(), {}
    mercati, aggiornato = None, 0
    giro = 0
    while time.time() - inizio < DURATA and datetime.now(timezone.utc) < FINE_TEST:
        t_giro = time.time()
        ora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        if mercati is None or time.time() - aggiornato > 3600:
            try:
                nuovi = scegli_mercati(datetime.now(timezone.utc))
                if not nuovi.empty:
                    mercati = nuovi
                    aggiornato = time.time()
                    mercati_tutti.append(mercati)
                    print(f'{ora} mercati: {len(mercati)} ({(mercati.tipo == "meteo").sum()} meteo, '
                          f'{(mercati.tipo == "macro").sum()} macro)', flush=True)
            except Exception as e:
                print(f'{ora} elenco mercati non aggiornato: {e}', flush=True)
        if mercati is None or mercati.empty:
            time.sleep(PASSO)
            continue
        for t in mercati.token_si:
            numeri.setdefault(t, len(numeri))           # numero breve e stabile per token, scritto nel file dei mercati
        mercati['id'] = mercati.token_si.map(numeri)
        meta = mercati.set_index('token_si').to_dict('index')
        token = list(meta)
        cambiati = 0
        for i in range(0, len(token), 50):
            try:
                risposta = gj(f'{C}/books', 'POST', [{'token_id': t} for t in token[i:i + 50]])
            except Exception as e:
                print(f'{ora} libri non letti ({e})', flush=True)
                continue
            for b in risposta or []:
                t = b.get('asset_id')
                if t in meta and b.get('hash') != ultimo_hash.get(t):
                    ultimo_hash[t] = b.get('hash')
                    libri.append(riga_libro(b, meta[t], ora))
                    cambiati += 1
        condizioni = list(dict.fromkeys(mercati.condizione.dropna()))
        nuovi_scambi = 0
        for i in range(0, len(condizioni), 20):
            try:
                tr = gj(f'{D}/trades?market={",".join(condizioni[i:i + 20])}&limit=500&takerOnly=true')
            except Exception:
                continue
            for x in tr or []:
                k = (x.get('transactionHash'), x.get('asset'), x.get('side'), x.get('size'), x.get('price'))
                if k in visti_scambi:
                    continue
                visti_scambi.add(k)
                scambi.append(dict(ora_lettura=ora, ts=x.get('timestamp'), condizione=x.get('conditionId'),
                                   token=x.get('asset'), lato=x.get('side'), prezzo=x.get('price'), size=x.get('size'),
                                   esito=x.get('outcome'), wallet=x.get('proxyWallet'), tx=x.get('transactionHash')))
                nuovi_scambi += 1
            time.sleep(0.2)
        giro += 1
        if giro % 6 == 1:
            print(f'{ora} giro {giro}: libri cambiati {cambiati}/{len(token)}, scambi nuovi {nuovi_scambi}', flush=True)
        if giro % 6 == 0:
            salva(cartella, nome, libri, scambi, mercati_tutti)
        time.sleep(max(5, PASSO - (time.time() - t_giro)))
    salva(cartella, nome, libri, scambi, mercati_tutti)
    print(f'fine: {giro} giri, {len(libri)} righe di libri, {len(scambi)} scambi', flush=True)
    return 0


def salva(cartella, nome, libri, scambi, mercati_tutti):
    if libri:
        pd.DataFrame(libri).to_csv(cartella / f'{nome}_libri.csv.gz', index=False, compression='gzip')
    if scambi:
        pd.DataFrame(scambi).to_csv(cartella / f'{nome}_scambi.csv.gz', index=False, compression='gzip')
    if mercati_tutti:
        pd.concat(mercati_tutti).drop_duplicates(['token_si', 'premi_min', 'premi_spread', 'premi_giorno', 'volume']).to_csv(cartella / f'{nome}_mercati.csv.gz', index=False, compression='gzip')


if __name__ == '__main__':
    if '--prova' in sys.argv:          # giro breve per collaudare: 3 fotografie a 60 secondi, uscita in analisi/
        DURATA, PASSO = 150, 60
        USCITA = Path(__file__).resolve().parent / 'prova_libri'
    sys.exit(main())
