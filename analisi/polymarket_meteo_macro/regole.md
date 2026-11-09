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
- **Frequenza**: ogni 10 minuti. Le regole del 9/10 dicevano 5: il giro di prova pesava circa 17 MB al giorno, quindi la frequenza è stata dimezzata lo stesso giorno, prima di qualsiasi risultato. Gli scambi restano registrati tutti.
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

## Esito del Test 2 (9/10/2026) e conseguenze

- **Meteo, modello contro mercato: NON SUPERATO.** Su 1.220 eventi di verifica il Brier è 0,801 per il modello e 0,674
  per il mercato (differenza +0,127, IC95% +0,111 / +0,143). Il modello batte il mercato in 1 città su 37 e la miscela
  50/50 è anch'essa peggiore del mercato. La previsione gratuita del giorno prima non aggiunge informazione al prezzo.
- **Calibrazione meteo**: la distorsione verso le scommesse improbabili è presente secondo il criterio fissato (fascia
  0-5¢: 0,60% di frequenza reale contro 0,81¢ di prezzo medio, −3,5 errori standard) ma vale circa 0,2¢ per azione.
- **Calibrazione macro**: nessuna distorsione significativa (tutte le fasce entro 2 errori standard; 820 esiti, 130 eventi).
- **Test 3 come definito sopra non si esegue**: la sua condizione (modello o miscela migliore del mercato) non è
  soddisfatta.

## Ipotesi esplorativa nata dal Test 2 (scritta il 9/10/2026, approvata lo stesso giorno: verifica il 9/11/2026)

Guardando la calibrazione meteo divisa nelle due metà del periodo (analisi fatta dopo aver visto i dati, quindi solo
esplorativa), gli esiti a 15-30¢ risultano cari di circa 1,8¢ in entrambe le metà (circa −1,8 errori standard
ciascuna). Gli esiti a 5-15¢ sono leggermente cari in entrambe le metà.

**Ipotesi da confermare su dati nuovi**: nei mercati giornalieri di temperatura, alla mezzanotte locale che apre il
giorno, gli esiti SÌ fra 5¢ e 30¢ valgono meno del prezzo.

- **Verifica**: sugli eventi risolti dal 10/10/2026 al 6/11/2026, che non sono mai stati usati, con la stessa misura e
  lo stesso momento di decisione.
- **Superata se**: nella fascia 5-30¢ la frequenza reale è inferiore al prezzo medio di almeno 2 errori standard, **e**
  il vantaggio medio resta positivo dopo aver venduto al prezzo lettera del libro registrato dal Test 1 (non al prezzo
  medio).
- **Se superata**, il passo dopo è la simulazione su carta di un market maker che espone lettere su quelle fasce, con le
  regole del Test 3.

## Esito del Test 1 (analisi del 9/11/2026)

Misure in [risultati_test1.txt](risultati_test1.txt) (script `test1_analisi.py`), resoconto in
[analisi/resoconti/2026-11-09_polymarket_meteo_macro.md](../resoconti/2026-11-09_polymarket_meteo_macro.md).

- **Copertura**: 3.375 fotografie su 4.096 attese (dal 9/10 13:12 al 6/11 23:48 UTC); 60 buchi oltre 30 minuti, 105 ore
  in tutto (15,4%), il più lungo 7,5 ore, tutti fra un giro di raccolta e il successivo (86 ore dal 26/10). Gli scambi
  mancano dal 2/11 20:38 UTC: dal 3/11 nessun giro ha registrato scambi e i giri sono rallentati a 13-15 minuti.
- **Spread mediano**: meteo 2¢ (medio 8,5¢), macro 2¢ (medio 4,5¢); fra 5¢ e 95¢ meteo 4¢ (medio 15,9¢), macro 3¢.
  Nel meteo il 52% delle fotografie non ha denaro sull'esito SÌ.
- **Somma dei SÌ**: lettere sotto 1 $ nello 0,20% delle fotografie complete, denari sopra 1 $ nello 0,90%; margini
  mediani 0,8¢ e 0,6¢ su circa 5 azioni: nessuno spazio pratico.
- **Volume** (9/10-2/11): meteo 9,2 milioni $ su 6.476 mercati con scambi (mediana 347 $ per mercato, 8.370 $ per
  evento); macro 19,7 milioni $ su 157 mercati (mediana 1.101 $).
- **Premi**: nei mercati meteo con premi, mediana per istante 13,8 $ al giorno ogni 1.000 $ esposti entro lo spread dei
  premi (macro 2,3 $); è un massimo lordo da dividere con chi si aggiunge.

## Esito della verifica dell'ipotesi esplorativa (9/11/2026): SUPERATA secondo le regole, con una riserva

Conti in [risultati_verifica_ipotesi.txt](risultati_verifica_ipotesi.txt) (dati: `verifica_ipotesi_dati.py`, conto:
`verifica_ipotesi.py`). 2.498 eventi dal 10/10 al 6/11/2026 (1.305 massime, 1.193 minime, 49 città).

- **Criterio 1**: fascia 5-30¢, 5.240 esiti, prezzo medio 15,73¢, frequenza reale 8,65%, errore standard 0,39¢:
  −7,08¢, pari a −18,2 errori standard. Superato.
- **Criterio 2**: 1.427 esiti della fascia con libro (12 città, 591 eventi); vendendo al prezzo lettera dell'ultima
  fotografia il vantaggio medio è +13,95¢ per azione (errore standard 0,81¢). Superato. Al prezzo denaro (misura
  secondaria, 1.021 esiti) il vantaggio è −0,55¢ (errore standard 0,97¢).
- **Riserva da leggere prima di qualsiasi passo**: dal 10/10 le minime sono quasi metà degli eventi (nel Test 2 erano il
  12%) e i loro prezzi CLOB alla mezzanotte non sono prezzi veri: la somma dei prezzi di un evento di minima ha mediana
  2,95 (83% degli eventi sopra 1,5), perché i libri sono vuoti o larghissimi (spread mediano 9¢ nella fascia, spesso
  senza denaro). Gran parte dell'effetto viene da lì. Sulle sole massime (controllo, senza verdetto) l'effetto è molto
  più piccolo ma c'è: −1,58¢ (ricampionamento per evento: IC95% −2,71 / −0,46¢), vantaggio al prezzo lettera +4,90¢,
  al prezzo denaro +1,84¢ (errore standard 1,27¢).
- Nota sui dati: dal 10/10 la fonte di risoluzione non è più Wunderground (weather.gov fino al 22/10, poi METAR di
  aviationweather.gov). Il codice della stazione serve solo per il fuso orario; gli eventi senza fonte (134: Tel Aviv,
  Hong Kong, Mosca, Istanbul in parte del periodo) sono esclusi come lo sarebbero stati nel Test 2.

Vendere al prezzo lettera vale solo se qualcuno compra a quel prezzo: è proprio ciò che il Test 3 deve misurare.

## Test 3: simulazione su carta del market maker (regole scritte il 9/11/2026, prima di qualsiasi simulazione; NON eseguito)

Le regole vanno approvate dal proprietario in chat prima di raccogliere i dati.

- **Universo**: eventi `daily-temperature` delle 12 città del Test 1, massime e minime, risolti in un **periodo nuovo**
  di raccolta di almeno 4 settimane che inizia dopo l'approvazione. I dati del Test 1 servono solo a collaudare il
  simulatore, senza verdetto (le loro risoluzioni sono già state guardate).
- **Ordine**: alla mezzanotte locale che apre il giorno, per ogni esito SÌ con prezzo CLOB (ultimo punto nelle 12 ore
  prima) fra 5¢ e 30¢, una vendita limite di 20 azioni al prezzo `max(lettera migliore − 1 tick, denaro migliore +
  1 tick)` dell'ultima fotografia del libro, che deve avere al massimo 30 minuti; senza fotografia, o senza lettera,
  nessun ordine. L'ordine resta fermo fino alla mezzanotte locale che chiude il giorno, senza modifiche né
  cancellazioni.
- **Esecuzione** (ipotesi prudente): l'ordine si considera eseguito solo da scambi avvenuti dopo il suo inserimento a
  un prezzo strettamente migliore del nostro: acquisti di SÌ a un prezzo maggiore del nostro, oppure vendite di NO a un
  prezzo minore di 1 − il nostro. Le azioni eseguite sono la somma delle quantità di quegli scambi, fino a 20.
- **Risultato**: per azione eseguita, prezzo − esito (1 se il SÌ vince), meno le commissioni del `feeSchedule` del
  mercato se diverse da zero. Capitale impegnato: 1 − prezzo per azione venduta. I premi di liquidità non entrano nel
  risultato principale.
- **Misure**: ordini, quota eseguita, risultato medio per azione eseguita, risultato totale, risultato sul capitale;
  frequenza del SÌ negli ordini eseguiti contro quelli non eseguiti (selezione avversa); tutto separato per massima e
  minima.
- **Criterio di successo**, tutti richiesti: almeno 200 ordini eseguiti (se meno, la raccolta continua fino a 200);
  risultato medio per azione eseguita positivo con intervallo bootstrap al 95% (per evento, 10.000 ricampionamenti,
  seme 20261109) che esclude zero; risultato positivo in entrambe le metà del periodo, in ordine di data.

**Cosa servirebbe per eseguirlo**:
1. Approvazione esplicita di queste regole da parte del proprietario.
2. Una nuova raccolta: `libri.py` ha `FINE_TEST` al 6/11/2026; andrebbe riattivato per il nuovo periodo (bastano i
   mercati meteo delle 12 città) e il workflow `libri.yml` ripartirebbe da solo. È una modifica all'automazione da
   approvare prima.
3. Sistemare la lettura degli scambi, che dal 3/11 non restituisce nulla (va capito il motivo) e legge al massimo 500
   scambi per gruppo di 20 mercati: per il Test 3 gli scambi sono indispensabili, quindi meglio una lettura per mercato,
   e un avviso in `STATO.md` se un giro non ne registra.
4. Uno script `test3_simulazione.py` collaudato sui dati del Test 1 (dal 10/10 al 2/11, senza verdetto).
