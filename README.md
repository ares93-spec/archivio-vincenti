# Archivio "copia i vincenti"

Registro quotidiano di dati pubblici e gratuiti, per verificare **più avanti** se in qualche mercato esistono partecipanti
che vincono con continuità e che si possono seguire. Oggi non produce segnali: raccoglie dati che domani non si
potrebbero più ricostruire.

> Progetto personale di ricerca. Nessun consiglio d'investimento, nessun ordine, nessun segnale operativo.

**Stato dell'ultimo giro → [STATO.md](STATO.md)** (si legge anche dall'app GitHub sul telefono).

---

## 1. Perché esiste

La ricerca iniziale (9/10/2026) ha concluso che:

- in ogni mercato studiato i bravi veri sono pochissimi (fra lo 0,6% e il 3% dei partecipanti);
- le classifiche per guadagno pescano soprattutto fortunati;
- a chi copia arriva metà del vantaggio, o meno.

Quattro direzioni meritano una verifica:

| # | Direzione | Cosa si fa qui |
|---|---|---|
| 1 | Acquisti degli insider (Form 4) su small e mid cap | **niente**: il test è già avviato altrove |
| 2 | Lato opposto della folla retail nelle opzioni | **raccolta attiva** di menzioni Reddit e catene Cboe, con le regole della sezione 3 |
| 3 | Polymarket, solo in lettura | **solo registrazione** di classifiche e pannello di wallet |
| 4 | Hyperliquid | **solo registrazione** di classifica, vault, posizioni e fill |

Le direzioni 3 e 4 non si analizzano finché la 2 non ha dato un verdetto. Si registrano da subito perché quei dati
non si recuperano a ritroso: le classifiche mostrano solo l'oggi e Hyperliquid conserva solo gli ultimi 10.000 fill per
wallet.

## 2. Cosa si registra e quando

Ogni giorno alle 21:40 UTC, cioè 23:40 italiane con l'ora legale e 22:40 con la solare, dopo la chiusura di Wall
Street. Un giro di riserva alle 23:40 UTC parte solo se il primo non è riuscito. Tutto gira su GitHub Actions senza
interventi manuali (`.github/workflows/archivio.yml`, codice in `raccolta.py`).

| Fonte | File giornalieri (`dati/<fonte>/<anno>/<data>_...csv.gz`) | Contenuto |
|---|---|---|
| ApeWisdom | `menzioni` | Tutti i titoli citati su Reddit (filtri `all-stocks` e `wallstreetbets`): menzioni, upvote, posto, menzioni e posto di 24 ore prima |
| Cboe (solo giorni feriali) | `sottostanti`, `scadenze` | Per i titoli scelti con le regole della sezione 3: prezzo, IV30, volumi e open interest totali; per ogni scadenza fino a 70 giorni: strike al denaro, IV al denaro, straddle e movimento implicito, spread al denaro, IV delle put e delle call a delta 25 |
| Polymarket | `classifiche`, `pannello` | Classifiche per P&L (giorno, settimana, mese, sempre: prime 1.000), per volume (mese: prime 500), per categoria (mese: prime 200). Pannello: P&L complessivo di ogni wallet entrato nelle classifiche mensili o storiche, registrato ogni giorno anche quando perde |
| Hyperliquid | `classifica`, `vault`, `posizioni`, `fill` | Classifica dei conti rilevanti (conto ≥ 100.000 $, oppure P&L del mese ≥ 50.000 $ in valore assoluto, oppure P&L storico ≥ 500.000 $); vault aperti con almeno 100 $ ogni giorno e tutti, chiusi compresi, il lunedì; posizioni aperte e fill delle ultime 26 ore di un pannello di circa 200-250 wallet |

Stato tecnico in `stato/`: titoli seguiti (`seguiti.json`), pannello Polymarket (`polymarket_pannello.json`), titoli
senza catena Cboe (`cboe_errori.txt`), data dell'ultimo giro riuscito.

## 3. Regole fissate il 9/10/2026, prima di vedere i dati

Non si cambiano dopo aver visto i risultati. Se un giorno andranno cambiate, la modifica si scrive qui con la data e
l'analisi riparte da quella data.

### Selezione dei titoli per la Cboe (direzione 2)

Universo: filtro ApeWisdom `all-stocks`, esclusi indici ed ETF (`ESCLUSI` in `raccolta.py`) e le sigle che su Reddit sono quasi sempre parole o gergo, come IT, DTE, API e CAN (`AMBIGUI`, aggiunta il 9/10/2026 dopo il primo giro e prima di qualsiasi analisi).

- **picco**: almeno 20 menzioni nelle 24 ore **e** almeno il triplo delle menzioni di 24 ore prima (se il dato
  precedente manca vale come zero);
- **folla**: i 25 titoli più citati;
- **controllo**: 15 titoli estratti a caso ogni giorno tra il 26° e il 500° posto, con almeno 3 menzioni e senza
  picco. L'estrazione è riproducibile perché il seme è la data.

Ogni titolo scelto viene registrato ogni giorno feriale per **35 giorni di calendario** dall'ultima scelta (circa 24
sedute), con un tetto di 260 titoli al giorno.

### Test della direzione 2 (da eseguire alle date della sezione 4)

**Evento**: un titolo che entra nel gruppo *picco* senza esserci stato nei 35 giorni precedenti. Il confronto è con i
titoli *controllo* dello stesso giorno.

**Misure**, tutte dalle fotografie serali della Cboe:

1. **M1**: movimento assoluto realizzato da t a t+5 sedute, diviso per il movimento implicito della prima scadenza con
   almeno 5 giorni di vita (straddle al denaro diviso prezzo).
2. **M2**: variazione dell'IV al denaro della scadenza tra 20 e 50 giorni, da t a t+5 e da t a t+20.
3. **M3**: rendimento del sottostante da t a t+5 e da t a t+20.

**Ipotesi**: dopo un picco di attenzione le opzioni sono care (M1 sotto 1 più che nel controllo, M2 negativo) e il
titolo tende a invertire (M3 negativo rispetto al controllo).

**Criteri di successo**, tutti richiesti:

- almeno **100 eventi** con 20 sedute di seguito: se non ci sono, il verdetto slitta;
- differenza fra picco e controllo con **lo stesso segno nella prima e nella seconda metà** degli eventi, divisi per
  data;
- **test di permutazione** (etichette mescolate tra i titoli dello stesso giorno) con p < 0,05;
- risultato riportato **con e senza** gli eventi a meno di 7 giorni dagli utili (le date degli utili si aggiungono al
  momento dell'analisi).

Se la differenza esiste, il passo dopo è una simulazione di put spread venduti sugli eventi, a carta. Non è
un'operatività.

### Direzioni 3 e 4: cosa si misurerà (non prima della data della sezione 4)

- **P&L giornaliero per wallet**: differenza tra due giorni consecutivi del P&L complessivo del pannello Polymarket e
  del P&L storico della classifica Hyperliquid.
- **Persistenza**: si classifica sulla prima metà del periodo, con una statistica t sul P&L giornaliero, e si misura
  sulla seconda metà (correlazione di rango, P&L medio del primo decile contro gli altri). Il confronto è con una
  permutazione delle etichette dei wallet.
- **Hyperliquid, profilo**: durata media delle posizioni dai fill, per distinguere i trader che tengono ore o giorni
  da quelli ad alta frequenza; persistenza dell'APR dei vault, chiusi compresi.
- **Costo del ritardo**: simulazione "copio le posizioni del giorno prima al prezzo di oggi" sulle posizioni salvate.

## 4. Calendario

| Data | Cosa |
|---|---|
| venerdì 23/10/2026 | Controllo tecnico: errori, dimensioni, tempi del giro |
| venerdì 4/12/2026 | Prima lettura della direzione 2 (circa 8 settimane), solo se ci sono almeno 100 eventi |
| venerdì 8/1/2027 | Verdetto della direzione 2 (circa 12 settimane) |
| lunedì 11/1/2027 | Prima prova di persistenza di Polymarket e Hyperliquid (3 mesi), solo se la direzione 2 ha dato un esito chiaro |
| venerdì 9/4/2027 | Verdetto di persistenza delle direzioni 3 e 4 (6 mesi) |

## 5. Limiti noti

- **Cboe**: dati ritardati di 15 minuti, letti dopo la chiusura. L'endpoint non è documentato ufficialmente e potrebbe
  cambiare.
- **ApeWisdom**: è un servizio di terzi e i criteri di conteggio non sono pubblici. Lo storico non è verificato,
  quindi si archivia da oggi in avanti.
- **Polymarket**: nei test del 9/10/2026 il filtro per categoria sembrava ignorato. Il giro lo controlla ogni sera e
  lo scrive in STATO.md se le categorie risultano identiche alla classifica generale.
- **Polymarket in Italia**: dal 2026 la piattaforma è in blacklist ADM e per l'Italia è "close-only". Qui si leggono
  solo dati pubblici, non si opera.
- **Hyperliquid**: i conti ad alta frequenza (2.000 fill o più in 26 ore) vengono contati ma non salvati: non sono il
  profilo che si può seguire.
- **Pannelli fissi**: Polymarket fino a 6.000 wallet (il primo giorno ne ha riempiti 2.500: con il vecchio tetto i nuovi vincenti dei mesi successivi sarebbero rimasti fuori), Hyperliquid circa 250. Un wallet entra nel pannello quando
  compare nelle classifiche, quindi c'è un bias verso chi ha vinto prima di entrare: va tenuto presente nell'analisi.
- **Dimensioni**: il primo giro (9/10/2026) pesava 3,5 MB; dopo gli arrotondamenti l'obiettivo è circa 2 MB al giorno. STATO.md segnala quando l'archivio supera i 700 MB (GitHub consiglia di
  restare sotto 1 GB).
- **Repository pubblico**: niente segreti, niente dati personali. Wallet e nomi utente sono già pubblici sulle fonti.

## 6. File

| File | Cosa |
|---|---|
| `raccolta.py` | Raccoglitore: una funzione per fonte, ogni fonte indipendente dalle altre |
| `.github/workflows/archivio.yml` | Orari del giro e salvataggio nel repository |
| `STATO.md` | Esito dell'ultimo giro, scritto in automatico |
| `CLAUDE.md` | Istruzioni per le sessioni di Claude su questo repository |
| `dati/` | Archivio |
| `stato/` | Liste di lavoro del raccoglitore |
