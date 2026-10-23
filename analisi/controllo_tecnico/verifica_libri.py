"""Verifica dal vivo (23/10/2026) della correzione di scegli_mercati in libri.py: eventi meteo ripetuti e token doppi."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'polymarket_meteo_macro'))
import libri  # noqa: E402

for prova in range(3):
    e = libri.eventi('daily-temperature')
    ids = [x.get('id') for x in e]
    m = libri.scegli_mercati(dt.datetime.now(dt.timezone.utc))
    m.set_index('token_si').to_dict('index')           # il punto che il 23/10 alle 05:13 UTC era fallito
    print(f'prova {prova + 1}: eventi meteo letti {len(ids)}, ripetuti {len(ids) - len(set(ids))}; '
          f'mercati scelti {len(m)} ({(m.tipo == "meteo").sum()} meteo, {(m.tipo == "macro").sum()} macro), '
          f'token unici {m.token_si.nunique()}; to_dict ok', flush=True)
