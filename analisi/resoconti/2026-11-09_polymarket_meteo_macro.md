# 9/11/2026 — Polymarket meteo e macro: Test 1 e verifica dell'ipotesi esplorativa

Regole: [analisi/polymarket_meteo_macro/regole.md](../polymarket_meteo_macro/regole.md), fissate il 9/10/2026.
Tutti i numeri vengono da `risultati_test1.txt` e `risultati_verifica_ipotesi.txt` nella stessa cartella.

## Verdetto dell'ipotesi: SUPERATA secondo le regole, con una riserva importante

Ipotesi: nei mercati giornalieri di temperatura, alla mezzanotte locale che apre il giorno, gli esiti SÌ fra 5¢ e 30¢
valgono meno del prezzo.

| Misura | Valore | Soglia | Esito |
|---|---|---|---|
| Fascia 5-30¢, tutti gli eventi (5.240 esiti, 2.119 eventi) | prezzo 15,73¢, frequenza 8,65%, −7,08¢ = −18,2 errori standard | ≤ −2 errori standard | sì |
| Vantaggio vendendo al prezzo lettera (1.427 esiti con libro, 12 città) | +13,95¢ per azione (e.s. 0,81¢) | > 0 | sì |
| Misura secondaria: al prezzo denaro (1.021 esiti con denaro) | −0,55¢ per azione (e.s. 0,97¢) | — | — |

**La riserva.** Dal 10/10 le minime sono 1.193 eventi su 2.498 (nel Test 2 erano 285 su 2.439) e i loro prezzi CLOB a
mezzanotte non sono prezzi di mercato: la somma dei prezzi degli esiti di un evento di minima ha mediana 2,95 (massime:
1,02) e supera 1,5 nell'83% degli eventi. Sono libri vuoti o larghissimi (spread mediano 9¢ nella fascia, 406 esiti su
1.427 senza denaro), dove lo storico CLOB registra un prezzo medio fittizio. Esempio: minima di New York del 10/10,
esito 48-49°F, prezzo CLOB 22,5¢, nel libro nessun denaro e lettera a 45¢. Sulle minime il "vantaggio" al prezzo
lettera (+20,3¢) è il prezzo a cui nessuno compra.

Controlli senza verdetto (non cambiano l'esito, servono a leggerlo):

| Sottoinsieme, fascia 5-30¢ | Frequenza − prezzo | IC95% per evento | Vantaggio a lettera | Vantaggio a denaro |
|---|---|---|---|---|
| Solo massime (2.401 esiti; 588 con libro) | −1,58¢ (−2,30 e.s.) | −2,71 / −0,46¢ | +4,90¢ (e.s. 1,27) | +1,84¢ (e.s. 1,27) |
| Solo minime (2.839 esiti; 839 con libro) | −11,73¢ (−28,9 e.s.) | −12,55 / −10,90¢ | +20,29¢ (e.s. 1,00) | −3,81¢ (e.s. 1,48, 433 esiti) |
| Prima metà (fino al 23/10) / seconda metà | −9,67 / −15,89 e.s. | | | |

Sulle massime l'effetto c'è ma è piccolo (circa 1,6¢, dello stesso ordine visto nel Test 2), e al prezzo denaro il
vantaggio non è distinguibile da zero. Il vantaggio al prezzo lettera presuppone che qualcuno compri a quel prezzo: è
la domanda del Test 3.

Le regole del Test 3 sono scritte in `regole.md` (sezione "Test 3"), **non eseguite**: richiedono l'approvazione del
proprietario, un nuovo periodo di raccolta di almeno 4 settimane e la lettura degli scambi sistemata (vedi sotto).

Nota sui dati della verifica: dal 10/10 la fonte di risoluzione è cambiata da Wunderground a weather.gov e poi (dal
23/10) ai METAR di aviationweather.gov. La lettura del Test 2 scartava questi eventi; il codice della stazione (che
serve solo per il fuso orario) ora si legge anche dai nuovi indirizzi. 134 eventi senza fonte (Tel Aviv, Hong Kong,
Mosca, Istanbul in parte del periodo) restano esclusi. Nessun evento ha più di 2 prezzi mancanti; tutti hanno la
previsione Open-Meteo del giorno.

## Test 1: libri ordini dal 9/10 al 6/11/2026

**Copertura.** 3.375 fotografie su 4.096 attese con un passo di 10 minuti (82%), dal 9/10 13:12 al 6/11 23:48 UTC,
in 103 giri di raccolta. 60 buchi oltre 30 minuti, 105 ore in tutto (15,4%), tutti fra un giro e il successivo; il più
lungo 7,5 ore; 86 ore di buco cadono dal 26/10 in poi. Giorni completi (24 ore con fotografie) dal 10/10 al 25/10 tranne il
23/10; dal 26/10 mancano da 1 a 9 ore quasi ogni giorno (completo solo il 31/10), più spesso alle 20-21 e alle 11-12 UTC. Ore con almeno una fotografia:
626 su 696. Gli **scambi mancano dal 2/11 20:38 UTC**: gli ultimi 12 giri (dal 3/11) non hanno registrato scambi e hanno
fotografato ogni 13-15 minuti invece di 10. Il volume del 3-6/11 manca.

**Spread** (lettera − denaro dell'esito SÌ, fotografie con entrambi i lati):

| | Tutti: mediano / medio | Prezzo 5-95¢: mediano / medio | Prezzo 5-30¢: mediano / medio |
|---|---|---|---|
| Meteo | 2,0 / 8,5¢ | 4,0 / 15,9¢ | 4,0 / 9,3¢ |
| Macro | 2,0 / 4,5¢ | 3,0 / 6,9¢ | 3,6 / 7,4¢ |

Per distanza dalla scadenza (meteo, prezzo 5-95¢): 24-48 ore 4¢ mediano (12,5¢ medio), 6-24 ore 4¢ (12,2¢), 0-6 ore
6¢ (27,7¢), dopo la data di fine 12¢ (31,0¢). Macro: da 2¢ a 4,5¢ mediani in tutte le fasce. Nel meteo il 52,4% delle
fotografie non ha denaro sull'esito SÌ (macro 3,9%). Nessun libro incrociato.

**Somma dei SÌ negli eventi a esiti multipli** (763 eventi con almeno 3 esiti; 236.368 fotografie con il libro di tutti
gli esiti): somma delle lettere sotto 1 $ nello 0,20% (429 fotografie, 89 eventi; 196 con margine di almeno 1¢), somma
dei denari sopra 1 $ nello 0,90% (2.136 fotografie, 220 eventi; 619 con almeno 1¢). Margine mediano 0,8¢ e 0,6¢,
quantità mediana 5 azioni per esito al primo livello. Somma mediana delle lettere 1,156, dei denari 0,919. Nessuno
spazio pratico per un arbitraggio.

**Volume** (scambi taker unici, 9/10-2/11): meteo 9,21 milioni $ in 531.214 scambi su 6.476 mercati con almeno uno
scambio (su 8.184 seguiti): mediana 347 $ per mercato, 8.370 $ per evento, 5 $ per scambio. Macro 19,66 milioni $ in
54.913 scambi su 157 mercati: mediana 1.101 $ per mercato (pochi mercati della Fed fanno quasi tutto il volume: p99 3,5
milioni $). Meteo stabile fra 305.000 e 458.000 $ al giorno.

**Premi di liquidità** (liquidità esposta = azioni entro lo spread dei premi, 4,5¢, valorizzate al capitale bloccato):

| | Mercati con premi | Premi disponibili (mediana per istante) | Liquidità esposta in quei mercati | $ al giorno per 1.000 $ esposti |
|---|---|---|---|---|
| Meteo | 3.932 su 7.026 | 4.079 $/giorno | 289.817 $ | 13,8 (p25 9,5, p75 20,5) |
| Macro | 116 su 157 | 2.298 $/giorno | 974.260 $ | 2,3 |

Per mercato la mediana è più alta (meteo 44 $ per 1.000 $ al giorno) perché molti mercati hanno pochissima liquidità
entro lo spread (26% delle fotografie meteo con premi ne ha zero). È un massimo lordo: i premi si dividono fra tutti gli
ordini che si qualificano, pesati per distanza dal prezzo medio, e chi si aggiunge abbassa il rapporto.

## Cosa resta da fare

- Decidere se approvare le regole del Test 3 e una nuova raccolta (modifica di `libri.py` e dell'automazione: da
  approvare prima).
- Capire perché dal 3/11 la lettura degli scambi non restituisce nulla, prima di qualsiasi nuova raccolta.

## File

- `analisi/polymarket_meteo_macro/test1_analisi.py` → `risultati_test1.txt`
- `analisi/polymarket_meteo_macro/verifica_ipotesi_dati.py` (workflow) → `eventi_verifica.csv.gz`;
  `verifica_ipotesi.py` → `risultati_verifica_ipotesi.txt`
- `analisi/polymarket_meteo_macro/diagnosi_eventi.py` (workflow) → `eventi_grezzi_verifica.json.gz`: diagnosi degli
  eventi scartati per il cambio di fonte
