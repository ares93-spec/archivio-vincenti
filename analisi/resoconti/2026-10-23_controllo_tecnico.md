# Controllo tecnico delle prime due settimane — 23/10/2026

Periodo: giri dal 9/10 al 22/10/2026 (il giro del 23/10 parte stasera). Tutti i numeri vengono da
[`analisi/controllo_tecnico/controllo.py`](../controllo_tecnico/controllo.py), che legge solo il repository e la storia
git; l'uscita completa è in [`controllo.txt`](../controllo_tecnico/controllo.txt). Gli esiti dei workflow vengono dalle
esecuzioni di GitHub Actions.

**Esito: raccolta completa, nessun giorno mancante. Due guasti tecnici trovati e corretti, tre punti da decidere.**

## 1. Giorni registrati

| Fonte | Attesi | Registrati | Mancanti |
|---|---|---|---|
| ApeWisdom | 14 | 14 | nessuno |
| Cboe (solo giorni feriali) | 10 | 10 | nessuno; nessun file nel fine settimana |
| Polymarket | 14 | 14 | nessuno |
| Hyperliquid | 14 | 14 | nessuno |

Ogni giorno ha tutti i file della fonte (nessun file isolato). Il vault completo di Hyperliquid del lunedì si vede nel
peso (12/10 e 19/10 sono i giorni più pesanti).

## 2. Errori

- **Workflow "Archivio quotidiano"**: 31 esecuzioni, tutte riuscite. Il giro delle 21:40 UTC parte in realtà fra le
  21:52 e le 22:09 UTC; la riserva delle 23:40 UTC fra le 23:47 e le 00:00 UTC, e nei giorni normali si ferma in 20-40
  secondi come previsto.
- **STATO.md**: nessuna fonte con ❌ in nessuno dei 18 giri salvati. Polymarket lascia 2-3 wallet senza risposta su
  3.800 ogni sera (0,05-0,08%); Hyperliquid 0 errori ogni sera.
- **Commit "Archivio del ..."**: uno al giorno dal 10/10 al 22/10, con due eccezioni:
  - 9/10: 4 commit, cioè i tre giri di prova della mattina più quello della sera; i file del 9/10 sono quelli della
    sera;
  - **20/10: 2 commit, il primo alle 00:13 UTC. È il primo guasto, descritto sotto.**
- **Cboe, `stato/cboe_errori.txt`**: 15 titoli senza catena su 166 seguiti (XXII, RE, TCRT, TP, DAY, TIL, LOT, XLAB, GOAT,
  IG, JZ, LINK, OLB, SOS, UI), tutti con risposta 403. Sono sempre gli stessi titoli (IG, TIL e LINK in tutti i 18 giri,
  OLB, SOS, GOAT, JZ in 16) mentre gli altri 151 vengono letti: è il comportamento della Cboe per i simboli senza
  opzioni quotate, non un guasto dell'endpoint. Questi titoli occupano posti nei gruppi senza dare dati Cboe: va solo
  tenuto presente nell'analisi.

### Guasto 1: la riserva partita dopo mezzanotte UTC registra un giorno in più (corretto)

Il 19/10 GitHub ha avviato la riserva delle 23:40 UTC alle 00:00:03 UTC del 20/10. Il programma prendeva come data del
giro la data UTC, quindi ha visto "20/10, giro di oggi non ancora fatto" ed è partito, salvando dati della sera del
19/10 con la data del 20/10. Il giro vero del 20/10 (22:22 UTC) ha poi riscritto tutti e nove i file del 20/10, quindi
**i file dell'archivio sono corretti**. Restano due tracce:

- `stato/seguiti.json` contiene le scelte di quel giro con la data del 20/10. Rifacendo la selezione su entrambe le
  versioni del file ApeWisdom del 20/10 (quella delle 00:00 è nella storia git, commit `9f5e87f`): il giro spurio ha
  messo nel gruppo *controllo* **DAX, TP e WDC**, che il giro vero non ha scelto, e nel gruppo *picco* APLD, CRWV, ET,
  RIVN e TSLA, mentre il *picco* vero del 20/10 è HTZ, JD, NFLX, OKLO, SMCI, SPCX. DAX e TP sono entrati nei seguiti
  solo per quel giro. Non ho toccato `seguiti.json`: quei titoli costano solo qualche riga Cboe e scadono da soli.
  **Per l'analisi della direzione 2 i gruppi vanno ricostruiti dai file ApeWisdom archiviati, non da `seguiti.json`.**
- il pannello Polymarket ha ricevuto i wallet delle classifiche di quella notte: nessun effetto sulle misure.

La partenza della riserva si sta spostando in avanti (23:47-23:49 dal 9/10 al 12/10, 23:58 il 21/10 e il 22/10), quindi il guasto si
sarebbe ripetuto.

**Correzione** (`raccolta.py`, commit `86e637b`): la data del giro è ora quella della seduta di New York, calcolata
come UTC meno 5 ore. Il giro delle 21:40 UTC resta sullo stesso giorno (lo resterebbe anche se partisse fino alle 04:59 UTC); una
riserva avviata dopo mezzanotte UTC resta sul giorno della seduta e, se il giro principale è riuscito, si ferma. Una
riserva di sabato dopo mezzanotte UTC registra correttamente la Cboe del venerdì. Soglie, selezioni e orari invariati.
Verifica: calcolo della data su 7 orari di prova (21:52, 23:58, 00:00, 04:59, 05:00 UTC, sabato 00:10, lunedì 22:09) e
prova di `main --riserva` con `ultimo_giro.txt` del 22/10, che si ferma come deve. Il commit porta `[skip ci]` per non
far partire un giro di prova a metà giornata, che avrebbe riscritto `seguiti.json` con dati di metà giornata: la prima
esecuzione vera è il giro di stasera.

### Guasto 2: il registratore dei libri ordini si è fermato il 23/10 alle 05:13 UTC (corretto)

Il giro del Test 1 partito alle 00:33 UTC del 23/10 è terminato con errore alle 05:13 UTC
(`DataFrame index must be unique`): l'elenco dei mercati conteneva due volte lo stesso token, perché la paginazione
degli eventi meteo può restituire due volte lo stesso evento (per gli eventi macro c'era già il controllo dei
doppioni). I 54 giri precedenti del registratore erano riusciti. Persi circa 2 ore di fotografie: l'ultima salvata è delle
04:23 UTC, il giro successivo è partito alle 06:32 UTC.

**Correzione** (`analisi/polymarket_meteo_macro/libri.py`, commit `86e637b`): eventi meteo con lo stesso id scartati
e token doppi tolti dall'elenco. I mercati scelti restano gli stessi. Verifica in locale con un elenco finto che
ripete un evento (5 mercati unici, `to_dict` riuscito) e dal vivo con il workflow "Analisi una tantum"
([`verifica_libri.py`](../controllo_tecnico/verifica_libri.py)); esito nella sezione 6. Il giro del registratore
partito alle 06:32 UTC usa ancora il codice vecchio e può fermarsi di nuovo fino alla fine (12:12 UTC circa); dal giro
delle 12:05 UTC usa la correzione.

## 3. Peso

MB al giorno di calendario (file compressi in `dati/`):

| Fonte | Media 14 giorni | Media ultimi 7 giorni |
|---|---|---|
| ApeWisdom | 0,028 | 0,030 |
| Cboe | 0,035 | 0,039 |
| Polymarket | 0,393 | 0,403 |
| Hyperliquid | 1,572 | 1,613 |
| **Totale** | **2,028** | **2,085** |

Oggi `dati/` pesa 28,4 MB. Con il ritmo degli ultimi 7 giorni:

| Orizzonte | `dati/` | Rispetto a 700 MB |
|---|---|---|
| 6 mesi (9/4/2027, verdetto di persistenza) | 381 MB | sotto |
| 12 mesi (9/10/2027) | 762 MB | **sopra**: 700 MB intorno al 9/9/2027 |

Il peso cresce piano: Polymarket per il pannello che si allarga, Cboe per i titoli seguiti. Hyperliquid è il 77% del
totale (classifica 0,9 MB e fill 0,5-0,6 MB al giorno).

**Fuori dalla soglia di STATO.md**: il Test 1 dei libri ordini (`dati_test/`) pesa già 115,9 MB, 8,43 MB al giorno, e
arriva a circa **242 MB al 6/11**. STATO.md conta solo `dati/`, ma il limite di GitHub riguarda il repository intero,
storia compresa: il pacchetto git pesa già 156 MB. Con `dati_test/` nella storia, 1 GB di repository arriva prima dei
12 mesi.

## 4. Tempi del giro e pannelli

- **Durata**: fra 8,2 e 14,7 minuti; nei giorni feriali sale (12,4 minuti il 13/10, 14,7 il 22/10) con i titoli Cboe
  seguiti. Il limite del workflow è 45 minuti: margine ampio.
- **Polymarket**: ogni sera letti tutti i wallet del pannello meno 2-3 (3.817 su 3.819 il 22/10). Il pannello cresce di
  87,7 wallet al giorno (2.679 il 9/10 sera, 3.819 il 22/10): a questo ritmo il tetto di 6.000 arriva intorno al
  **15/11/2026**.
- **Cboe**: titoli seguiti da 78 a 166 in 13 giorni (6,8 al giorno). Se la crescita resta lineare il tetto di 260
  arriva intorno al **4/11/2026**, prima delle prime uscite per i 35 giorni (dal 13/11). Oltre il tetto il programma
  tiene i titoli scelti oggi e poi i più recenti: si perdono per primi quelli scelti da più tempo, che di solito hanno
  già passato le 20 sedute, ma va controllato.
- **Hyperliquid**: pannello di 198-205 wallet, 0 errori ogni sera.

## 5. Test Polymarket meteo e macro (`analisi/polymarket_meteo_macro/`)

- **Fotografie dei libri ordini**: 1.860 dal 9/10 13:12 al 23/10 04:23 UTC. Nei giorni interi 135-139 fotografie su
  144 attese: fra un giro di 5 ore e 40 minuti e il successivo restano buchi di 35-40 minuti, perché GitHub avvia i
  giri 20-35 minuti dopo l'orario. In totale 52 buchi oltre 15 minuti, 26,0 ore su circa 13,6 giorni (8%), tutti a
  cavallo dei cambi di giro, più il buco del guasto 2.
- **Scambi**: 68.000-92.000 al giorno, in crescita negli ultimi giorni (90.430 il 21/10, 92.165 il 22/10).
- **Mercati seguiti**: 1.014 nel giro del 23/10 (924 meteo, 90 macro), circa 900 nelle regole.
- **Errori**: solo il guasto 2. Rischio da controllare il 9/11: la lettura degli scambi prende al massimo 500 scambi
  per gruppo di 20 mercati ogni 10 minuti; il massimo visto per un solo mercato in una lettura è 326 (3 letture su
  104.618 coppie lettura-mercato sopra 250), quindi in pochi picchi un gruppo può aver superato il limite.
- **Test 2 e calibrazione**: chiusi il 9/10 (README, sezione 5). La verifica dell'ipotesi esplorativa del 9/11 usa
  eventi risolti che si leggono anche a ritroso: nessun dato da raccogliere qui.

## 6. Verifica dal vivo della correzione dei libri

Workflow "Analisi una tantum" del 23/10 (commit `b614979`, log in `analisi/ultimo_log.txt`), codice corretto,
tre letture di seguito: 338 eventi meteo letti, 0 ripetuti; 772 mercati scelti (682 meteo, 90 macro), 772 token
unici; `to_dict` riuscito ogni volta. In questo momento la fonte non restituisce doppioni, quindi la prova dal vivo
conferma che il codice corretto gira, non riproduce il guasto; il caso con i doppioni è coperto dalla prova in locale.

## Da decidere (non ho cambiato nulla)

1. **Peso del repository**: `dati_test/` (circa 242 MB al 6/11) più `dati/` porta il repository oltre 1 GB prima dei 12
   mesi. Possibilità: a fine Test 1 spostare `dati_test/` in un repository a parte o in un rilascio compresso e
   riscrivere la storia, oppure accettarlo e rivedere a 6 mesi. Va deciso prima del 6/11.
2. **Tetto di 260 titoli Cboe** (regola della sezione 3), che a questo ritmo si raggiunge intorno al 4/11: tenerlo o
   alzarlo prima che scatti. Il peso Cboe è piccolo (0,04 MB al giorno).
3. **Tetto di 6.000 wallet Polymarket**, raggiunto intorno al 15/11: dopo, i nuovi vincenti non entrano più nel
   pannello.

Inoltre, per l'analisi del 4/12: i gruppi del 20/10 vanno presi dai file ApeWisdom, non da `seguiti.json` (guasto 1).
