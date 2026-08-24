# RAL → Netto 2026

Calcolatore trasparente del netto da RAL per un lavoratore dipendente privato residente a Milano, basato sulla normativa fiscale e contributiva applicabile al periodo d'imposta 2026.

## Demo online

🚀 **[Prova il calcolatore](https://ral-netto-2026-8bvjqztjgnbksya5qrem4y.streamlit.app/)**

L'applicazione è utilizzabile direttamente dal browser e non richiede l'installazione di Python o di altre dipendenze.

Il progetto può comunque essere eseguito anche in locale seguendo le istruzioni riportate più avanti.

---

## Obiettivo del progetto

Trasformare una Retribuzione Annua Lorda in uno stipendio netto sembra, a prima vista, un semplice problema aritmetico.

In realtà il risultato dipende dall'interazione tra diverse componenti fiscali e contributive:

- contributi previdenziali;
- scaglioni IRPEF;
- detrazione per lavoro dipendente;
- misure di riduzione del cuneo fiscale;
- addizionale regionale;
- addizionale comunale;
- soglie di esenzione;
- regole di precisione, troncamento e arrotondamento;
- caratteristiche personali, reddituali e contrattuali del lavoratore.

L'obiettivo del progetto è trasformare queste regole in un motore di calcolo:

- esplicito;
- verificabile;
- testabile;
- comprensibile anche nel percorso che conduce al risultato finale.

Il flusso logico può essere sintetizzato come:

**RAL → contributi → imponibile → IRPEF → detrazioni e benefici → addizionali → netto**

L'interfaccia richiede volutamente soltanto due input:

1. Retribuzione Annua Lorda;
2. numero di mensilità: 12, 13 o 14.

La progettazione è quindi partita da una domanda precisa:

> Con soli due input, qual è il perimetro più ampio che può essere modellato senza introdurre informazioni arbitrarie?

La scelta non è stata quella di eliminare automaticamente tutto ciò che richiederebbe ulteriori dati.

Quando è stato possibile definire un caso d'uso preciso e coerente, alcune variabili sono state fissate come caratteristiche del modello.

Ad esempio, la residenza fiscale è posta a Milano per tutto l'anno. Regione e Comune non diventano quindi ulteriori input dell'utente, ma le relative addizionali possono essere determinate direttamente.

Quando invece una componente dipende da informazioni individuali, contrattuali o aziendali per le quali non esiste un valore standard sufficientemente giustificabile, non viene introdotto un valore convenzionale soltanto per ampliare apparentemente la copertura del simulatore.

In sintesi:

> **Il dominio viene ristretto fino a rendere determinabili le principali regole del calcolo; ciò che rimane indeterminato non viene simulato attraverso assunzioni arbitrarie.**

---

# Perimetro del modello

Il simulatore rappresenta un caso d'uso volutamente circoscritto:

- lavoratore dipendente del settore privato;
- contratto a tempo indeterminato;
- rapporto full-time;
- rapporto di lavoro per l'intero anno;
- unico datore di lavoro;
- profilo contributivo ordinario FPLD per la quota a carico del lavoratore;
- residenza fiscale a Milano, Lombardia, per tutto l'anno;
- unico reddito derivante dal rapporto di lavoro modellato;
- nessun familiare fiscalmente a carico;
- nessuna deduzione o detrazione personale ulteriore;
- nessun regime fiscale speciale;
- RAL compresa tra €20.000 e €100.000;
- 12, 13 o 14 mensilità.

Queste condizioni non sono semplicemente impostazioni predefinite dell'interfaccia: costituiscono il **dominio esplicito del modello**.

## Perché queste assunzioni?

### Dipendente privato, tempo indeterminato, full-time e anno completo

L'obiettivo è costruire un modello deterministico utilizzando un numero minimo di input.

Rapporti part-time, apprendistato, periodi lavorati inferiori all'intero anno o categorie contrattuali particolari possono modificare la contribuzione, le detrazioni spettanti e altri elementi del calcolo.

Per supportarli correttamente sarebbe quindi necessario raccogliere ulteriori informazioni.

È stato preferito restringere il dominio piuttosto che simulare questi casi attraverso ipotesi non visibili all'utente.

---

### Unico datore di lavoro e nessun altro reddito

Diverse componenti fiscali dipendono dal reddito complessivo del contribuente.

Assumendo che il lavoratore abbia un solo datore e che il reddito modellato sia il suo unico reddito, è possibile ricondurre le principali grandezze fiscali ai dati prodotti dal motore senza dover stimare:

- altri redditi;
- conguagli tra più Certificazioni Uniche;
- rapporti di lavoro contemporanei;
- variazioni derivanti da fonti reddituali esterne.

Si tratta quindi di una scelta necessaria per rendere il problema determinabile attraverso i soli dati disponibili, non dell'affermazione che queste situazioni non possano verificarsi nella realtà.

---

### Residenza fiscale a Milano, Lombardia

Le addizionali IRPEF regionali e comunali dipendono dalla residenza fiscale.

Un calcolatore generale dovrebbe quindi chiedere all'utente almeno Regione e Comune.

In questo progetto la residenza fiscale a Milano viene invece fissata come parte del caso d'uso.

In questo modo è possibile includere realmente nel calcolo:

- l'addizionale regionale della Lombardia;
- l'addizionale comunale del Comune di Milano;
- la relativa soglia di esenzione;

senza aggiungere ulteriori input all'interfaccia.

Questo è un esempio di variabile che non viene ignorata, ma resa determinata attraverso la definizione del dominio.

---

### Nessun familiare a carico e nessuna detrazione personale particolare

Elementi come familiari fiscalmente a carico, determinate spese detraibili, oneri deducibili o altre situazioni personali non possono essere inferiti dalla RAL.

A differenza della residenza geografica, non esiste in questi casi un valore standard che possa essere assunto senza attribuire arbitrariamente al lavoratore una situazione personale che potrebbe non corrispondere alla realtà.

Per questo motivo tali componenti non vengono simulate.

---

### Profilo contributivo ordinario FPLD

Il modello utilizza come riferimento contributivo il profilo ordinario IVS del Fondo Pensioni Lavoratori Dipendenti:

- **9,19%** a carico del lavoratore;
- **1% aggiuntivo** sulla quota eccedente la prima fascia di retribuzione pensionabile prevista per il 2026.

Il 9,19% non deve essere interpretato come un'aliquota contributiva universale applicabile a qualsiasi lavoratore dipendente privato.

Possono esistere ulteriori contribuzioni legate, ad esempio:

- al settore;
- alle caratteristiche del datore di lavoro;
- a specifici fondi;
- al regime contributivo applicabile.

Queste informazioni non sono ricavabili dalla sola RAL e non esiste un'unica aliquota aggiuntiva rappresentativa dell'intero settore privato.

Per questo il modello dichiara esplicitamente il profilo contributivo assunto invece di attribuire arbitrariamente ulteriori contribuzioni.

---

### RAL minima di €20.000

Il limite inferiore di €20.000 **non rappresenta una soglia normativa, un salario minimo legale o un requisito generale del rapporto di lavoro**.

È una scelta prudenziale di perimetro.

Scendendo verso RAL sensibilmente più basse diventano più rilevanti situazioni nelle quali minimali contributivi, caratteristiche contrattuali o durata effettiva del rapporto possono assumere maggiore importanza.

Poiché il simulatore non raccoglie queste informazioni, estendere il dominio fino a livelli molto inferiori avrebbe aumentato la copertura apparente senza garantire lo stesso livello di affidabilità del modello.

È stato quindi preferito un intervallo più ristretto ma meglio definito.

---

### RAL massima di €100.000

Il limite superiore di €100.000 rappresenta anch'esso una scelta esplicita di perimetro e non una soglia normativa.

Il motore, i test automatici e le verifiche sul comportamento complessivo sono stati costruiti e validati all'interno dell'intervallo dichiarato.

Il simulatore non pretende quindi di fornire risultati per valori esterni al dominio sul quale è stato progettato e verificato.

---

### 12, 13 o 14 mensilità

La fiscalità del modello viene calcolata su base annuale.

Di conseguenza, il numero di mensilità **non modifica il netto annuale**.

Serve esclusivamente a trasformare il risultato annuale in un valore mensile medio:

```text
Netto mensile medio = Netto annuale / Numero di mensilità
```

Il valore mostrato dall'applicazione **non rappresenta quindi la simulazione puntuale dei singoli cedolini**.

Una tredicesima o una quattordicesima reale possono avere una composizione differente rispetto a quella suggerita dalla semplice divisione del netto annuale.

---

# Componenti del calcolo

Il motore include le principali componenti necessarie a trasformare la RAL nel netto annuale previsto dal modello.

| Componente | Regola modellata |
|---|---|
| Contributi previdenziali | IVS lavoratore FPLD 9,19% |
| Contributo aggiuntivo | 1% sulla quota eccedente €56.224 |
| IRPEF | 23% / 33% / 43% |
| Detrazione lavoro dipendente | Formula differenziata per fascia di reddito |
| Maggiorazione della detrazione | €65 nella fascia prevista dalla normativa |
| Riduzione del cuneo fiscale | Somma o ulteriore detrazione in funzione del reddito |
| Trattamento integrativo | Regola implementata nel motore; non produce importi positivi nel dominio ammesso con le assunzioni adottate |
| Addizionale regionale | Aliquote progressive Regione Lombardia |
| Addizionale comunale | Comune di Milano, aliquota 0,8% |
| Esenzione comunale | Reddito imponibile fino a €23.000 |
| Netto annuale | Composizione delle componenti precedenti |
| Netto mensile | Media del netto annuale su 12, 13 o 14 mensilità |

---

# Flusso di calcolo

Il motore segue una sequenza esplicita.

```text
RAL
 │
 ▼
Contributi previdenziali
 │
 ▼
Reddito imponibile
 │
 ▼
IRPEF lorda per scaglioni
 │
 ▼
Detrazione per lavoro dipendente
 │
 ▼
Riduzione del cuneo fiscale
 │
 ▼
IRPEF netta
 │
 ├───────────────┐
 ▼               ▼
Addizionale      Addizionale
Lombardia        Milano
 │               │
 └───────┬───────┘
         │
         ▼
Eventuali somme riconosciute
         │
         ▼
    NETTO ANNUO
         │
         ▼
Netto mensile medio
```

Ogni componente viene calcolata separatamente e conservata nell'oggetto risultato.

L'interfaccia può quindi mostrare non soltanto il valore finale, ma anche le grandezze che hanno contribuito a determinarlo.

---

# Architettura

Il progetto separa deliberatamente:

1. parametri e soglie normative;
2. logica di calcolo;
3. struttura del risultato;
4. interfaccia utente.

```text
regole_fiscali_2026.py
          │
          ▼
    calcolatore.py
          │
          ▼
   RisultatoCalcolo
          │
          ▼
        app.py
```

## `regole_fiscali_2026.py`

Centralizza i parametri utilizzati dal modello:

- aliquote;
- soglie;
- scaglioni;
- limiti;
- configurazione della precisione;
- dominio ammesso dal simulatore.

Le regole vengono mantenute separate dall'interfaccia e dalla maggior parte della logica applicativa.

---

## `calcolatore.py`

Contiene il calculation engine.

Le diverse componenti vengono implementate attraverso funzioni separate e testabili.

Il punto di ingresso utilizzato dall'interfaccia è:

```python
calcola_netto(ral, mensilita)
```

La funzione restituisce un oggetto `RisultatoCalcolo` contenente sia il risultato finale sia le principali componenti intermedie.

---

## `app.py`

Contiene l'interfaccia Streamlit.

La sua responsabilità è limitata a:

```text
input utente
    ↓
calcola_netto()
    ↓
RisultatoCalcolo
    ↓
formattazione
    ↓
visualizzazione
```

Una regola architetturale del progetto è che **la UI non contiene formule fiscali**.

L'interfaccia può formattare e organizzare i valori già prodotti dal motore, ma non calcola autonomamente IRPEF, contributi, detrazioni o addizionali.

---

## Perché separare regole, motore e interfaccia?

La normativa fiscale cambia nel tempo.

Inserire soglie e aliquote direttamente nei componenti grafici renderebbe difficile:

- identificare le regole utilizzate;
- testarle isolatamente;
- modificarle;
- verificare quali parti del sistema sono influenzate da un aggiornamento normativo.

La separazione riduce quindi l'accoppiamento tra normativa, calculation engine e presentazione.

Non significa che ogni futura modifica normativa possa essere gestita cambiando esclusivamente un numero: nuove regole possono richiedere anche nuova logica.

L'obiettivo è rendere esplicito **dove si trovano le responsabilità delle diverse parti del sistema**.

---

# Precisione numerica

I calcoli monetari utilizzano `Decimal` invece dei normali `float`.

La scelta evita che la rappresentazione binaria dei numeri in virgola mobile introduca errori indesiderati nelle operazioni monetarie.

Il motore distingue inoltre tra:

- precisione interna del calcolo;
- eventuali regole normative di troncamento;
- arrotondamento destinato alla presentazione.

I valori non vengono quindi arrotondati indiscriminatamente dopo ogni operazione.

Quando una formula richiede un trattamento specifico della precisione, questo viene implementato esplicitamente.

L'arrotondamento ai centesimi viene invece applicato ai valori destinati alla visualizzazione.

---

# Testing

Il calculation engine è accompagnato da una suite automatizzata di test.

La versione validata contiene:

```text
90 test automatici
100% statement coverage su calcolatore.py
100% branch coverage su calcolatore.py
```

La coverage non viene considerata, da sola, una dimostrazione della correttezza fiscale del modello.

Serve invece a verificare che i rami implementati nel calculation engine vengano effettivamente esercitati dalla suite.

## Cosa viene testato

La suite comprende test relativi a:

- validazione degli input;
- contributi previdenziali ordinari;
- soglia del contributo aggiuntivo dell'1%;
- scaglioni IRPEF;
- detrazione per lavoro dipendente;
- maggiorazione di €65;
- riduzione del cuneo fiscale;
- trattamento integrativo;
- addizionale regionale Lombardia;
- addizionale comunale Milano;
- soglia di esenzione comunale;
- precisione e arrotondamenti;
- calcoli end-to-end;
- indipendenza del netto annuale dal numero di mensilità;
- immutabilità delle strutture risultato.

Particolare attenzione è stata dedicata ai **confini delle regole**.

Quando appropriato, una soglia non viene testata con un solo valore, ma attraverso il pattern:

```text
soglia - 1
soglia
soglia + 1
```

o, quando la precisione al centesimo è rilevante:

```text
soglia - €0,01
soglia
soglia + €0,01
```

Lo scopo è verificare esplicitamente l'inclusione o l'esclusione della soglia e intercettare errori come l'utilizzo di `>` al posto di `>=`, o viceversa.

---

# Verifiche sul comportamento complessivo del modello

I test puntuali permettono di verificare che una determinata regola produca il risultato atteso per specifici valori di input.

Da soli, però, non permettono di osservare facilmente come il risultato complessivo evolva passando progressivamente da una RAL all'altra.

Per questo il calculation engine è stato verificato anche attraverso scansioni sistematiche del dominio supportato.

L'obiettivo è controllare che l'interazione tra contributi, imposte, detrazioni e addizionali produca un andamento coerente lungo l'intero intervallo e, in particolare, analizzare con maggiore precisione le zone in cui sono presenti soglie normative.

Le verifiche comprendono:

- scansioni dell'intero dominio supportato;
- confronto tra valori consecutivi del netto;
- scansioni più fini in prossimità delle principali soglie;
- controlli specifici sui punti nei quali una regola produce una variazione discreta del risultato.

## Soglia di esenzione dell'addizionale comunale di Milano

Il Comune di Milano prevede un'esenzione dall'addizionale comunale per redditi imponibili non superiori a €23.000.

La soglia rappresenta un'esenzione e non una franchigia.

Di conseguenza:

```text
reddito imponibile ≤ €23.000
→ addizionale comunale = €0
```

mentre, superata la soglia:

```text
reddito imponibile > €23.000
→ aliquota 0,8% applicata all'intera base rilevante
```

Il comportamento viene verificato esplicitamente attraverso valori immediatamente inferiori, uguali e superiori alla soglia.

Ad esempio:

```text
€22.999,99 → addizionale = €0
€23.000,00 → addizionale = €0
€23.000,01 → 0,8% applicato all'intero imponibile
```

Il test permette quindi di verificare contemporaneamente:

- il punto esatto in cui cessa l'esenzione;
- la corretta distinzione tra esenzione e franchigia;
- la base sulla quale viene applicata l'aliquota dopo il superamento della soglia.

---

## Maggiorazione di €65 della detrazione per lavoro dipendente

La normativa prevede una maggiorazione di €65 della detrazione per lavoro dipendente all'interno di uno specifico intervallo di reddito.

Superato il limite superiore previsto, la maggiorazione cessa di spettare.

La suite verifica separatamente i valori:

- immediatamente precedenti alla soglia;
- sulla soglia;
- immediatamente successivi.

In questo modo il cambiamento del risultato viene ricondotto direttamente alla regola che lo determina.

---

## Scansione complessiva

Oltre ai singoli test sui confini, il netto viene osservato al crescere progressivo della RAL.

La crescita del netto non viene imposta artificialmente come perfettamente lineare o continua.

Il controllo verifica invece che eventuali variazioni discrete siano riconducibili alle regole esplicitamente modellate.

Questo consente di analizzare non soltanto la correttezza delle singole funzioni, ma anche il comportamento che emerge dalla loro combinazione.

---

# Validazione con simulatori esterni

Dopo la validazione interna del calculation engine, i risultati sono stati confrontati con due simulatori pubblici:

- **CalcolaStipendio.app**
- **Jet HR**

I simulatori esterni non sono stati utilizzati come fonte delle regole implementate né come ground truth.

Il confronto rappresenta un ulteriore controllo sul comportamento complessivo del modello e uno strumento per individuare differenze da approfondire.

Sono state confrontate otto RAL comprese tra €20.000 e €70.000, mantenendo per quanto possibile coerenti le principali assunzioni.

| RAL | Questo motore | CalcolaStipendio.app | Δ annuo | Jet HR | Δ annuo |
|---:|---:|---:|---:|---:|---:|
| €20.000 | €17.432,53 | €17.433 | -€0,47 | €17.249 | +€183,53 |
| €25.000 | €20.569,65 | €20.570 | -€0,35 | €20.354 | +€215,65 |
| €30.000 | €23.425,48 | €23.426 | -€0,52 | €23.395 | +€30,48 |
| €35.000 | €26.032,18 | €26.032 | +€0,18 | €25.935 | +€97,18 |
| €40.000 | €27.960,17 | €27.960 | +€0,17 | €27.782 | +€178,17 |
| €56.224 | €35.707,46 | €35.707 | +€0,46 | €35.282 | +€425,46 |
| €60.000 | €37.554,66 | €37.555 | -€0,34 | €37.137 | +€417,66 |
| €70.000 | €42.446,61 | €42.447 | -€0,39 | €42.049 | +€397,61 |

## CalcolaStipendio.app

Sul campione analizzato, il confronto con CalcolaStipendio.app produce risultati sostanzialmente coincidenti.

Lo scostamento massimo osservato è inferiore a **€1 annuo**.

Questa corrispondenza rappresenta un utile controllo indipendente, ma non viene considerata di per sé una prova assoluta di correttezza.

Due modelli potrebbero infatti condividere la stessa interpretazione o la stessa assunzione.

---

## Jet HR

Il confronto con Jet HR evidenzia differenze maggiori e non uniformi lungo il dominio analizzato.

Nel campione considerato lo scostamento annuo varia da circa **€30 a €425**, con questo motore che restituisce in tutti gli otto casi un netto superiore.

La presenza di una differenza rispetto a un simulatore esterno non viene interpretata automaticamente come indicazione di errore.

Quando due risultati non coincidono, il criterio seguito è riesaminare progressivamente:

1. la fonte normativa;
2. l'assunzione utilizzata;
3. la formula implementata;
4. il relativo test;
5. la coerenza con gli altri controlli effettuati.

Il calculation engine non è stato quindi modificato con l'obiettivo di replicare artificialmente l'output di uno specifico simulatore.

L'obiettivo del confronto esterno è utilizzare le differenze come **segnali da investigare**, non eliminarle semplicemente.

---

# Strategia complessiva di validazione

Nessun singolo controllo viene considerato sufficiente, da solo, a dimostrare la correttezza del modello.

La validazione deriva dalla combinazione di:

1. fonti normative e istituzionali;
2. definizione esplicita del dominio e delle assunzioni;
3. calcoli manuali di riferimento;
4. test unitari;
5. test sui boundary;
6. test end-to-end;
7. scansioni del comportamento complessivo;
8. confronto con simulatori esterni.

---

# Fonti normative e istituzionali

Il modello è stato costruito privilegiando fonti normative e istituzionali rispetto a simulatori commerciali o articoli divulgativi.

## IRPEF

Riferimento generale:

- **D.P.R. 22 dicembre 1986, n. 917 — Testo Unico delle Imposte sui Redditi**
- art. 11 TUIR

[Normattiva — D.P.R. 917/1986](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.del.presidente.della.repubblica:1986-12-22;917)

Per il periodo d'imposta 2026:

- **Legge 30 dicembre 2025, n. 199**
- art. 1, comma 3;
- modifica dell'aliquota del secondo scaglione IRPEF dal 35% al 33%.

[Normattiva — Legge 30 dicembre 2025, n. 199](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2025-12-30;199)

Il modello applica quindi:

- 23% fino a €28.000;
- 33% oltre €28.000 e fino a €50.000;
- 43% oltre €50.000.

---

## Detrazione per lavoro dipendente

La disciplina deriva dall'art. 13 TUIR e dalle successive modifiche normative.

Tra i riferimenti utilizzati:

- **Legge 30 dicembre 2021, n. 234**
- modifiche alla struttura della detrazione per redditi di lavoro dipendente.

[Normattiva — Legge 30 dicembre 2021, n. 234](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2021-12-30;234)

L'importo previsto per il primo livello di reddito è stato successivamente portato a €1.955 dalla:

- **Legge 30 dicembre 2024, n. 207**.

[Normattiva — Legge 30 dicembre 2024, n. 207](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2024-12-30;207)

---

## Riduzione del cuneo fiscale

Riferimento:

- **Legge 30 dicembre 2024, n. 207**
- art. 1, commi relativi alla somma riconosciuta ai redditi di lavoro dipendente fino a €20.000 e all'ulteriore detrazione per i redditi superiori a €20.000 e fino a €40.000.

[Normattiva — Legge 30 dicembre 2024, n. 207](https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2024-12-30;207)

---

## Contributi previdenziali

Per il profilo contributivo ordinario FPLD:

- aliquota IVS complessiva 33%;
- 23,81% a carico del datore;
- **9,19% a carico del lavoratore**.

Riferimento:

- **INPS — Circolare n. 101 del 29 novembre 2024**

[INPS — Circolare n. 101 del 29 novembre 2024](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2024.11.circolare-numero-101-del-29-11-2024_14714.html)

Per il 2026, la prima fascia di retribuzione pensionabile è pari a:

- **€56.224 annui**;
- €4.685 mensili.

Sulla quota eccedente si applica il contributo aggiuntivo dell'1%.

Riferimento:

- **INPS — Circolare n. 6 del 30 gennaio 2026**

[INPS — Circolare n. 6 del 30 gennaio 2026](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2026.01.circolare-numero-6-del-30-01-2026_15151.html)

---

## Addizionale regionale — Lombardia

Il modello utilizza le aliquote progressive pubblicate dalla Regione Lombardia:

- 1,23% fino a €15.000;
- 1,58% oltre €15.000 e fino a €28.000;
- 1,72% oltre €28.000 e fino a €50.000;
- 1,73% oltre €50.000.

[Regione Lombardia — Addizionale regionale all'IRPEF](https://www.regione.lombardia.it/bollo-auto-e-tributi-regionali/red-addizionale-regionale-irpef)

Riferimento normativo regionale:

- art. 72, L.R. Lombardia n. 10/2003.

[Normativa Regione Lombardia](https://normelombardia.consiglio.regione.lombardia.it/)

---

## Addizionale comunale — Milano

Il Comune di Milano prevede:

- aliquota unica dello **0,8%**;
- esenzione per redditi imponibili IRPEF non superiori a **€23.000**.

[Comune di Milano — Addizionale comunale IRPEF](https://www.comune.milano.it/argomenti/tributi/addizionale-comunale-irpef)

La soglia è trattata come **esenzione e non come franchigia**.

Questo significa che, una volta superata la soglia prevista, l'aliquota viene applicata all'intera base rilevante secondo la disciplina comunale e non soltanto alla parte eccedente €23.000.

---

# Limiti del modello

Questo progetto è un **simulatore annuale**, non un motore payroll completo.

Il risultato deve quindi essere interpretato come una stima coerente con il perimetro dichiarato.

Il modello non considera, tra le altre cose:

- CCNL;
- livello di inquadramento;
- contribuzioni ulteriori specifiche del settore o del datore;
- apprendistato;
- part-time;
- rapporti di lavoro inferiori all'intero anno;
- più rapporti di lavoro;
- altri redditi;
- familiari fiscalmente a carico;
- spese personali detraibili;
- oneri deducibili;
- previdenza complementare;
- contributi sindacali;
- premi di risultato;
- bonus;
- straordinari;
- fringe benefit;
- welfare aziendale;
- rimborsi;
- regimi fiscali speciali;
- TFR;
- contribuzione a carico del datore;
- INAIL;
- costo aziendale complessivo.

## Netto mensile ≠ cedolino mensile

Il netto mensile mostrato dall'app è:

```text
netto annuale / numero di mensilità
```

Rappresenta quindi una **media informativa**.

Il progetto non cerca di simulare la sequenza reale dei singoli cedolini, che potrebbe differire per effetto di:

- conguagli;
- modalità mensili di applicazione di alcune componenti;
- tredicesima;
- quattordicesima;
- variazioni della retribuzione durante l'anno;
- eventi individuali.

---

# Struttura della repository

```text
ral-netto-2026/
│
├── app.py
├── calcolatore.py
├── regole_fiscali_2026.py
├── requirements.txt
├── README.md
│
└── tests/
    ├── conftest.py
    └── test_calcolatore.py
```

---

# Esecuzione online

L'applicazione è disponibile direttamente all'indirizzo:

**https://ral-netto-2026-8bvjqztjgnbksya5qrem4y.streamlit.app/**

Non è richiesta alcuna installazione locale.

---

# Esecuzione locale

## 1. Clonare la repository

```bash
git clone <URL_REPOSITORY>
cd ral-netto-2026
```

## 2. Installare le dipendenze

```bash
python -m pip install -r requirements.txt
```

Su Windows, se viene utilizzato Python Launcher:

```powershell
py -m pip install -r requirements.txt
```

## 3. Avviare l'app

```bash
python -m streamlit run app.py
```

oppure su Windows:

```powershell
py -m streamlit run app.py
```

Streamlit avvierà l'applicazione in locale e mostrerà nel terminale l'indirizzo da aprire nel browser.

---

# Esecuzione dei test

```bash
python -m pytest -v
```

Su Windows:

```powershell
py -m pytest -v
```

Risultato atteso sulla versione validata:

```text
90 passed
```

## Coverage

```bash
python -m pytest --cov=calcolatore --cov-branch --cov-report=term-missing
```

Risultato validato sul calculation engine:

```text
calcolatore.py
100% statement coverage
100% branch coverage
```

---

# Principi seguiti nello sviluppo

## 1. Prima la specifica, poi il codice

Le regole fiscali, il dominio e le assunzioni sono stati definiti prima dell'implementazione.

L'obiettivo è evitare che decisioni di dominio finiscano implicitamente nel codice senza essere state identificate e motivate.

---

## 2. Restringere il dominio invece di introdurre falsa precisione

Quando una variabile può essere resa determinata definendo esplicitamente il caso d'uso, viene fissata come parte del modello.

Quando invece una componente richiede informazioni che non possono essere ricavate dai dati disponibili e per le quali non esiste un'assunzione standard sufficientemente giustificabile, la componente viene dichiarata fuori dal perimetro.

---

## 3. Una fonte esterna non è automaticamente ground truth

I simulatori pubblici vengono utilizzati come benchmark di validazione, non come fonte normativa.

Una differenza rispetto a un altro strumento viene analizzata prima di decidere se modificare il calculation engine.

---

## 4. Business logic indipendente dalla UI

Il motore deve poter funzionare ed essere testato indipendentemente da Streamlit.

L'interfaccia utilizza i risultati del motore, ma non contiene la logica fiscale.

---

## 5. I confini fanno parte della funzionalità

Una regola non viene considerata verificata soltanto perché produce un risultato plausibile nel centro di uno scaglione.

Le soglie e i valori immediatamente precedenti e successivi costituiscono parte esplicita della suite di test.

---

## 6. Le assunzioni devono essere visibili

Il risultato numerico ha significato soltanto rispetto alle condizioni nelle quali è stato ottenuto.

Per questo il progetto rende espliciti:

- il profilo del lavoratore;
- il territorio;
- il profilo contributivo;
- il dominio RAL;
- le componenti escluse;
- la natura annuale della simulazione.

---

# Disclaimer

Il progetto ha finalità dimostrative e informative.

Non costituisce consulenza fiscale, previdenziale o del lavoro e non sostituisce un cedolino elaborato da un professionista o da un software payroll che disponga di tutte le informazioni individuali, contrattuali e contributive necessarie.

I risultati sono validi esclusivamente rispetto alle regole e alle assunzioni dichiarate dal modello.
