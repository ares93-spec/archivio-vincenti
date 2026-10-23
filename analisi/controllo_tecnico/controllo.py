"""Controllo tecnico delle prime due settimane (README, sezione 4: venerdì 23/10/2026).

Legge solo il repository (file in dati/, dati_test/, stato/ e storia git): nessuna rete.
Uso: python analisi/controllo_tecnico/controllo.py > analisi/controllo_tecnico/controllo.txt
"""
import datetime as dt
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd

RADICE = Path(__file__).resolve().parents[2]
INIZIO, FINE = dt.date(2026, 10, 9), dt.date(2026, 10, 22)      # 23/10: il giro della sera non è ancora partito
GIORNI = [INIZIO + dt.timedelta(d) for d in range((FINE - INIZIO).days + 1)]
FERIALI = [g for g in GIORNI if g.weekday() < 5]
FILE = {'apewisdom': ['menzioni'], 'cboe': ['sottostanti', 'scadenze'], 'polymarket': ['classifiche', 'pannello'],
        'hyperliquid': ['classifica', 'vault', 'posizioni', 'fill']}


def git(*a):
    return subprocess.check_output(['git', *a], cwd=RADICE, text=True)


def mb(x):
    return x / 1024 / 1024


print('=== 1. Giorni registrati (dal 2026-10-09 al 2026-10-22) ===')
peso = defaultdict(dict)              # fonte -> giorno -> byte
righe = defaultdict(dict)
for fonte, nomi in FILE.items():
    attesi = FERIALI if fonte == 'cboe' else GIORNI
    for g in GIORNI:
        tot, n, presenti = 0, 0, 0
        for nome in nomi:
            p = RADICE / 'dati' / fonte / str(g.year) / f'{g.isoformat()}_{nome}.csv.gz'
            if p.exists():
                presenti += 1
                tot += p.stat().st_size
                n += len(pd.read_csv(p, low_memory=False))
        if presenti:
            peso[fonte][g] = tot
            righe[fonte][g] = n
        if presenti not in (0, len(nomi)):
            print(f'  {fonte} {g}: file incompleti ({presenti}/{len(nomi)})')
    mancanti = [g.isoformat() for g in attesi if g not in peso[fonte]]
    extra = [g.isoformat() for g in peso[fonte] if g not in attesi]
    print(f'{fonte:12s} attesi {len(attesi):2d}, registrati {len(peso[fonte]):2d}, '
          f'mancanti {mancanti or "nessuno"}, fuori calendario {extra or "nessuno"}')

print('\nRighe per giorno (somma dei file della fonte):')
print('giorno       ' + ''.join(f'{f:>13s}' for f in FILE))
for g in GIORNI:
    print(f'{g} {g.strftime("%a")[:3]}' + ''.join(f'{righe[f].get(g, 0):>13d}' for f in FILE))

print('\n=== 2. Commit "Archivio del ..." (attesi: uno al giorno) ===')
log = git('log', '--reverse', '--date=iso-strict', '--format=%h|%ad|%s').splitlines()
arch = [l.split('|') for l in log if '|Archivio del ' in l]
per_data = defaultdict(list)
for h, quando, s in arch:
    per_data[s.split()[-1]].append((h, quando))
for g in GIORNI + [FINE + dt.timedelta(1)]:
    c = per_data.get(g.isoformat(), [])
    nota = '' if len(c) == 1 else ('  <-- nessuno' if not c else f'  <-- {len(c)} commit')
    print(f'{g}: ' + ', '.join(f'{h} ({q[11:16]} UTC del {q[:10]})' for h, q in c) + nota)

print('\n=== 3. Peso per giorno (MB, file compressi in dati/) ===')
print('giorno       ' + ''.join(f'{f:>13s}' for f in FILE) + '       totale')
for g in GIORNI:
    t = sum(peso[f].get(g, 0) for f in FILE)
    print(f'{g} {g.strftime("%a")[:3]}' + ''.join(f'{mb(peso[f].get(g, 0)):>13.3f}' for f in FILE) + f'{mb(t):>13.3f}')
# media sugli ultimi 7 giorni (dal 16/10: pannelli già a regime), Cboe pesata sui giorni feriali
ultimi = GIORNI[-7:]
media = {f: sum(peso[f].get(g, 0) for g in ultimi) / 7 for f in FILE}
media_14 = {f: sum(peso[f].get(g, 0) for g in GIORNI) / len(GIORNI) for f in FILE}
print('media al giorno di calendario, 14 giorni: ' + ', '.join(f'{f} {mb(v):.3f}' for f, v in media_14.items())
      + f' -> totale {mb(sum(media_14.values())):.3f} MB')
print('media al giorno di calendario, ultimi 7:  ' + ', '.join(f'{f} {mb(v):.3f}' for f, v in media.items())
      + f' -> totale {mb(sum(media.values())):.3f} MB')
dati_oggi = sum(p.stat().st_size for p in (RADICE / 'dati').rglob('*') if p.is_file())
test_oggi = sum(p.stat().st_size for p in (RADICE / 'dati_test').rglob('*') if p.is_file())
print(f'\ndati/ oggi: {mb(dati_oggi):.1f} MB; dati_test/ oggi: {mb(test_oggi):.1f} MB')
giorno = sum(media.values())
for mesi, giorni in ((6, 182), (12, 365)):
    gg = (INIZIO + dt.timedelta(giorni) - FINE).days
    stima = dati_oggi + giorno * gg
    print(f'proiezione dati/ a {mesi} mesi dal 9/10 ({(INIZIO + dt.timedelta(giorni)).isoformat()}): '
          f'{mb(stima):.0f} MB (soglia 700 MB), con il ritmo degli ultimi 7 giorni')
giorni_700 = (700 * 1024 * 1024 - dati_oggi) / giorno
print(f'dati/ arriva a 700 MB dopo circa {giorni_700:.0f} giorni da oggi ({(FINE + dt.timedelta(giorni_700)).isoformat()})')

print('\nTest 1 libri ordini (dati_test/libri), peso per giorno (MB):')
libri_g = defaultdict(int)
for p in (RADICE / 'dati_test' / 'libri').rglob('*.csv.gz'):
    libri_g[p.name[:10]] += p.stat().st_size
for g in sorted(libri_g):
    print(f'  {g}: {mb(libri_g[g]):.2f}')
pieni = [libri_g[g.isoformat()] for g in GIORNI[1:]]         # 9/10 è iniziato a metà giornata
ritmo = sum(pieni) / len(pieni)
resto = (dt.date(2026, 11, 6) - FINE).days
print(f'  media sui giorni interi 10-22/10: {mb(ritmo):.2f} MB al giorno; fino al 6/11 altri {resto} giorni '
      f'-> dati_test/ a circa {mb(test_oggi + ritmo * resto):.0f} MB a fine test')

print('\n=== 4. Tempi del giro e pannelli (STATO.md di ogni commit "Archivio del ...") ===')
rx_giro = re.compile(r'Ultimo giro: \*\*(.+?)\*\* ora italiana \(([\d.]+) minuti\)')
rx_pan = re.compile(r'pannello: (\d+) wallet letti su (\d+), (\d+) senza risposta')
rx_cboe = re.compile(r'seguiti (\d+); letti (\d+), senza catena (\d+)')
rx_hl = re.compile(r'pannello: (\d+) wallet, (\d+) posizioni aperte, (\d+) fill, (\d+) ad alta frequenza esclusi, (\d+) errori')
print('commit   giro (ora italiana)  minuti  PM letti/pannello  Cboe seguiti/letti/senza  HL wallet/errori  fonti ❌')
for h, quando, s in arch:
    t = git('show', f'{h}:STATO.md')
    m = rx_giro.search(t)
    pn = rx_pan.search(t)
    cb = rx_cboe.search(t)
    hl = rx_hl.search(t)
    ko = t.count('❌')
    print(f'{h}  {m.group(1) if m else "?":17s} {m.group(2) if m else "?":>7s}  '
          f'{(pn.group(1) + "/" + pn.group(2)) if pn else "-":>17s}  '
          f'{("/".join(cb.groups())) if cb else "-":>24s}  {(hl.group(1) + "/" + hl.group(5)) if hl else "-":>16s}  {ko}')

# crescita dei pannelli dal giro serale del 9/10 (bad653f) all'ultimo
def conta(h):
    t = git('show', f'{h}:STATO.md')
    return int(rx_pan.search(t).group(2)), int(rx_cboe.search(t).group(1))
p0, c0 = conta('bad653f')
p1, c1 = conta(arch[-1][0])
gg = 13
vp, vc = (p1 - p0) / gg, (c1 - c0) / gg
print(f'\npannello Polymarket: da {p0} a {p1} wallet in {gg} giorni = {vp:.1f} al giorno; '
      f'tetto 6.000 raggiunto fra circa {(6000 - p1) / vp:.0f} giorni ({(FINE + dt.timedelta((6000 - p1) / vp)).isoformat()}) a questo ritmo')
print(f'titoli Cboe seguiti: da {c0} a {c1} in {gg} giorni = {vc:.1f} al giorno; tetto 260 raggiunto fra circa '
      f'{(260 - c1) / vc:.0f} giorni ({(FINE + dt.timedelta((260 - c1) / vc)).isoformat()}) se la crescita resta lineare '
      f'(le prime uscite per i 35 giorni arrivano dal 13/11)')

print('\n=== 5. Titoli senza catena Cboe (stato/cboe_errori.txt) ===')
err = [r for r in (RADICE / 'stato' / 'cboe_errori.txt').read_text().splitlines() if r.strip()]
print(f'ultimo giro (22/10): {len(err)} titoli senza catena: ' + ', '.join(r.split(':')[0] for r in err))
tipi = defaultdict(int)
for r in err:
    tipi[r.split(':', 1)[1].strip()[:40]] += 1
for k, v in tipi.items():
    print(f'  {v} x {k}')
storia = defaultdict(int)
for h, quando, s in arch:
    try:
        e = git('show', f'{h}:stato/cboe_errori.txt').splitlines()
    except subprocess.CalledProcessError:
        continue
    for r in e:
        if r.strip():
            storia[r.split(':')[0]] += 1
print('titoli senza catena più ricorrenti (numero di giri su', len(arch), '):',
      ', '.join(f'{k} {v}' for k, v in sorted(storia.items(), key=lambda x: -x[1])[:20]))

print('\n=== 6. Test 1 Polymarket: fotografie dei libri ordini ===')
fotografie = defaultdict(set)
scambi_g = defaultdict(int)
for p in sorted((RADICE / 'dati_test' / 'libri').rglob('*_libri.csv.gz')):
    ore = pd.read_csv(p, usecols=['ora']).ora.unique()
    for o in ore:
        fotografie[o[:10]].add(o[:16])
for p in sorted((RADICE / 'dati_test' / 'libri').rglob('*_scambi.csv.gz')):
    s = pd.read_csv(p, usecols=['ora_lettura'])
    for g, n in s.ora_lettura.str[:10].value_counts().items():
        scambi_g[g] += n
tutte = sorted(o for v in fotografie.values() for o in v)
print('giorno      fotografie (attese 144)  scambi registrati')
for g in sorted(fotografie):
    print(f'{g}  {len(fotografie[g]):>22d}  {scambi_g.get(g, 0):>17d}')
tt = [dt.datetime.fromisoformat(o) for o in tutte]
buchi = [(a, b) for a, b in zip(tt, tt[1:]) if (b - a).total_seconds() > 15 * 60]
print(f'fotografie totali: {len(tt)}, dal {tutte[0]} al {tutte[-1]} UTC')
print(f'buchi oltre 15 minuti: {len(buchi)}; durata totale {sum((b - a).total_seconds() for a, b in buchi) / 3600:.1f} ore')
lunghi = sorted(buchi, key=lambda x: (x[1] - x[0]), reverse=True)[:8]
for a, b in lunghi:
    print(f'  {a:%Y-%m-%d %H:%M} -> {b:%Y-%m-%d %H:%M} ({(b - a).total_seconds() / 60:.0f} minuti)')
