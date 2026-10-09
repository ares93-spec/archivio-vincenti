# Polymarket, meteo e macro: regole fissate il 9/10/2026, prima di qualsiasi risultato

Obiettivo: capire se su Polymarket esiste spazio per un market maker "informato", cioè uno che espone denaro e lettera
intorno a un prezzo giusto calcolato da un modello, sui mercati meteo e macro. Nessuna operatività: solo dati pubblici
e simulazioni.

## Test 1: fotografia dei libri ordini (dal 9/10/2026 al 6/11/2026)

- **Mercati meteo**: eventi giornalieri di temperatura (etichetta `daily-temperature`), massima e minima, solo per 12
  città: New York, Londra, Seoul, Miami, Chicago, Dallas, Atlanta, Toronto, Parigi, Tokyo, Buenos Aires, Seattle.
  Solo eventi che scadono entro 48 ore.
- **Mercati macro**: eventi aperti delle serie su inflazione USA (mensile e annua, core), occupati (jobs added),
  disoccupazione, decisioni della Fed, PCE, PPI, richieste di sussidio e PIL USA.
- **Frequenza**: ogni 5 minuti.
  - Dal libro di ogni esito SÌ si salvano i primi 3 livelli per lato, la profondità entro 2¢ ed entro lo spread dei
    premi.
  - Si salvano anche i nuovi scambi di quei mercati (Data API `/trades`), che servono a simulare quando un ordine
    limite sarebbe stato eseguito.
  - Una volta all'ora si salvano i parametri dei premi di liquidità.
- **Misure, a fine periodo**:
  - spread medio e mediano per tipo di mercato e per distanza dalla scadenza;
  - frequenza di "SÌ di tutti gli esiti < 1 $" e "> 1 $" nei mercati a esiti multipli;
  - volume scambiato per mercato;
  - premi giornalieri disponibili per unità di liquidità esposta.

## Test 2: modello contro mercato su eventi già risolti

### Meteo (test principale)

- **Universo**: eventi `daily-temperature` chiusi, con esito, terminati tra l'1/12/2025 e l'8/10/2026. Se sono più di
  2.500, se ne estrae un campione casuale di 2.500 con seme fisso 20261009.
- **Momento della decisione**: la mezzanotte locale che apre il giorno dell'evento (fine del giorno prima).
- **Prezzo di mercato**:
  - per ogni esito, l'ultimo prezzo dello storico CLOB nelle 12 ore precedenti la decisione;
  - le probabilità si normalizzano a somma 1 sugli esiti dell'evento;
  - l'evento si scarta se mancano i prezzi di più di 2 esiti.
- **Modello**:
  - Massimo (o minimo) delle temperature orarie del giorno locale, prese dalla previsione emessa il giorno prima
    (Open-Meteo, `temperature_2m_previous_day1`). Il punto di previsione è l'aeroporto di risoluzione (codice ICAO
    nell'URL Wunderground; coordinate da OurAirports).
  - Valore vero X ~ Normale(previsione + distorsione, sigma), con distorsione e sigma stimati per città e tipo
    (massima/minima) sulla metà di addestramento.
  - Il valore osservato è il centro dell'esito vincente. Gli esiti estremi ("o meno", "o più") non entrano nella stima.
  - Con meno di 15 eventi di addestramento si usano distorsione e sigma globali del tipo. Sigma ha un minimo di
    1 grado.
  - Probabilità di un esito: P(estremo inferiore − 0,5 ≤ X < estremo superiore + 0,5), nell'unità del mercato (°C o °F).
- **Divisione**: metà degli eventi in ordine di data per l'addestramento, metà per la verifica. Si giudica solo la
  verifica.
- **Misura principale**: Brier score multi-esito (somma dei quadrati degli errori sugli esiti), modello contro mercato,
  sulla metà di verifica.
- **Criterio di successo**, tutti richiesti:
  1. Brier del modello inferiore a quello del mercato, con intervallo bootstrap al 95% (per evento, 10.000
     ricampionamenti) della differenza che esclude zero;
  2. il modello batte il mercato in almeno 2/3 delle città con almeno 20 eventi di verifica.
- **Misure secondarie** (senza verdetto):
  - log-loss;
  - miscela 50/50 di modello e mercato contro mercato: se la miscela batte il mercato, il modello aggiunge
    informazione anche senza batterlo da solo;
  - risultati separati per massima e minima e per °C e °F.

### Calibrazione dei prezzi (meteo e macro)

- **Macro**: eventi chiusi delle serie macro del Test 1. Prezzo di ogni esito 24 ore prima della prima chiusura di un
  mercato dell'evento.
- **Meteo**: gli stessi eventi e prezzi del test principale.
- **Misura**: per fasce di prezzo (0-5¢, 5-15¢, 15-30¢, 30-50¢, 50-70¢, 70-85¢, 85-95¢, 95-100¢), frequenza reale del
  SÌ contro prezzo medio, con errore standard.
- **Distorsione verso le scommesse improbabili** (favourite-longshot): presente se nella fascia 0-5¢ o 5-15¢ la
  frequenza reale è inferiore al prezzo medio di oltre 2 errori standard.

## Test 3 (dopo il 6/11/2026): simulazione su carta del market maker

Da definire con regole scritte prima, sui dati del Test 1 e solo se il Test 2 mostra che il modello aggiunge
informazione (criterio principale superato o miscela migliore del mercato).

Ipotesi prudente da usare: un ordine limite si considera eseguito solo quando uno scambio avviene a un prezzo
strettamente migliore del nostro.
