"""Archivio quotidiano del progetto "copia i vincenti" (trading personale di Antonio, solo ricerca).

Ogni giorno salva, senza interpretare nulla, i dati che domani non si possono più ricostruire:

  1. ApeWisdom: menzioni dei titoli su Reddit (tutte le pagine)                     -> dati/apewisdom/
  2. Cboe: catene di opzioni dei titoli scelti con le regole fissate nel README       -> dati/cboe/
     (solo nei giorni feriali; riassunto per scadenza, non contratto per contratto)
  3. Polymarket: classifiche dei trader e P&L complessivo di un pannello fisso di wallet -> dati/polymarket/
  4. Hyperliquid: classifica, vault, posizioni e fill delle ultime 26 ore dei migliori  -> dati/hyperliquid/

Nessun segreto, nessun ordine, nessun segnale operativo: è solo un registro per i test futuri.
Ogni fonte è indipendente: se una fallisce le altre vanno avanti, e l'esito finisce in STATO.md.

Uso:
  python raccolta.py              giro completo
  python raccolta.py --riserva    giro di riserva: parte solo se oggi il giro non è ancora riuscito
  python raccolta.py --solo cboe  una fonte sola (apewisdom, cboe, polymarket, hyperliquid), per le prove
"""
import argparse
import datetime as dt
import json
import random
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

RADICE = Path(__file__).resolve().parent
DATI = RADICE / 'dati'
STATO = RADICE / 'stato'
ADESSO = dt.datetime.now(dt.timezone.utc)
OGGI = ADESSO.date()                                   # data UTC del giro (alle 21:40 UTC è ancora la seduta di New York)
FERIALE = OGGI.weekday() < 5

S = requests.Session()
S.headers['User-Agent'] = 'archivio-vincenti/1.0 (ricerca personale; github.com/ares93-spec/archivio-vincenti)'
NOTE = []                                              # (fonte, esito ok/errore, testo) per STATO.md


# ---------------------------------------------------------------------------------------
# utilità
# ---------------------------------------------------------------------------------------
def scarica(url, metodo='GET', corpo=None, tentativi=3, attesa=60):
    """JSON da un URL, con pochi tentativi e pausa crescente sui rifiuti (429) e sugli errori."""
    ultimo = None
    for i in range(tentativi):
        try:
            if metodo == 'POST':
                r = S.post(url, json=corpo, timeout=attesa)
            else:
                r = S.get(url, timeout=attesa)
            if r.status_code == 429:
                ultimo = RuntimeError(f'429 troppe richieste ({url[:80]})')
                time.sleep(15 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:                         # rete, HTTP, JSON non valido
            ultimo = e
            time.sleep(3 * (i + 1))
    raise ultimo


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def salva(df, fonte, nome, decimali=None):
    """dati/<fonte>/<anno>/<data>_<nome>.csv.gz. Un secondo giro nello stesso giorno sovrascrive il primo.
    decimali: {colonna: cifre} per arrotondare i campi che non servono a piena precisione (pesano sul file)."""
    if decimali:
        df = df.copy()
        for c, n in decimali.items():
            if c in df:
                df[c] = pd.to_numeric(df[c], errors='coerce').round(n)
    cartella = DATI / fonte / str(OGGI.year)
    cartella.mkdir(parents=True, exist_ok=True)
    percorso = cartella / f'{OGGI.isoformat()}_{nome}.csv.gz'
    df.to_csv(percorso, index=False, compression='gzip')
    return percorso


def leggi_json(nome, vuoto):
    p = STATO / nome
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return vuoto


def scrivi_json(nome, dati):
    STATO.mkdir(exist_ok=True)
    (STATO / nome).write_text(json.dumps(dati, indent=1, sort_keys=True))


def kb(p):
    return f'{p.stat().st_size / 1024:,.0f} KB'.replace(',', '.')


# ---------------------------------------------------------------------------------------
# 1. ApeWisdom
# ---------------------------------------------------------------------------------------
def apewisdom():
    righe = []
    for filtro in ('all-stocks', 'wallstreetbets'):
        pagina, pagine = 1, 1
        while pagina <= min(pagine, 20):
            j = scarica(f'https://apewisdom.io/api/v1.0/filter/{filtro}/page/{pagina}')
            pagine = int(j.get('pages') or 1)
            for r in j.get('results', []):
                r = dict(r)
                r['filtro'] = filtro
                righe.append(r)
            pagina += 1
            time.sleep(1)
    df = pd.DataFrame(righe)
    df.insert(0, 'ora_utc', ADESSO.strftime('%Y-%m-%d %H:%M'))
    p = salva(df, 'apewisdom', 'menzioni')
    NOTE.append(('ApeWisdom', True, f'{len(df)} righe ({(df.filtro == "all-stocks").sum()} titoli in all-stocks), {kb(p)}'))
    return df


# ---------------------------------------------------------------------------------------
# 2. Selezione dei titoli per la Cboe: regole fissate il 9/10/2026, prima di vedere i dati (README, sezione 3)
# ---------------------------------------------------------------------------------------
ESCLUSI = {'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'TQQQ', 'SQQQ', 'SPX', 'XSP', 'VIX', 'UVXY', 'SOXL', 'SOXS',
           'TLT', 'GLD', 'SLV', 'ARKK', 'SPXL', 'SPXS', 'TNA', 'TZA', 'USO'}   # indici ed ETF: sono il mercato, non la folla
# sigle che su Reddit sono quasi sempre parole o gergo, non il titolo (aggiunte il 9/10/2026, prima di qualsiasi analisi)
AMBIGUI = {'IT', 'DTE', 'API', 'CAN', 'ATR', 'ARR', 'WTI', 'DD', 'CEO', 'AI', 'ON', 'ALL', 'ARE', 'NOW', 'OR', 'SO', 'BE',
           'GO', 'YOLO', 'EPS', 'PE', 'ATH', 'IMO', 'ANY', 'KEY', 'BIG', 'HAS', 'TV', 'USA', 'IPO', 'ETF', 'GDP', 'CPI',
           'FED', 'FOR', 'OP', 'EV', 'RSI', 'ATM', 'OTM', 'ITM', 'IV', 'PM', 'AM', 'UK', 'EU', 'CASH', 'LOVE', 'FUN',
           'REAL', 'BEST', 'NEXT', 'OPEN', 'TECH', 'MAIN', 'HUGE', 'TRUE', 'PLAY', 'SAFE', 'RUN', 'LOW', 'NEW', 'ONE'}
PICCO_MENZIONI = 20          # menzioni minime nelle 24 ore per parlare di picco
PICCO_MULTIPLO = 3           # menzioni almeno triplicate rispetto a 24 ore prima
FOLLA = 25                   # i 25 titoli più citati
CONTROLLO = 15               # gruppo di controllo estratto a caso tra i rank 26-500 senza picco
GIORNI_SEGUITI = 35          # ogni titolo scelto viene registrato per 35 giorni di calendario
MASSIMO_SEGUITI = 260        # tetto per tenere il giro sotto i 15 minuti


def selezione(ape):
    a = ape[ape.filtro == 'all-stocks'].copy()
    a['ticker'] = a.ticker.astype(str).str.upper().str.strip()
    a = a[a.ticker.str.fullmatch(r'[A-Z][A-Z.]{0,5}') & ~a.ticker.isin(ESCLUSI | AMBIGUI)]
    a['menzioni'] = pd.to_numeric(a.mentions, errors='coerce').fillna(0)
    a['menzioni_24h'] = pd.to_numeric(a.mentions_24h_ago, errors='coerce').fillna(0)
    a['posto'] = pd.to_numeric(a['rank'], errors='coerce')
    a = a.drop_duplicates('ticker').sort_values('posto')
    picco = set(a[(a.menzioni >= PICCO_MENZIONI) & (a.menzioni >= PICCO_MULTIPLO * a.menzioni_24h.clip(lower=1))].ticker)
    folla = set(a.head(FOLLA).ticker)
    resto = a[(a.posto > FOLLA) & (a.posto <= 500) & (a.menzioni >= 3) & ~a.ticker.isin(picco | folla)]
    controllo = set(resto.sample(n=min(CONTROLLO, len(resto)), random_state=int(OGGI.strftime('%Y%m%d'))).ticker)
    oggi = {}
    for tk in picco | folla | controllo:
        oggi[tk] = '+'.join(g for g, s in (('picco', picco), ('folla', folla), ('controllo', controllo)) if tk in s)
    return oggi


def aggiorna_seguiti(scelti):
    """stato/seguiti.json: per ogni titolo, prima e ultima data di scelta e gruppi. Restano quelli scelti negli ultimi 35 giorni."""
    seguiti = leggi_json('seguiti.json', {})
    for tk, gruppo in scelti.items():
        s = seguiti.setdefault(tk, {'primo': OGGI.isoformat(), 'gruppi': []})
        s['ultimo'] = OGGI.isoformat()
        if gruppo not in s['gruppi']:
            s['gruppi'].append(gruppo)
    limite = (OGGI - dt.timedelta(days=GIORNI_SEGUITI)).isoformat()
    seguiti = {tk: s for tk, s in seguiti.items() if s['ultimo'] >= limite}
    scrivi_json('seguiti.json', seguiti)
    # tetto: prima quelli scelti oggi, poi i più recenti
    ordine = sorted(seguiti, key=lambda tk: (0 if tk in scelti else 1, -int(seguiti[tk]['ultimo'].replace('-', ''))))
    return ordine[:MASSIMO_SEGUITI], seguiti


# ---------------------------------------------------------------------------------------
# 3. Cboe: catena ritardata di 15 minuti, riassunta per scadenza
# ---------------------------------------------------------------------------------------
RX_OPZ = re.compile(r'(\d{2})(\d{2})(\d{2})([CP])(\d{8})$')


def riassunto_cboe(tk):
    j = scarica(f'https://cdn.cboe.com/api/global/delayed_quotes/options/{tk}.json', tentativi=2, attesa=90)
    d = j.get('data') or {}
    base = {k: v for k, v in d.items() if not isinstance(v, (list, dict))}
    base['ticker'] = tk
    base['timestamp_cboe'] = j.get('timestamp')
    spot = num(d.get('current_price')) or num(d.get('close')) or num(d.get('prev_day_close'))
    o = pd.DataFrame(d.get('options') or [])
    scadenze = []
    if o.empty or not spot:
        base['contratti'] = 0
        return base, scadenze
    m = o.option.astype(str).str.extract(RX_OPZ)
    o['scadenza'] = pd.to_datetime('20' + m[0] + '-' + m[1] + '-' + m[2], errors='coerce')
    o['tipo'] = m[3]
    o['strike'] = pd.to_numeric(m[4], errors='coerce') / 1000
    for c in ('bid', 'ask', 'iv', 'open_interest', 'volume', 'delta'):
        o[c] = pd.to_numeric(o.get(c), errors='coerce')
    o = o.dropna(subset=['scadenza', 'strike'])
    o['gg'] = (o.scadenza - pd.Timestamp(OGGI)).dt.days
    o['mid'] = ((o.bid + o.ask) / 2).where((o.bid > 0) & (o.ask > 0))
    base['contratti'] = len(o)
    base['volume_call'] = float(o.loc[o.tipo == 'C', 'volume'].sum())
    base['volume_put'] = float(o.loc[o.tipo == 'P', 'volume'].sum())
    base['oi_call'] = float(o.loc[o.tipo == 'C', 'open_interest'].sum())
    base['oi_put'] = float(o.loc[o.tipo == 'P', 'open_interest'].sum())
    for sc, g in o[(o.gg >= 0) & (o.gg <= 70)].groupby('scadenza'):
        c, p = g[g.tipo == 'C'], g[g.tipo == 'P']
        r = dict(ticker=tk, scadenza=sc.date().isoformat(), gg=int(g.gg.iloc[0]), spot=spot,
                 volume_call=float(c.volume.sum()), volume_put=float(p.volume.sum()),
                 oi_call=float(c.open_interest.sum()), oi_put=float(p.open_interest.sum()))
        comuni = sorted(set(c.strike) & set(p.strike), key=lambda k: abs(k - spot))
        if comuni:
            k = comuni[0]
            cc, pp = c[c.strike == k].iloc[0], p[p.strike == k].iloc[0]
            r.update(strike_atm=k, iv_atm=pd.Series([cc.iv, pp.iv]).mean(),
                     straddle=(cc.mid + pp.mid) if pd.notna(cc.mid) and pd.notna(pp.mid) else None)
            r['mossa_implicita'] = r['straddle'] / spot if r['straddle'] else None
            spr = [(x.ask - x.bid) / x.mid for x in (cc, pp) if pd.notna(x.mid) and x.mid > 0]
            r['spread_atm'] = sum(spr) / len(spr) if spr else None
        for tipo, bersaglio, nome in (('P', -0.25, 'iv_put25'), ('C', 0.25, 'iv_call25')):
            g2 = g[(g.tipo == tipo) & g.delta.notna() & (g.iv > 0)]
            if not g2.empty:
                r[nome] = float(g2.loc[(g2.delta - bersaglio).abs().idxmin(), 'iv'])
        scadenze.append(r)
    return base, scadenze


def cboe(ape):
    if not FERIALE:
        NOTE.append(('Cboe', True, 'saltata: oggi la borsa americana è chiusa'))
        return
    scelti = selezione(ape)
    lista, seguiti = aggiorna_seguiti(scelti)
    basi, scad, errori = [], [], []
    for tk in lista:
        try:
            b, s = riassunto_cboe(tk)
            b['gruppo_oggi'] = scelti.get(tk, '')
            b['gruppi'] = '|'.join(seguiti[tk]['gruppi'])
            b['primo_giorno'] = seguiti[tk]['primo']
            basi.append(b)
            scad.extend(s)
        except Exception as e:
            errori.append(f'{tk}: {str(e)[:60]}')
        time.sleep(0.4)
    gruppi = pd.Series(list(scelti.values()))
    if basi:
        p1 = salva(pd.DataFrame(basi), 'cboe', 'sottostanti')
        p2 = salva(pd.DataFrame(scad), 'cboe', 'scadenze')
        dim = f'{kb(p1)} + {kb(p2)}'
    else:
        dim = 'nessun file'
    testo = (f'scelti oggi {len(scelti)} (picco {gruppi.str.contains("picco").sum()}, folla {gruppi.str.contains("folla").sum()}, '
             f'controllo {gruppi.str.contains("controllo").sum()}); seguiti {len(lista)}; letti {len(basi)}, '
             f'senza catena {len(errori)}; {dim}')
    NOTE.append(('Cboe', len(basi) > 0, testo))
    if errori:
        (STATO / 'cboe_errori.txt').write_text('\n'.join(errori))


# ---------------------------------------------------------------------------------------
# 4. Polymarket: classifiche e pannello fisso di wallet
# ---------------------------------------------------------------------------------------
PM = 'https://data-api.polymarket.com/v1/leaderboard'
PM_CATEGORIE = ('POLITICS', 'SPORTS', 'CRYPTO', 'WEATHER', 'ECONOMICS', 'FINANCE', 'TECH', 'CULTURE')
PM_PANNELLO_MAX = 2500       # wallet seguiti ogni giorno, anche quando perdono
PM_TEMPO_PANNELLO = 9 * 60   # secondi al massimo per il pannello


def pm_classifica(categoria, periodo, quanti, ordine='PNL'):
    righe, visti, offset = [], set(), 0
    while offset < quanti:
        j = scarica(f'{PM}?category={categoria}&timePeriod={periodo}&orderBy={ordine}&limit=50&offset={offset}')
        if not isinstance(j, list) or not j:
            break
        nuovi = 0
        for r in j:
            w = r.get('proxyWallet')
            if w in visti:
                continue
            visti.add(w)
            nuovi += 1
            righe.append(dict(categoria=categoria, periodo=periodo, ordine=ordine, rank=r.get('rank'), wallet=w,
                              utente=r.get('userName'), x=r.get('xUsername'), volume=r.get('vol'), pnl=r.get('pnl'),
                              verificato=r.get('verifiedBadge')))
        if nuovi == 0 or offset + len(j) > 1000:
            break
        offset += len(j)
        time.sleep(0.3)
    return righe


def polymarket():
    righe = []
    giri = [('OVERALL', p, 1000, 'PNL') for p in ('DAY', 'WEEK', 'MONTH', 'ALL')]
    giri += [('OVERALL', 'MONTH', 500, 'VOL')]
    giri += [(c, 'MONTH', 200, 'PNL') for c in PM_CATEGORIE]
    for g in giri:
        try:
            righe.extend(pm_classifica(*g))
        except Exception as e:
            NOTE.append(('Polymarket', False, f'classifica {g[0]}/{g[1]}/{g[3]}: {str(e)[:80]}'))
    df = pd.DataFrame(righe)
    if df.empty:
        NOTE.append(('Polymarket', False, 'nessuna classifica letta'))
        return
    p = salva(df, 'polymarket', 'classifiche', {'volume': 0, 'pnl': 0})
    # le categorie sono davvero diverse dalla classifica generale? (il filtro risultava ignorato nei test del 9/10)
    gen = set(df[(df.categoria == 'OVERALL') & (df.periodo == 'MONTH') & (df.ordine == 'PNL')].wallet.head(200))
    uguali = sum(set(df[df.categoria == c].wallet) == gen for c in PM_CATEGORIE if (df.categoria == c).any())
    NOTE.append(('Polymarket', True, f'classifiche: {len(df)} righe, {df.wallet.nunique()} wallet, {kb(p)}'
                 + (f'; ATTENZIONE: {uguali} categorie identiche alla generale' if uguali else '')))

    # pannello: chiunque sia entrato nelle classifiche mensili o storiche, seguito ogni giorno con il P&L complessivo
    pannello = leggi_json('polymarket_pannello.json', {})
    candidati = df[(df.periodo.isin(['MONTH', 'ALL'])) & (df.ordine == 'PNL')].sort_values('pnl', ascending=False).wallet
    for w in candidati:
        if w and w not in pannello and len(pannello) < PM_PANNELLO_MAX:
            pannello[w] = OGGI.isoformat()
    scrivi_json('polymarket_pannello.json', pannello)
    inizio, letti, vuoti, quote = time.time(), [], 0, []

    def leggi(w):
        if time.time() - inizio > PM_TEMPO_PANNELLO:
            return w, 'tempo'
        try:
            j = scarica(f'{PM}?timePeriod=ALL&orderBy=PNL&user={w}', tentativi=3, attesa=30)
            return w, (j[0] if isinstance(j, list) and j else None)
        except Exception:
            return w, None

    with ThreadPoolExecutor(max_workers=4) as ex:      # 4 richieste alla volta: tutto il pannello in pochi minuti
        for w, r in ex.map(leggi, list(pannello)):
            if isinstance(r, dict):
                letti.append(dict(wallet=w, dal=pannello[w], rank_all=r.get('rank'), volume_all=r.get('vol'), pnl_all=r.get('pnl')))
            else:
                vuoti += 1
    if letti:
        p2 = salva(pd.DataFrame(letti), 'polymarket', 'pannello', {'volume_all': 0, 'pnl_all': 2})
        quote = kb(p2)
    NOTE.append(('Polymarket', bool(letti), f'pannello: {len(letti)} wallet letti su {len(pannello)}, {vuoti} senza risposta'
                 + (f', {quote}' if quote else '')))


# ---------------------------------------------------------------------------------------
# 5. Hyperliquid: classifica, vault, posizioni e fill dei migliori
# ---------------------------------------------------------------------------------------
HL_INFO = 'https://api.hyperliquid.xyz/info'
HL_STATS = 'https://stats-data.hyperliquid.xyz/Mainnet'
HL_PANNELLO_MAX = 250


def hyperliquid():
    # classifica completa (file pubblico), salvata solo per i conti rilevanti
    lb = scarica(f'{HL_STATS}/leaderboard', attesa=240)
    righe = lb.get('leaderboardRows', []) if isinstance(lb, dict) else (lb or [])
    tab = []
    for r in righe:
        wp = {k: v for k, v in (r.get('windowPerformances') or [])}
        rec = dict(wallet=r.get('ethAddress'), nome=r.get('displayName'), valore_conto=num(r.get('accountValue')))
        for w in ('day', 'week', 'month', 'allTime'):
            p = wp.get(w) or {}
            rec[f'pnl_{w}'], rec[f'roi_{w}'], rec[f'vlm_{w}'] = num(p.get('pnl')), num(p.get('roi')), num(p.get('vlm'))
        tab.append(rec)
    df = pd.DataFrame(tab)
    if df.empty:
        raise RuntimeError(f'classifica vuota (chiavi: {list(lb)[:5] if isinstance(lb, dict) else type(lb)})')
    for c in ('valore_conto', 'pnl_month', 'pnl_allTime', 'vlm_month'):
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    rilevanti = df[(df.valore_conto >= 100_000) | (df.pnl_month.abs() >= 50_000) | (df.pnl_allTime.abs() >= 500_000)]
    rilevanti = rilevanti.drop(columns=['roi_day', 'roi_week', 'vlm_day', 'vlm_week'])
    soldi = {c: 0 for c in rilevanti.columns if c.startswith(('pnl_', 'vlm_')) or c == 'valore_conto'}
    p = salva(rilevanti, 'hyperliquid', 'classifica', {**soldi, 'roi_month': 4, 'roi_allTime': 4})
    NOTE.append(('Hyperliquid', True, f'classifica: {len(df)} conti, salvati {len(rilevanti)} rilevanti, {kb(p)}'))

    # vault: tutti, chiusi compresi (serve contro il bias di sopravvivenza)
    vt = []
    try:
        vault = scarica(f'{HL_STATS}/vaults', attesa=240)
        for v in vault:
            s = v.get('summary') or {}
            rec = dict(vault=s.get('vaultAddress'), nome=s.get('name'), leader=s.get('leader'), tvl=num(s.get('tvl')),
                       chiuso=s.get('isClosed'), creato=s.get('createTimeMillis'), apr=num(v.get('apr')),
                       tipo=(s.get('relationship') or {}).get('type'))
            for periodo, serie in (v.get('pnls') or []):
                rec[f'pnl_{periodo}'] = num(serie[-1]) if serie else None
            vt.append(rec)
        vdf = pd.DataFrame(vt)
        chiusi = vdf.chiuso.fillna(False).astype(bool)
        # i vault chiusi non cambiano più: tutti il lunedì, negli altri giorni solo gli aperti con almeno 100 $
        da_salvare = vdf if OGGI.weekday() == 0 else vdf[~chiusi & (vdf.tvl.fillna(0) >= 100)]
        soldi = {c: 0 for c in vdf.columns if c.startswith('pnl_') or c == 'tvl'}
        p = salva(da_salvare, 'hyperliquid', 'vault', {**soldi, 'apr': 4})
        NOTE.append(('Hyperliquid', True, f'vault: {len(vdf)} ({int(chiusi.sum())} chiusi), salvati {len(da_salvare)}, {kb(p)}'))
    except Exception as e:
        vdf = pd.DataFrame()
        NOTE.append(('Hyperliquid', False, f'vault: {str(e)[:80]}'))

    # pannello di oggi: migliori del mese con conto vero, migliori di sempre, leader dei vault più grandi
    base = df[(df.valore_conto >= 100_000) & (df.vlm_month > 0)]
    pannello = list(base.nlargest(150, 'pnl_month').wallet) + list(base.nlargest(50, 'pnl_allTime').wallet)
    if not vdf.empty:
        aperti = vdf[~vdf.chiuso.fillna(False).astype(bool)].nlargest(30, 'tvl')
        pannello += list(aperti.leader)
    pannello = list(dict.fromkeys(w for w in pannello if isinstance(w, str)))[:HL_PANNELLO_MAX]

    posizioni, fill, troppi, errori = [], [], 0, 0
    inizio_fill = int((ADESSO - dt.timedelta(hours=26)).timestamp() * 1000)
    for w in pannello:
        try:
            st = scarica(HL_INFO, 'POST', {'type': 'clearinghouseState', 'user': w}, tentativi=2, attesa=30)
            conto = num((st.get('marginSummary') or {}).get('accountValue'))
            for ap in st.get('assetPositions') or []:
                ps = ap.get('position') or {}
                posizioni.append(dict(wallet=w, conto=conto, coin=ps.get('coin'), size=num(ps.get('szi')),
                                      prezzo_medio=num(ps.get('entryPx')), valore=num(ps.get('positionValue')),
                                      pnl_aperto=num(ps.get('unrealizedPnl')), leva=(ps.get('leverage') or {}).get('value'),
                                      liquidazione=num(ps.get('liquidationPx'))))
            fl = scarica(HL_INFO, 'POST', {'type': 'userFillsByTime', 'user': w, 'startTime': inizio_fill,
                                           'aggregateByTime': True}, tentativi=2, attesa=60)
            if len(fl) >= 2000:
                troppi += 1                        # operatore ad alta frequenza: non è il profilo che ci interessa
                fl = []
            for f in fl:
                fill.append(dict(wallet=w, ora=f.get('time'), coin=f.get('coin'), lato=f.get('side'), dir=f.get('dir'),
                                 prezzo=num(f.get('px')), size=num(f.get('sz')), pnl_chiuso=num(f.get('closedPnl')),
                                 commissione=num(f.get('fee')), crossed=f.get('crossed'), tid=f.get('tid')))
        except Exception:
            errori += 1
        time.sleep(1.3)                            # 1.200 di peso al minuto: circa 22 a wallet + i fill restituiti
    testo = f'pannello: {len(pannello)} wallet, {len(posizioni)} posizioni aperte, {len(fill)} fill, {troppi} ad alta frequenza esclusi, {errori} errori'
    if posizioni:
        testo += f', {kb(salva(pd.DataFrame(posizioni), "hyperliquid", "posizioni"))}'
    if fill:
        testo += f' + {kb(salva(pd.DataFrame(fill), "hyperliquid", "fill"))}'
    NOTE.append(('Hyperliquid', errori < len(pannello) / 2, testo))


# ---------------------------------------------------------------------------------------
# STATO.md: il riepilogo da leggere dal telefono
# ---------------------------------------------------------------------------------------
def dimensione(cartella):
    return sum(f.stat().st_size for f in cartella.rglob('*') if f.is_file()) if cartella.exists() else 0


def scrivi_stato(durata):
    ora_it = ADESSO.astimezone(ZoneInfo('Europe/Rome'))
    righe = [f'# Stato dell\'archivio', '',
             f'Ultimo giro: **{ora_it:%d/%m/%Y %H:%M}** ora italiana ({durata / 60:.1f} minuti).', '',
             '| Fonte | Esito | Dettaglio |', '|---|---|---|']
    for fonte, ok, testo in NOTE:
        righe.append(f'| {fonte} | {"✅" if ok else "❌"} | {testo} |')
    tot = dimensione(DATI) / 1024 / 1024
    righe += ['', f'Archivio: **{tot:.1f} MB** in totale.'.replace('.', ',', 1), '']
    if tot > 700:
        righe += ['⚠️ **Oltre 700 MB**: GitHub consiglia di restare sotto 1 GB. Va deciso cosa sfoltire.', '']
    giorni = sorted({p.name[:10] for p in DATI.rglob('*.csv.gz')}) if DATI.exists() else []
    if giorni:
        righe.append(f'Giorni registrati: **{len(giorni)}**, dal {giorni[0]} al {giorni[-1]}.')
    righe += ['', 'Calendario delle analisi e regole: vedi [README.md](README.md).', '']
    (RADICE / 'STATO.md').write_text('\n'.join(righe))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--riserva', action='store_true')
    ap.add_argument('--solo', choices=['apewisdom', 'cboe', 'polymarket', 'hyperliquid'])
    a = ap.parse_args()
    STATO.mkdir(exist_ok=True)
    fatto = STATO / 'ultimo_giro.txt'
    if a.riserva and fatto.exists() and fatto.read_text().strip() == OGGI.isoformat():
        print('Giro di oggi già riuscito: la riserva non parte.')
        return 0
    inizio = time.time()
    ape = None
    fonti = ['apewisdom', 'cboe', 'polymarket', 'hyperliquid'] if not a.solo else [a.solo]
    if 'cboe' in fonti and 'apewisdom' not in fonti:
        fonti = ['apewisdom'] + fonti
    for f in fonti:
        print(f'--- {f}', flush=True)
        try:
            if f == 'apewisdom':
                ape = apewisdom()
            elif f == 'cboe':
                if ape is None:
                    raise RuntimeError('mancano le menzioni di ApeWisdom')
                cboe(ape)
            elif f == 'polymarket':
                polymarket()
            elif f == 'hyperliquid':
                hyperliquid()
        except Exception as e:
            traceback.print_exc()
            NOTE.append(({'apewisdom': 'ApeWisdom', 'cboe': 'Cboe', 'polymarket': 'Polymarket',
                          'hyperliquid': 'Hyperliquid'}[f], False, f'errore: {str(e)[:120]}'))
    durata = time.time() - inizio
    scrivi_stato(durata)
    for n in NOTE:
        print(n)
    riusciti = sum(1 for _, ok, _ in NOTE if ok)
    if riusciti and not a.solo:
        fatto.write_text(OGGI.isoformat())
    return 0 if riusciti else 1


if __name__ == '__main__':
    sys.exit(main())
