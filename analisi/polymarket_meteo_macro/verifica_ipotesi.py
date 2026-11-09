"""Verifica dell'ipotesi esplorativa (regole.md, scritta e approvata il 9/10/2026): nei mercati giornalieri di temperatura,
alla mezzanotte locale che apre il giorno, gli esiti SÌ fra 5¢ e 30¢ valgono meno del prezzo.

Dati: eventi_verifica.csv.gz (scaricato da verifica_ipotesi_dati.py: eventi risolti dal 10/10 al 6/11/2026, prezzo =
ultimo punto dello storico CLOB nelle 12 ore prima della decisione) e libri ordini del Test 1 (dati_test/libri/2026/).

Regole (copiate da regole.md, non si cambiano):
  - stessa misura del Test 2: per fascia di prezzo grezzo dell'esito SÌ, frequenza reale contro prezzo medio, errore
    standard sqrt(f(1-f)/n); evento scartato se mancano i prezzi di più di 2 esiti;
  - superata se nella fascia 5-30¢ la frequenza reale è inferiore al prezzo medio di almeno 2 errori standard E il
    vantaggio medio resta positivo vendendo al prezzo lettera (ask) dell'ultima fotografia del libro prima della
    decisione (eventi delle 12 città seguite dal Test 1). Misura secondaria: lo stesso al prezzo denaro (bid).
Scelte di calcolo fissate prima di vedere i risultati: la fascia si sceglie con il prezzo CLOB (la popolazione
dell'ipotesi); vantaggio di chi vende un SÌ al prezzo x = x - esito (1 se vince); un esito senza lettera nell'ultima
fotografia non entra nel conto al prezzo lettera (si riporta quanti sono).
Uscita: risultati_verifica_ipotesi.txt
"""
import glob
import math
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
DATI = QUI.parents[1] / 'dati_test' / 'libri' / '2026'
FASCE = [0, .05, .15, .30, .50, .70, .85, .95, 1.0001]
RIGHE = []


def log(t=''):
    print(t, flush=True)
    RIGHE.append(str(t))


def riga_fascia(prezzo, y):
    n = len(y)
    f = y.mean()
    se = math.sqrt(max(f * (1 - f), 1e-9) / n)
    return n, prezzo.mean(), f, se, (f - prezzo.mean()) / se


def calibrazione(d, col='p', titolo=''):
    log(f'\n{titolo}')
    log(f'{"fascia":>14} {"n":>6} {"prezzo medio":>13} {"freq. reale":>12} {"err.std":>8} {"diff/err":>9}')
    d = d.assign(fascia=pd.cut(d[col], FASCE, right=False))
    for f, g in d.groupby('fascia', observed=True):
        n, pm, fr, se, z = riga_fascia(g[col], g.y)
        log(f'{str(f):>14} {n:>6} {pm:>13.4f} {fr:>12.4f} {se:>8.4f} {z:>9.2f}')


def libri_per_token():
    """Tutte le righe dei libri con il token al posto dell'id del giro, più gli istanti di ogni giro di raccolta."""
    parti, istanti = [], []
    for f in sorted(glob.glob(str(DATI / '*_libri.csv.gz'))):
        nome = Path(f).name[:15]
        lib = pd.read_csv(f, usecols=['ora', 'id', 'bid', 'ask', 'bid_size', 'ask_size'])
        mer = pd.read_csv(DATI / f'{nome}_mercati.csv.gz', usecols=['id', 'token_si'], dtype={'token_si': str})
        lib = lib.merge(mer.drop_duplicates('id'), on='id', how='left')
        lib['ora'] = pd.to_datetime(lib.ora).astype('datetime64[us]')
        lib['giro'] = nome
        parti.append(lib)
        istanti.append(pd.DataFrame({'giro': nome, 'ora': sorted(lib.ora.unique())}))
    return pd.concat(parti, ignore_index=True), pd.concat(istanti, ignore_index=True)


def main():
    d = pd.read_csv(QUI / 'eventi_verifica.csv.gz', dtype={'token': str, 'id': str})
    d['y'] = d.vince.astype(float)
    log('VERIFICA DELL\'IPOTESI ESPLORATIVA METEO (regole.md, 9/10/2026); calcolo del 9/11/2026')
    log(f'esiti letti {len(d)}, eventi {d.id.nunique()}, giorni {d.giorno.min()} - {d.giorno.max()}, città (aeroporti) {d.icao.nunique()}')
    manc = d.groupby('id').p.apply(lambda s: s.isna().sum())
    validi = manc[manc <= 2].index
    log(f'eventi con al massimo 2 prezzi mancanti: {len(validi)} (scartati {len(manc) - len(validi)})')
    d = d[d.id.isin(validi)]
    log(f'eventi validi senza previsione Open-Meteo del giorno (nel Test 2 sarebbero stati esclusi): '
        f'{d[~d.prev_ok].id.nunique()}')
    c = d.dropna(subset=['p'])
    som = c.groupby('id').agg(somma=('p', 'sum'), tipo=('tipo', 'first'))
    log('eventi per tipo: ' + ', '.join(f'{k} {v}' for k, v in som.tipo.value_counts().items()))
    log('somma dei prezzi CLOB degli esiti di un evento (controllo, senza verdetto): ' + '; '.join(
        f'{k}: mediana {g.somma.median():.3f}, eventi con somma > 1,5: {(g.somma > 1.5).mean():.1%}'
        for k, g in som.groupby('tipo')))
    calibrazione(c, titolo='Calibrazione, tutti gli eventi validi (prezzo CLOB alla mezzanotte locale)')
    for k, g in c.groupby('tipo'):
        calibrazione(g, titolo=f'Calibrazione, solo {k} (controllo, senza verdetto)')
    fa = c[(c.p >= .05) & (c.p < .30)]
    n, pm, fr, se, z = riga_fascia(fa.p, fa.y)
    log(f'\nFASCIA 5-30¢: n {n} esiti in {fa.id.nunique()} eventi; prezzo medio {pm:.4f}; frequenza reale {fr:.4f}; '
        f'errore standard {se:.4f}; differenza {(fr - pm) * 100:+.2f}¢ = {z:+.2f} errori standard')
    crit1 = (pm - fr) >= 2 * se
    log(f'CRITERIO 1 (frequenza inferiore al prezzo di almeno 2 errori standard): {"SÌ" if crit1 else "NO"}')
    log(f'  per tipo: ' + '; '.join(
        f'{k} n {len(g)} prezzo {g.p.mean():.4f} freq {g.y.mean():.4f} ({riga_fascia(g.p, g.y)[4]:+.2f} e.s.)'
        for k, g in fa.groupby('tipo')))
    rng = np.random.default_rng(20261009)
    for k, h in [('tutti', fa)] + list(fa.groupby('tipo')):
        e = h.groupby('id').agg(s=('p', 'sum'), y=('y', 'sum'), n=('p', 'size'))
        bs = []
        for _ in range(10000):
            i = rng.integers(0, len(e), len(e))
            bs.append((e.y.values[i].sum() - e.s.values[i].sum()) / e.n.values[i].sum())
        lo, hi = np.percentile(bs, [2.5, 97.5])
        log(f'  controllo con ricampionamento per evento (10.000, senza verdetto), {k}: frequenza - prezzo '
            f'{(e.y.sum() - e.s.sum()) / e.n.sum() * 100:+.2f}¢, IC95% {lo * 100:+.2f} / {hi * 100:+.2f}¢')
    meta = sorted(fa.giorno.unique())[len(fa.giorno.unique()) // 2]
    log(f'  per metà del periodo (taglio al {meta}): ' + '; '.join(
        f'{k} n {len(g)} prezzo {g.p.mean():.4f} freq {g.y.mean():.4f} ({riga_fascia(g.p, g.y)[4]:+.2f} e.s.)'
        for k, g in fa.groupby(fa.giorno >= meta)).replace('False', 'prima').replace('True', 'seconda'))

    # ------------------------------------------------------------------ libro del Test 1
    lib, ist = libri_per_token()
    lib = lib[lib.token_si.isin(set(c.token))].sort_values('ora')
    log(f'\n=== PREZZI DEL LIBRO (Test 1) ===')
    con = c[c.token.isin(set(lib.token_si))].copy()
    log(f'esiti con almeno una fotografia del libro: {len(con)} in {con.id.nunique()} eventi '
        f'(città: {", ".join(sorted(con.serie.str.split("-daily").str[0].unique()))})')
    con['t_dec'] = pd.to_datetime(con.decisione, unit='s').astype('datetime64[us]')
    q = pd.merge_asof(con.sort_values('t_dec'), lib.drop(columns='id').rename(columns={'token_si': 'token', 'ora': 'ora_libro'})
                      .sort_values('ora_libro'), left_on='t_dec', right_on='ora_libro', by='token',
                      direction='backward')
    q = q.dropna(subset=['ora_libro'])
    # età dell'ultima fotografia: decisione meno l'ultimo istante del giro di raccolta (che contiene la riga) <= decisione
    ultimo = ist.groupby('giro').ora.max()
    q['ultima_foto'] = np.minimum(q.giro.map(ultimo), q.t_dec)
    q['eta_min'] = (q.t_dec - q.ultima_foto).dt.total_seconds() / 60
    log(f'esiti con una fotografia prima della decisione: {len(q)} in {q.id.nunique()} eventi; età dell\'ultima '
        f'fotografia: mediana {q.eta_min.median():.0f} min, entro 30 min {(q.eta_min <= 30).mean():.1%}, '
        f'oltre 6 ore {(q.eta_min > 360).mean():.1%}')
    fq = q[(q.p >= .05) & (q.p < .30)].copy()
    sp = (fq.ask - fq.bid) * 100
    log(f'  spread del libro alla decisione per gli esiti 5-30¢: ' + '; '.join(
        f'{k} mediana {h.median():.1f}¢' for k, h in sp.groupby(fq.tipo)))
    log(f'\nFASCIA 5-30¢ (scelta col prezzo CLOB), esiti con libro: {len(fq)} in {fq.id.nunique()} eventi; '
        f'senza lettera: {fq.ask.isna().sum()}; senza denaro: {fq.bid.isna().sum()}')
    n2, pm2, fr2, se2, z2 = riga_fascia(fq.p, fq.y)
    log(f'  stesso sottoinsieme al prezzo CLOB: prezzo medio {pm2:.4f}, frequenza {fr2:.4f}, e.s. {se2:.4f} ({z2:+.2f} e.s.)')
    risultati = {}
    for nome, col in (('LETTERA (ask), misura del verdetto', 'ask'), ('DENARO (bid), misura secondaria', 'bid'),
                      ('PREZZO MEDIO DEL LIBRO, solo confronto', 'mid')):
        if col == 'mid':
            fq['mid'] = (fq.ask + fq.bid) / 2
        g = fq.dropna(subset=[col])
        v = g[col] - g.y
        sev = v.std(ddof=1) / math.sqrt(len(v))
        n3, pm3, fr3, se3, z3 = riga_fascia(g[col], g.y)
        risultati[col] = v.mean()
        per_tipo = '; '.join(f'{k} n {len(h)} vantaggio {(h[col] - h.y).mean() * 100:+.2f}¢ '
                             f'(e.s. {(h[col] - h.y).std(ddof=1) / math.sqrt(len(h)) * 100:.2f}¢), prezzo CLOB '
                             f'{h.p.mean():.4f}, freq {h.y.mean():.4f}' for k, h in g.groupby('tipo'))
        log(f'  al {nome}: n {len(g)}; prezzo medio {pm3:.4f}, frequenza {fr3:.4f} ({z3:+.2f} e.s.); vantaggio medio '
            f'di chi vende {v.mean() * 100:+.2f}¢ per azione (e.s. {sev * 100:.2f}¢, t {v.mean() / sev:+.2f})')
        log(f'    per tipo: {per_tipo}')
        if col == 'ask':
            log(f'    stesso conto solo con fotografie entro 30 min: ' + (
                lambda h: f'n {len(h)}, vantaggio {(h.ask - h.y).mean() * 100:+.2f}¢' if len(h) else 'nessuna')(
                g[g.eta_min <= 30]))
            log(f'    lettera meno prezzo CLOB: mediana {(g.ask - g.p).median() * 100:+.2f}¢, media {(g.ask - g.p).mean() * 100:+.2f}¢')
    calibrazione(q.dropna(subset=['ask']), 'ask', 'Calibrazione al prezzo lettera, eventi con libro (fasce scelte con la lettera)')
    crit2 = risultati['ask'] > 0
    log(f'\nCRITERIO 2 (vantaggio medio positivo vendendo al prezzo lettera): {"SÌ" if crit2 else "NO"}')
    log(f'VERDETTO IPOTESI: {"SUPERATA" if (crit1 and crit2) else "NON SUPERATA"}')
    (QUI / 'risultati_verifica_ipotesi.txt').write_text('\n'.join(RIGHE) + '\n')


if __name__ == '__main__':
    main()
