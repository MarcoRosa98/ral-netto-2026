"""Parametri normativi per il calcolo del netto da RAL — periodo d'imposta 2026.

Questo modulo contiene ESCLUSIVAMENTE parametri primitivi (soglie e aliquote).
Nessuna logica di calcolo, nessun valore matematicamente derivabile:
- i cumulati IRPEF (6.440, 13.700) sono derivati dagli scaglioni;
- i denominatori delle detrazioni (13.000, 22.000, 8.000) sono differenze tra soglie;
- la soglia di capienza del trattamento integrativo (1.880) è 1.955 - 75.
Tutti questi valori vengono calcolati in calcolatore.py.

Tutti gli importi sono Decimal dichiarati da stringa: Decimal("0.0919") è esatto,
Decimal(0.0919) erediterebbe l'errore di rappresentazione binaria del float.

Perimetro del modello (vedi README): lavoratore dipendente privato, tempo
indeterminato, anno intero, unico datore, residenza Milano (Lombardia),
nessun altro reddito, nessun carico familiare, nessuna deduzione/detrazione
aggiuntiva. Sotto queste assunzioni reddito complessivo, reddito imponibile
fiscale e reddito di lavoro dipendente coincidono: RAL - contributi_totali.
"""

from decimal import Decimal, ROUND_HALF_UP

# ── Perimetro del prototipo (vincoli di prodotto, non parametri fiscali) ──
# Il motore rifiuta input fuori da questi limiti: il perimetro vale per
# QUALSIASI chiamante (UI, API, notebook, test), non solo per Streamlit.
#
# RAL_MIN = 20.000 NON è una soglia normativa né una RAL minima legale:
# è una scelta prudenziale di product scope. Il prototipo modella un
# dipendente privato full-time, a tempo indeterminato, occupato tutto
# l'anno a Milano: RAL molto basse (10-15k) sono poco rappresentative
# di questo profilo e, scendendo, minimali contributivi e contrattuali
# diventano rilevanti senza poter essere determinati dai soli due input
# della V1. Meglio restringere il dominio che produrre falsa precisione.
RAL_MIN = Decimal("20000")
RAL_MAX = Decimal("100000")
MENSILITA_AMMESSE = (12, 13, 14)

# ── Contributi previdenziali (quota lavoratore) ──────────────────────────
# Il prototipo modella la contribuzione IVS ordinaria FPLD a carico del
# lavoratore (9,19%) e l'eventuale contributo aggiuntivo dell'1% sulla
# quota di imponibile eccedente la soglia annua.
# NON sono incluse ulteriori contribuzioni a carico del dipendente che
# dipendono da settore, caratteristiche del datore o regime contributivo
# (es. 0,30% CIGS): determinarle richiederebbe input che il prototipo
# non chiede — assunzione di modello, documentata nel README.
ALIQUOTA_IVS_LAVORATORE = Decimal("0.0919")
SOGLIA_CONTRIBUTO_AGGIUNTIVO = Decimal("56224")
ALIQUOTA_CONTRIBUTO_AGGIUNTIVO = Decimal("0.01")

# ── IRPEF: scaglioni 2026 ────────────────────────────────────────────────
# Struttura: (limite_superiore, aliquota); None = ultimo scaglione, senza
# limite. I limiti inferiori non sono memorizzati: sono il limite superiore
# dello scaglione precedente. Per il 2026 il secondo scaglione è al 33%.
SCAGLIONI_IRPEF = (
    (Decimal("28000"), Decimal("0.23")),
    (Decimal("50000"), Decimal("0.33")),
    (None,             Decimal("0.43")),
)

# ── Detrazione per lavoro dipendente ─────────────────────────────────────
# Importi base per fascia di reddito e soglie che delimitano le fasce.
# I denominatori dei rapporti (13.000 = 28.000-15.000; 22.000 = 50.000-28.000)
# sono derivabili dalle soglie e vengono calcolati nel motore.
DETRAZIONE_LAVORO_SOGLIA_1 = Decimal("15000")   # fino a qui: importo fisso
DETRAZIONE_LAVORO_SOGLIA_2 = Decimal("28000")   # fine prima fascia decrescente
DETRAZIONE_LAVORO_SOGLIA_3 = Decimal("50000")   # oltre: detrazione = 0

DETRAZIONE_LAVORO_IMPORTO_BASE = Decimal("1955")       # per R <= soglia 1
DETRAZIONE_LAVORO_IMPORTO_FISSO = Decimal("1910")      # base fasce successive
DETRAZIONE_LAVORO_IMPORTO_VARIABILE = Decimal("1190")  # quota decrescente 15k-28k

# Correttivo di 65 € per 25.000 < R <= 35.000 (min esclusa, max inclusa).
DETRAZIONE_LAVORO_BONUS = Decimal("65")
DETRAZIONE_LAVORO_BONUS_SOGLIA_MIN = Decimal("25000")  # esclusa
DETRAZIONE_LAVORO_BONUS_SOGLIA_MAX = Decimal("35000")  # inclusa

# ── Cuneo fiscale, meccanismo A: somma integrativa (R <= 20.000) ─────────
# Somma riconosciuta direttamente al lavoratore (NON riduce l'IRPEF: va
# aggiunta al netto finale).
# ATTENZIONE: la percentuale si applica all'INTERO reddito di lavoro della
# fascia di appartenenza, NON progressivamente per scaglioni. Non usare
# applica_scaglioni() su questa lista.
FASCE_SOMMA_CUNEO = (
    (Decimal("8500"),  Decimal("0.071")),
    (Decimal("15000"), Decimal("0.053")),
    (Decimal("20000"), Decimal("0.048")),
)

# ── Cuneo fiscale, meccanismo B: ulteriore detrazione IRPEF ──────────────
# Detrazione piena per 20.000 < R <= 32.000 (min esclusa), poi décalage
# lineare fino ad azzerarsi a 40.000. Il denominatore del décalage
# (8.000 = 40.000 - 32.000) è derivabile e viene calcolato nel motore.
DETRAZIONE_CUNEO_IMPORTO = Decimal("1000")
DETRAZIONE_CUNEO_SOGLIA_MIN = Decimal("20000")    # esclusa
DETRAZIONE_CUNEO_SOGLIA_PIENA = Decimal("32000")  # fino a qui importo pieno
DETRAZIONE_CUNEO_SOGLIA_MAX = Decimal("40000")    # oltre: 0

# ── Trattamento integrativo ──────────────────────────────────────────────
# Importo annuo massimo per redditi fino alla soglia, subordinato alla
# capienza: IRPEF lorda > detrazione lavoro - riduzione.
# La soglia di capienza effettiva (1.955 - 75 = 1.880) è derivata nel motore.
TRATTAMENTO_INTEGRATIVO_IMPORTO = Decimal("1200")
TRATTAMENTO_INTEGRATIVO_SOGLIA_REDDITO = Decimal("15000")
TRATTAMENTO_INTEGRATIVO_RIDUZIONE_CAPIENZA = Decimal("75")

# ── Addizionale regionale Lombardia ──────────────────────────────────────
# Scaglioni progressivi. Stessa struttura di SCAGLIONI_IRPEF: la funzione
# generica applica_scaglioni() è riusabile su questa lista.
# Dovuta solo se l'IRPEF netta è positiva.
SCAGLIONI_ADDIZIONALE_LOMBARDIA = (
    (Decimal("15000"), Decimal("0.0123")),
    (Decimal("28000"), Decimal("0.0158")),
    (Decimal("50000"), Decimal("0.0172")),
    (None,             Decimal("0.0173")),
)

# ── Addizionale comunale Milano ──────────────────────────────────────────
# Aliquota unica con soglia di ESENZIONE (non franchigia): per R <= soglia
# non è dovuto nulla; per R > soglia l'aliquota si applica all'intero
# imponibile. Dovuta solo se l'IRPEF netta è positiva.
ALIQUOTA_ADDIZIONALE_MILANO = Decimal("0.008")
SOGLIA_ESENZIONE_MILANO = Decimal("23000")

# ── Precisione ───────────────────────────────────────────────────────────
# Troncamento (non arrotondamento) a 4 cifre decimali: regola prevista
# dalla normativa ESCLUSIVAMENTE per i rapporti della detrazione da
# lavoro dipendente (art. 13 TUIR). Non è una regola generale del
# sistema fiscale: il décalage del cuneo B usa precisione piena.
CIFRE_TRONCAMENTO_DETRAZIONE_LAVORO = 4

# Arrotondamento al centesimo dei soli valori esposti all'utente
# (i calcoli intermedi mantengono la precisione piena di Decimal).
# ROUND_HALF_UP è una scelta di PRESENTAZIONE, dichiarata esplicitamente
# per non dipendere dal default di contesto di Decimal (ROUND_HALF_EVEN).
CIFRE_ARROTONDAMENTO_OUTPUT = 2
ARROTONDAMENTO_OUTPUT = ROUND_HALF_UP
