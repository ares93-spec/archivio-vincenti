"""Test 1 (regole in regole.md, fissate il 9/10/2026): misure sui libri ordini registrati dal 9/10 al 6/11/2026.

Legge dati_test/libri/2026/ (scritti da libri.py) e scrive risultati_test1.txt.

Come si ricostruisce la fotografia: libri.py salva una riga solo quando il libro di un esito è cambiato (hash). Dentro
ogni giro di 5 ore e 40 minuti l'istante di ogni fotografia è un valore di 'ora' (o di 'ora_lettura' negli scambi);
lo stato di un esito a quell'istante è la sua ultima riga, a partire dalla prima riga dell'esito nel giro e fino
all'ultima (dopo l'ultima riga non si sa se l'esito era ancora seguito, quindi non si conta). Gli 'id' valgono solo
dentro il proprio giro e si traducono in token con il file _mercati dello stesso giro.

Scelte di presentazione fissate prima di calcolare: distanza dalla scadenza = fine_evento (endDate di Gamma) meno
istante della fotografia, in fasce <0 ore, 0-6, 6-24, 24-48 ore, 2-7, 7-45 giorni; "esiti multipli" = eventi con almeno
3 esiti, e una fotografia conta solo se c'è il libro di tutti gli esiti dell'evento (tutti i token visti per
quell'evento nei file _mercati); somma delle lettere con un esito senza lettera = non eseguibile; somma dei denari con
un esito senza denaro = quell'esito vale 0.
"""
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
DATI = QUI.parents[1] / 'dati_test' / 'libri' / '2026'
INIZIO_T, FINE_T = pd.Timestamp('2026-10-09 00:00'), pd.Timestamp('2026-11-06 23:59:59')
FASCE_H = [-1e9, 0, 6, 24, 48, 168, 1080]
NOMI_H = ['scaduto (<0 h)', '0-6 h', '6-24 h', '24-48 h', '2-7 g', '7-45 g']
RIGHE = []


def log(t=''):
    print(t, flush=True)
    RIGHE.append(str(t))


def carica():
    pannelli, scambi, giri, mercati_tutti = [], [], [], []
    for f in sorted(glob.glob(str(DATI / '*_libri.csv.gz'))):
        nome = Path(f).name[:15]
        lib = pd.read_csv(f)
        mer = pd.read_csv(DATI / f'{nome}_mercati.csv.gz', dtype={'token_si': str, 'condizione': str, 'evento_id': str})
        fs = DATI / f'{nome}_scambi.csv.gz'
        sc = pd.read_csv(fs, dtype={'token': str, 'condizione': str}) if fs.exists() else pd.DataFrame()
        lib['ora'] = pd.to_datetime(lib.ora)
        istanti = set(lib.ora)
        if not sc.empty:
            istanti |= set(pd.to_datetime(sc.ora_lettura))
            sc['giro'] = nome
            scambi.append(sc)
        istanti = pd.DatetimeIndex(sorted(istanti))
        giri.append(pd.DataFrame({'giro': nome, 'ora': istanti}))
        # metadati per id del giro: premi come media dei valori registrati nel giro
        m = mer.groupby('id').agg(token=('token_si', 'first'), tipo=('tipo', 'first'), evento_id=('evento_id', 'first'),
                                  evento=('evento', 'first'), fine=('fine_evento', 'first'), condizione=('condizione', 'first'),
                                  premi_giorno=('premi_giorno', 'mean'), premi_spread=('premi_spread', 'mean'),
                                  premi_min=('premi_min', 'mean')).reset_index()
        mer['giro'] = nome
        mercati_tutti.append(mer)
        # griglia esito x istante fra prima e ultima riga dell'esito nel giro
        lim = lib.groupby('id').ora.agg(['min', 'max'])
        g = pd.DataFrame({'ora': istanti}).merge(lim.reset_index(), how='cross')
        g = g[(g.ora >= g['min']) & (g.ora <= g['max'])][['id', 'ora']].sort_values('ora')
        p = pd.merge_asof(g, lib.sort_values('ora'), on='ora', by='id', direction='backward')
        p = p.merge(m, on='id', how='left')
        p['giro'] = nome
        pannelli.append(p)
    pan = pd.concat(pannelli, ignore_index=True)
    pan['fine'] = pd.to_datetime(pan.fine, utc=True).dt.tz_localize(None)
    return pan, pd.concat(scambi, ignore_index=True), pd.concat(giri, ignore_index=True), pd.concat(mercati_tutti)


def copertura(giri):
    log('=== COPERTURA ===')
    gg = giri.groupby('giro').ora.agg(['min', 'max', 'count'])
    log(f'giri di raccolta (file): {len(gg)}; fotografie (istanti): {len(giri)}; '
        f'prima {giri.ora.min()} UTC, ultima {giri.ora.max()} UTC')
    o = giri.ora.sort_values().reset_index(drop=True)
    salti = o.diff().dt.total_seconds() / 60
    log(f'intervallo fra fotografie consecutive: mediana {salti.median():.1f} min; dentro un giro di raccolta '
        f'{giri.groupby("giro").ora.apply(lambda s: s.sort_values().diff().dt.total_seconds().median() / 60).median():.1f} min '
        f'(mediana delle mediane)')
    buchi = [(o[i - 1], o[i], salti[i]) for i in range(1, len(o)) if salti[i] > 30]
    ore_buchi = sum(b[2] for b in buchi) / 60
    tot = (o.iloc[-1] - o.iloc[0]).total_seconds() / 3600
    log(f'buchi oltre 30 minuti: {len(buchi)}, in tutto {ore_buchi:.1f} ore su {tot:.1f} ({ore_buchi / tot:.1%})')
    g_ord = giri.sort_values('ora').reset_index(drop=True)
    tra = sum(1 for i in range(1, len(o)) if salti[i] > 30 and g_ord.giro[i] != g_ord.giro[i - 1])
    dopo = sum(b[2] for b in buchi if b[0] >= pd.Timestamp('2026-10-26')) / 60
    log(f'buchi fra un giro di raccolta e il successivo: {tra} su {len(buchi)}; ore di buco dal 26/10: {dopo:.1f}')
    log(f'buco più lungo: {max(b[2] for b in buchi) / 60:.1f} ore; mediana dei buchi {np.median([b[2] for b in buchi]) / 60:.1f} ore')
    # giri con fotografie più rade di 10 minuti
    lenti = giri.groupby('giro').ora.apply(lambda s: s.sort_values().diff().dt.total_seconds().median() / 60)
    lenti = lenti[lenti > 12]
    if len(lenti):
        log(f'giri di raccolta con passo mediano oltre 12 minuti: {len(lenti)} (dal {lenti.index.min()} al '
            f'{lenti.index.max()}; passo mediano {lenti.min():.1f}-{lenti.max():.1f} min)')
    log('\nPer giorno (UTC): fotografie, ore del giorno con almeno una fotografia, ore senza')
    d = giri.assign(g=giri.ora.dt.date, h=giri.ora.dt.hour)
    tab = d.groupby('g').agg(fotografie=('ora', 'size'), ore=('h', 'nunique'))
    tab['ore_senza'] = 24 - tab.ore
    log(tab.to_string())
    log(f'giorni con fotografie: {len(tab)}; ore con almeno una fotografia: {int(tab.ore.sum())} su {24 * len(tab)}')
    log('\nOre UTC più spesso scoperte (giorni senza fotografie in quell\'ora, su ' + str(len(tab)) + '):')
    scoperte = {h: int((d.groupby('g').h.apply(lambda s: h not in set(s))).sum()) for h in range(24)}
    log('  ' + ', '.join(f'{h:02d}:{v}' for h, v in scoperte.items()))
    return buchi


def spread(pan):
    log('\n=== SPREAD (lettera - denaro dell\'esito SÌ, in centesimi, per fotografia) ===')
    p = pan.copy()
    p['ore_scad'] = (p.fine - p.ora).dt.total_seconds() / 3600
    p['dist'] = pd.cut(p.ore_scad, FASCE_H, labels=NOMI_H, right=False)
    p['due_lati'] = p.bid.notna() & p.ask.notna()
    log('fotografie esito x istante: ' + ', '.join(f'{k} {v:,}' for k, v in p.tipo.value_counts().items()))
    log('quota con entrambi i lati: ' + ', '.join(f'{k} {v:.1%}' for k, v in p.groupby('tipo').due_lati.mean().items()))
    log('quota senza denaro: ' + ', '.join(f'{k} {v:.1%}' for k, v in p.groupby('tipo').bid.apply(lambda s: s.isna().mean()).items())
        + '; senza lettera: ' + ', '.join(f'{k} {v:.1%}' for k, v in p.groupby('tipo').ask.apply(lambda s: s.isna().mean()).items()))
    q = p[p.due_lati].copy()
    q['spread'] = (q.ask - q.bid) * 100
    q['mid'] = (q.ask + q.bid) / 2
    log(f'libri incrociati o a spread nullo (lettera <= denaro): {(q.spread <= 0).sum()}')

    def tabella(x, titolo):
        t = x.groupby(['tipo', 'dist'], observed=True).spread.agg(n='size', medio='mean', mediano='median',
                                                                   p90=lambda s: s.quantile(.9))
        tt = x.groupby('tipo').spread.agg(n='size', medio='mean', mediano='median', p90=lambda s: s.quantile(.9))
        tt.index = pd.MultiIndex.from_tuples([(k, 'TUTTE') for k in tt.index])
        log(f'\n{titolo}')
        log(pd.concat([t, tt]).sort_index().round(2).to_string())

    tabella(q, 'Tutti gli esiti con entrambi i lati')
    tabella(q[(q.mid >= .05) & (q.mid <= .95)], 'Solo esiti con prezzo medio fra 5¢ e 95¢')
    tabella(q[(q.mid >= .05) & (q.mid <= .30)], 'Solo esiti con prezzo medio fra 5¢ e 30¢ (fascia dell\'ipotesi)')
    return p


def esiti_multipli(pan, mercati):
    log('\n=== SOMMA DEI SÌ NEGLI EVENTI A ESITI MULTIPLI (stessa fotografia) ===')
    insieme = mercati.groupby('evento_id').token_si.nunique()
    multi = insieme[insieme >= 3]
    tipi = mercati.groupby('evento_id').tipo.first()
    log(f'eventi con almeno 3 esiti: {len(multi)} ({", ".join(f"{k} {v}" for k, v in tipi[multi.index].value_counts().items())});'
        f' esiti per evento: mediana {multi.median():.0f}')
    p = pan[pan.evento_id.isin(multi.index)]
    agg = p.groupby(['evento_id', 'ora']).agg(n=('token', 'nunique'), tipo=('tipo', 'first'),
                                              somma_ask=('ask', 'sum'), ask_mancanti=('ask', lambda s: s.isna().sum()),
                                              somma_bid=('bid', lambda s: s.fillna(0).sum()),
                                              taglia_ask=('ask_size', 'min'), taglia_bid=('bid_size', 'min')).reset_index()
    agg['completo'] = agg.n == agg.evento_id.map(multi)
    log(f'fotografie evento x istante: {len(agg):,}; complete (libro di tutti gli esiti): {agg.completo.sum():,}')
    a = agg[agg.completo].copy()
    a['ask_ok'] = a.ask_mancanti == 0
    for tipo, g in [('TUTTI', a)] + list(a.groupby('tipo')):
        n = len(g)
        nk = g.ask_ok.sum()
        sotto = g.ask_ok & (g.somma_ask < 1 - 1e-9)
        sopra = g.somma_bid > 1 + 1e-9
        log(f'\n{tipo}: fotografie complete {n:,} (eventi {g.evento_id.nunique()}); con lettera su tutti gli esiti {nk:,}')
        log(f'  somma delle lettere < 1 $: {sotto.sum():,} ({sotto.sum() / max(nk, 1):.2%} delle fotografie con tutte le '
            f'lettere), in {g[sotto].evento_id.nunique()} eventi; con margine >= 1¢: {(g.ask_ok & (g.somma_ask <= .99 + 1e-9)).sum():,}')
        log(f'  somma dei denari > 1 $: {sopra.sum():,} ({sopra.mean():.2%}), in {g[sopra].evento_id.nunique()} eventi; '
            f'con margine >= 1¢: {(g.somma_bid >= 1.01 - 1e-9).sum():,}')
        if sotto.sum():
            m = (1 - g[sotto].somma_ask) * 100
            log(f'  quando la somma delle lettere è < 1: margine mediano {m.median():.2f}¢ (max {m.max():.2f}¢), '
                f'quantità eseguibile mediana {g[sotto].taglia_ask.median():.1f} azioni per esito (al primo livello)')
        if sopra.sum():
            m = (g[sopra].somma_bid - 1) * 100
            log(f'  quando la somma dei denari è > 1: margine mediano {m.median():.2f}¢ (max {m.max():.2f}¢), '
                f'quantità eseguibile mediana {g[sopra].taglia_bid.median():.1f} azioni (minimo fra gli esiti con denaro)')
        log(f'  somma delle lettere: mediana {g[g.ask_ok].somma_ask.median():.3f}; somma dei denari: mediana {g.somma_bid.median():.3f}')


def volume(scambi, mercati):
    log('\n=== VOLUME SCAMBIATO (Data API /trades, solo taker, senza doppioni) ===')
    s = scambi.drop_duplicates(['tx', 'token', 'lato', 'size', 'prezzo']).copy()
    s['t'] = pd.to_datetime(s.ts, unit='s')
    log(f'scambi letti {len(scambi):,}, unici {len(s):,}; dal {s.t.min()} al {s.t.max()} UTC')
    senza = sorted(set(Path(f).name[:15] for f in glob.glob(str(DATI / '*_libri.csv.gz'))) - set(scambi.giro))
    if senza:
        log(f'giri di raccolta senza file degli scambi: {len(senza)}, dal {senza[0]} al {senza[-1]}: dopo l\'ultimo scambio '
            f'registrato ({s.t.max()} UTC) la Data API non ha restituito scambi e il volume di quei giorni manca')
    log('i giri di raccolta durano 5 h 40 e partono ogni 6 ore circa: gli scambi dei buchi si recuperano solo in parte '
        '(la prima lettura di ogni giro chiede gli ultimi 500 scambi per gruppo di 20 mercati)')
    s = s[(s.t >= INIZIO_T) & (s.t <= FINE_T)]
    s['usd'] = s['size'] * s['prezzo']
    cond = mercati.drop_duplicates('condizione').set_index('condizione')[['tipo', 'evento_id']]
    s = s.join(cond, on='condizione')
    log(f'scambi nel periodo 9/10-6/11: {len(s):,}; controvalore {s.usd.sum():,.0f} $; senza mercato noto {s.tipo.isna().sum()}')
    per = s.groupby(['tipo', 'condizione']).agg(usd=('usd', 'sum'), azioni=('size', 'sum'), scambi=('usd', 'count'))
    seguiti = mercati.groupby('tipo').condizione.nunique()
    for tipo, g in per.groupby(level=0):
        log(f'\n{tipo}: mercati seguiti {seguiti[tipo]}, con almeno uno scambio {len(g)}; controvalore totale '
            f'{g.usd.sum():,.0f} $ in {int(g.scambi.sum()):,} scambi')
        q = g.usd.quantile([.1, .25, .5, .75, .9, .99])
        log(f'  controvalore per mercato: media {g.usd.mean():,.0f} $, ' +
            ', '.join(f'p{int(k * 100)} {v:,.0f} $' for k, v in q.items()) + f', max {g.usd.max():,.0f} $')
        log(f'  azioni per mercato: mediana {g.azioni.median():,.0f}; scambi per mercato: mediana {g.scambi.median():.0f}')
        ev = s[s.tipo == tipo].groupby('evento_id').usd.sum()
        log(f'  controvalore per evento: eventi {len(ev)}, mediana {ev.median():,.0f} $, media {ev.mean():,.0f} $')
        tg = s[s.tipo == tipo].usd
        log(f'  dimensione di uno scambio: mediana {tg.median():.2f} $, media {tg.mean():.2f} $')
    giorno = s.groupby([s.t.dt.date, 'tipo']).usd.sum().unstack().round(0)
    log('\nControvalore per giorno (UTC), $:')
    log(giorno.to_string())
    # avviso: la lettura chiede al massimo 500 scambi per 20 mercati ogni 10 minuti
    k = scambi.groupby(['giro', 'ora_lettura']).size()
    log(f'\nscambi nuovi per lettura (tutti i mercati, ogni 10 minuti): mediana {k.median():.0f}, max {k.max()}; '
        f'il limite di 500 vale per gruppo di 20 mercati, quindi nei momenti più attivi qualche scambio può mancare')


def premi(p):
    log('\n=== PREMI DI LIQUIDITÀ PER UNITÀ DI LIQUIDITÀ ESPOSTA ===')
    log('liquidità esposta = profondità entro lo spread dei premi (denaro + lettera, in azioni) registrata nel libro;')
    log('in dollari: azioni in denaro x prezzo medio + azioni in lettera x (1 - prezzo medio), cioè il capitale bloccato.')
    q = p[p.prof_bid_premi.notna()].copy()
    q['mid'] = (q.bid + q.ask) / 2
    q['prof_az'] = q.prof_bid_premi + q.prof_ask_premi
    q['prof_usd'] = q.prof_bid_premi * q.mid + q.prof_ask_premi * (1 - q.mid)
    log('fotografie con prezzo medio (servono entrambi i lati): ' + ', '.join(f'{k} {v:,}' for k, v in q.tipo.value_counts().items()))
    log('spread massimo dei premi (¢): ' + ', '.join(f'{k} {v}' for k, v in p.groupby('tipo').premi_spread.agg(
        lambda s: sorted(s.dropna().unique().tolist())).items()) + '; taglia minima (azioni): ' +
        ', '.join(f'{k} {sorted(v)}' for k, v in p.groupby('tipo').premi_min.agg(lambda s: s.dropna().unique().tolist()).items()))
    for tipo, g in [('TUTTI', q)] + list(q.groupby('tipo')):
        con = g[g.premi_giorno > 0]
        log(f'\n{tipo}: fotografie con premi > 0: {len(con) / len(g):.1%}; mercati con premi > 0: '
            f'{con.token.nunique()} su {g.token.nunique()}')
        # per istante: premi del giorno disponibili su tutti i mercati attivi e liquidità esposta
        ist = g.groupby('ora').agg(premi=('premi_giorno', 'sum'), usd=('prof_usd', 'sum'), az=('prof_az', 'sum'))
        ic = con.groupby('ora').agg(premi=('premi_giorno', 'sum'), usd=('prof_usd', 'sum'), az=('prof_az', 'sum'))
        log(f'  per fotografia (mediana sugli istanti): premi disponibili {ist.premi.median():,.0f} $/giorno, liquidità '
            f'esposta {ist.usd.median():,.0f} $ ({ist.az.median():,.0f} azioni)')
        rap = (ic.premi / ic.usd).replace(np.inf, np.nan)
        log(f'  solo mercati con premi: premi {ic.premi.median():,.0f} $/giorno su {ic.usd.median():,.0f} $ esposti; '
            f'rapporto per istante: mediana {rap.median() * 1000:.2f} $ al giorno per 1.000 $ esposti '
            f'(p25 {rap.quantile(.25) * 1000:.2f}, p75 {rap.quantile(.75) * 1000:.2f})')
        mk = con[con.prof_usd > 0].assign(r=lambda x: x.premi_giorno / x.prof_usd).groupby('token').r.median()
        if len(mk):
            log(f'  per mercato (mediana nel tempo del rapporto premi/esposto): mediana {mk.median() * 1000:.2f} $ al giorno '
                f'per 1.000 $, p75 {mk.quantile(.75) * 1000:.2f}, p90 {mk.quantile(.9) * 1000:.2f}; '
                f'per 1.000 azioni: {(con[con.prof_az > 0].premi_giorno / con[con.prof_az > 0].prof_az).median() * 1000:.2f} $/giorno')
        senza = (con.prof_az == 0).mean()
        log(f'  fotografie di mercati con premi ma nessuna liquidità entro lo spread dei premi: {senza:.1%}')
    log('\nNota: i premi si dividono fra tutti gli ordini che si qualificano, pesati per distanza dal prezzo medio e con')
    log('taglia minima; il rapporto è quindi un massimo lordo per chi si aggiunge, non un rendimento ottenibile.')


def main():
    pan, scambi, giri, mercati = carica()
    log('TEST 1 - LIBRI ORDINI POLYMARKET METEO E MACRO (regole.md, 9/10/2026); calcolo del 9/11/2026')
    log(f'fotografie ricostruite (esito x istante): {len(pan):,}; file in {DATI.relative_to(QUI.parents[1])}')
    log(f'fotografie attese con un passo di 10 minuti fra la prima e l\'ultima: '
        f'{int((giri.ora.max() - giri.ora.min()).total_seconds() // 600) + 1:,}; registrate {len(giri):,}\n')
    copertura(giri)
    p = spread(pan)
    esiti_multipli(pan, mercati)
    volume(scambi, mercati)
    premi(p)
    (QUI / 'risultati_test1.txt').write_text('\n'.join(RIGHE) + '\n')


if __name__ == '__main__':
    main()
