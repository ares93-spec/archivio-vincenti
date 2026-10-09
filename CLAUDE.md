# CLAUDE.md — archivio-vincenti

Istruzioni per ogni sessione su questo repository. Leggile prima di toccare qualsiasi file.

## Cos'è
Registro quotidiano di dati pubblici (ApeWisdom, Cboe, Polymarket, Hyperliquid) per un progetto personale di ricerca:
verificare se in qualche mercato esistono partecipanti che vincono con continuità e che si possono seguire. Il piano,
le regole fissate prima dei dati e il calendario sono nel `README.md`, che è il file di riferimento del progetto.

## Vincoli non negoziabili
- **Repository pubblico**: nessun segreto, nessun dato personale del proprietario (nome, professione, conti, posizioni),
  nessun riferimento ad altri repository privati. Tutto quello che entra qui lo vede chiunque.
- **Nessun ordine, nessun segnale operativo**: qui si raccolgono e si analizzano dati, non si opera.
- **Regole della sezione 3 del README**: non si cambiano dopo aver visto i dati. Una modifica va decisa esplicitamente
  dal proprietario in chat, scritta nel README con la data, e l'analisi riparte da quella data.
- **Automazione senza interventi manuali**: il workflow deve girare da solo. Se una modifica richiede un'azione del
  proprietario (un segreto, un'approvazione), dillo prima.
- **Orari**: 21:40 UTC più la riserva alle 23:40 UTC. Non spostarli senza chiedere.
- **Leggibilità dal telefono**: l'esito resta in `STATO.md`.
- **Dimensioni**: tieni l'archivio sotto 1 GB. Prima di aggiungere una fonte stima quanto pesa al giorno.

## Metodo per le analisi
1. Regola e misure scritte prima del test (README, sezione 3). Nessun ritocco dopo aver visto i risultati.
2. Confronto con un gruppo di controllo o con una permutazione: conta la differenza, non il risultato assoluto.
3. Due metà del campione separate: un effetto che cambia segno tra le due è rumore.
4. Quando si scansionano molti wallet, correggi per i test multipli (soglia t intorno a 3, oppure false discovery rate).
5. Riporta i risultati come sono, anche quando smentiscono l'idea: un test negativo è un risultato e va scritto nel README.
6. Ogni numero riportato viene da un'esecuzione, non da una stima. Double check sui calcoli.

## Convenzioni
- Italiano ovunque: commenti, testi, commit.
- Le analisi vanno in `analisi/<nome>/`, con lo script e i risultati in un `.txt` accanto, più una riga nel README.
- Dalla rete di una sessione cloud le fonti spesso non rispondono: le prove si fanno con il workflow (`push` su
  `raccolta.py` lancia un giro) o con un workflow una tantum.
