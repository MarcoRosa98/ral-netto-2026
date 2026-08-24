"""Motore di calcolo del netto da RAL — periodo d'imposta 2026.

Funzioni pure, nessuna dipendenza da Streamlit. Ogni funzione applica
un blocco del flusso: contributi → imponibile → IRPEF lorda → detrazioni
→ IRPEF netta → addizionali → netto.

Ordine del modulo:
1. dataclass dei risultati (immutabili: frozen=True + tuple, non liste)
2. helper: _tronca_rapporto (solo detrazione lavoro), per_output
3. funzioni di calcolo, nell'ordine del flusso
4. orchestratore calcola_netto (valida il perimetro del modello)
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

import regole_fiscali_2026 as regole


# ─────────────────────────────────────────────────────────────────────────
# Dataclass dei risultati
# ─────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Contributi:
    ordinario: Decimal
    aggiuntivo: Decimal
    totale: Decimal


@dataclass(frozen=True)
class DettaglioScaglione:
    limite_inferiore: Decimal
    limite_superiore: Decimal | None   # None = ultimo scaglione
    quota_imponibile: Decimal          # fetta di base che cade nello scaglione
    aliquota: Decimal
    imposta: Decimal                   # quota_imponibile × aliquota


@dataclass(frozen=True)
class IrpefLorda:
    totale: Decimal
    dettaglio: tuple[DettaglioScaglione, ...]


@dataclass(frozen=True)
class Cuneo:
    somma: Decimal        # meccanismo A: si aggiunge al netto finale
    detrazione: Decimal   # meccanismo B: riduce l'IRPEF lorda


@dataclass(frozen=True)
class AddizionaleRegionale:
    totale: Decimal
    dettaglio: tuple[DettaglioScaglione, ...]


@dataclass(frozen=True)
class RisultatoCalcolo:
    # input
    ral: Decimal
    mensilita: int
    # contributi
    contributo_ordinario: Decimal
    contributo_aggiuntivo: Decimal
    contributi_totali: Decimal
    # imponibile e IRPEF
    reddito_imponibile: Decimal
    irpef_lorda: Decimal
    dettaglio_irpef: tuple[DettaglioScaglione, ...]
    # detrazioni
    detrazione_lavoro: Decimal
    detrazione_cuneo: Decimal
    irpef_netta: Decimal
    # benefici
    somma_cuneo: Decimal
    # addizionali
    addizionale_regionale: Decimal
    dettaglio_addizionale_regionale: tuple[DettaglioScaglione, ...]
    addizionale_comunale: Decimal
    # output
    netto_annuale: Decimal
    netto_mensile: Decimal
    percentuale_netto: Decimal   # frazione (netto/RAL)


# ─────────────────────────────────────────────────────────────────────────
# Helper interni
# ─────────────────────────────────────────────────────────────────────────

def _tronca_rapporto(numeratore: Decimal, denominatore: Decimal) -> Decimal:
    """Rapporto troncato (non arrotondato) alle prime 4 cifre decimali.

    Regola prevista dalla normativa ESCLUSIVAMENTE per i rapporti della
    detrazione da lavoro dipendente (art. 13 TUIR): l'unico chiamante
    ammesso è calcola_detrazione_lavoro. Il décalage del cuneo B usa
    precisione piena perché la sua norma non prevede troncamenti.
    """
    esponente = Decimal(10) ** -regole.CIFRE_TRONCAMENTO_DETRAZIONE_LAVORO  # 0.0001
    return (numeratore / denominatore).quantize(esponente, rounding=ROUND_DOWN)


def per_output(valore: Decimal) -> Decimal:
    """Arrotonda al centesimo per la sola PRESENTAZIONE all'utente.

    ROUND_HALF_UP esplicito (scelta dichiarata nel file regole): il
    quantize senza rounding userebbe il default di contesto
    (ROUND_HALF_EVEN), una dipendenza implicita che non vogliamo.
    Il motore internamente lavora sempre a precisione piena: questa
    funzione è per la UI, mai per i calcoli intermedi.
    """
    esponente = Decimal(10) ** -regole.CIFRE_ARROTONDAMENTO_OUTPUT  # 0.01
    return valore.quantize(esponente, rounding=regole.ARROTONDAMENTO_OUTPUT)


# ─────────────────────────────────────────────────────────────────────────
# Funzioni di calcolo, nell'ordine del flusso
# ─────────────────────────────────────────────────────────────────────────

def calcola_contributi(ral: Decimal) -> Contributi:
    """Contributi previdenziali a carico del lavoratore.

    L'intera RAL costituisce imponibile previdenziale (assunzione del
    modello). Il contributo aggiuntivo dell'1% è dovuto solo sulla quota
    eccedente la soglia annua.
    """
    ordinario = ral * regole.ALIQUOTA_IVS_LAVORATORE

    eccedenza = max(Decimal("0"), ral - regole.SOGLIA_CONTRIBUTO_AGGIUNTIVO)
    aggiuntivo = eccedenza * regole.ALIQUOTA_CONTRIBUTO_AGGIUNTIVO

    return Contributi(
        ordinario=ordinario,
        aggiuntivo=aggiuntivo,
        totale=ordinario + aggiuntivo,
    )


def calcola_reddito_imponibile(ral: Decimal, contributi_totali: Decimal) -> Decimal:
    """Reddito imponibile fiscale.

    Nel perimetro del modello (nessun altro reddito, nessun onere
    deducibile) coincide con il reddito complessivo R utilizzato da
    detrazioni, cuneo fiscale e addizionali.
    """
    return ral - contributi_totali


def applica_scaglioni(
    base: Decimal,
    scaglioni: Sequence[tuple[Decimal | None, Decimal]],
) -> tuple[Decimal, tuple[DettaglioScaglione, ...]]:
    """Applica una progressione per scaglioni alla base imponibile.

    Ogni aliquota si applica solo alla quota di base compresa tra il
    limite dello scaglione precedente e il proprio. Restituisce il
    totale e il dettaglio dei soli scaglioni effettivamente incisi.
    """
    totale = Decimal("0")
    dettaglio: list[DettaglioScaglione] = []
    limite_inferiore = Decimal("0")

    for limite_superiore, aliquota in scaglioni:
        tetto = base if limite_superiore is None else min(base, limite_superiore)
        quota = tetto - limite_inferiore

        if quota <= 0:
            break  # la base non raggiunge questo scaglione

        imposta = quota * aliquota
        totale += imposta
        dettaglio.append(
            DettaglioScaglione(
                limite_inferiore=limite_inferiore,
                limite_superiore=limite_superiore,
                quota_imponibile=quota,
                aliquota=aliquota,
                imposta=imposta,
            )
        )
        limite_inferiore = limite_superiore

    return totale, tuple(dettaglio)


def calcola_irpef_lorda(reddito: Decimal) -> IrpefLorda:
    """IRPEF lorda per scaglioni progressivi 2026."""
    totale, dettaglio = applica_scaglioni(reddito, regole.SCAGLIONI_IRPEF)
    return IrpefLorda(totale=totale, dettaglio=dettaglio)


def calcola_detrazione_lavoro(reddito: Decimal) -> Decimal:
    """Detrazione per redditi di lavoro dipendente, rapporto full-year.

    I rapporti delle fasce decrescenti sono troncati a 4 decimali
    come da normativa. Correttivo di 65 € per 25.000 < R <= 35.000.
    """
    if reddito <= regole.DETRAZIONE_LAVORO_SOGLIA_1:
        detrazione = regole.DETRAZIONE_LAVORO_IMPORTO_BASE

    elif reddito <= regole.DETRAZIONE_LAVORO_SOGLIA_2:
        rapporto = _tronca_rapporto(
            regole.DETRAZIONE_LAVORO_SOGLIA_2 - reddito,
            regole.DETRAZIONE_LAVORO_SOGLIA_2 - regole.DETRAZIONE_LAVORO_SOGLIA_1,
        )
        detrazione = (
            regole.DETRAZIONE_LAVORO_IMPORTO_FISSO
            + regole.DETRAZIONE_LAVORO_IMPORTO_VARIABILE * rapporto
        )

    elif reddito <= regole.DETRAZIONE_LAVORO_SOGLIA_3:
        rapporto = _tronca_rapporto(
            regole.DETRAZIONE_LAVORO_SOGLIA_3 - reddito,
            regole.DETRAZIONE_LAVORO_SOGLIA_3 - regole.DETRAZIONE_LAVORO_SOGLIA_2,
        )
        detrazione = regole.DETRAZIONE_LAVORO_IMPORTO_FISSO * rapporto

    else:
        detrazione = Decimal("0")

    if (
        regole.DETRAZIONE_LAVORO_BONUS_SOGLIA_MIN
        < reddito
        <= regole.DETRAZIONE_LAVORO_BONUS_SOGLIA_MAX
    ):
        detrazione += regole.DETRAZIONE_LAVORO_BONUS

    return detrazione


def calcola_cuneo(reddito: Decimal) -> Cuneo:
    """Riduzione del cuneo fiscale, due meccanismi alternativi.

    A (R <= 20.000): somma riconosciuta al lavoratore, percentuale
    applicata all'INTERO reddito della fascia (non per scaglioni).
    Non riduce l'IRPEF: va aggiunta al netto finale.
    B (20.000 < R <= 40.000): ulteriore detrazione IRPEF, piena fino
    a 32.000 poi decrescente fino ad azzerarsi a 40.000.

    Il rapporto del décalage B è a PRECISIONE PIENA: la L. 207/2024
    scrive la formula senza regole di troncamento. Il troncamento a
    4 decimali appartiene solo alla detrazione da lavoro (art. 13):
    estenderlo qui "per coerenza" sarebbe un'assunzione non supportata
    dalla norma (errore individuato in revisione incrociata).
    """
    somma = Decimal("0")
    for limite_superiore, percentuale in regole.FASCE_SOMMA_CUNEO:
        if reddito <= limite_superiore:
            somma = reddito * percentuale
            break

    detrazione = Decimal("0")
    if regole.DETRAZIONE_CUNEO_SOGLIA_MIN < reddito <= regole.DETRAZIONE_CUNEO_SOGLIA_PIENA:
        detrazione = regole.DETRAZIONE_CUNEO_IMPORTO
    elif regole.DETRAZIONE_CUNEO_SOGLIA_PIENA < reddito <= regole.DETRAZIONE_CUNEO_SOGLIA_MAX:
        rapporto = (
            regole.DETRAZIONE_CUNEO_SOGLIA_MAX - reddito
        ) / (
            regole.DETRAZIONE_CUNEO_SOGLIA_MAX - regole.DETRAZIONE_CUNEO_SOGLIA_PIENA
        )
        detrazione = regole.DETRAZIONE_CUNEO_IMPORTO * rapporto

    return Cuneo(somma=somma, detrazione=detrazione)


def calcola_irpef_netta(
    irpef_lorda: Decimal,
    detrazione_lavoro: Decimal,
    detrazione_cuneo: Decimal,
) -> Decimal:
    """IRPEF netta: lorda meno detrazioni, mai negativa.

    La somma cuneo (meccanismo A) NON entra qui: non è una detrazione
    IRPEF, si aggiunge direttamente al netto finale.
    """
    detrazioni_totali = detrazione_lavoro + detrazione_cuneo
    return max(Decimal("0"), irpef_lorda - detrazioni_totali)


def calcola_addizionale_regionale(
    reddito: Decimal,
    irpef_netta: Decimal,
) -> AddizionaleRegionale:
    """Addizionale regionale Lombardia, per scaglioni progressivi.

    Dovuta solo se l'IRPEF netta è positiva: in caso di incapienza
    totale l'addizionale si azzera.
    """
    if irpef_netta <= 0:
        return AddizionaleRegionale(totale=Decimal("0"), dettaglio=())

    totale, dettaglio = applica_scaglioni(
        reddito, regole.SCAGLIONI_ADDIZIONALE_LOMBARDIA
    )
    return AddizionaleRegionale(totale=totale, dettaglio=dettaglio)


def calcola_addizionale_comunale(
    reddito: Decimal,
    irpef_netta: Decimal,
) -> Decimal:
    """Addizionale comunale Milano: aliquota unica sopra la soglia.

    La soglia è di ESENZIONE, non una franchigia: superata la soglia,
    l'aliquota si applica all'intero imponibile, non all'eccedenza.
    Dovuta solo se l'IRPEF netta è positiva.
    """
    if irpef_netta <= 0:
        return Decimal("0")
    if reddito <= regole.SOGLIA_ESENZIONE_MILANO:
        return Decimal("0")
    return reddito * regole.ALIQUOTA_ADDIZIONALE_MILANO


# ─────────────────────────────────────────────────────────────────────────
# Orchestratore
# ─────────────────────────────────────────────────────────────────────────

def calcola_netto(ral: Decimal, mensilita: int) -> RisultatoCalcolo:
    """Orchestratore: dal lordo annuo al netto, perimetro 2026.

    Applica il flusso completo della specifica. Nessuna formula
    fiscale propria: solo composizione delle funzioni del motore.

    Valida il perimetro del prototipo (RAL 20.000-100.000, mensilità
    12/13/14) e solleva ValueError fuori dominio: la validazione vive
    nel motore, non nella UI, così vale per qualsiasi chiamante.
    """
    if not regole.RAL_MIN <= ral <= regole.RAL_MAX:
        raise ValueError(
            f"RAL fuori dal perimetro del prototipo: {ral} "
            f"(ammesso da {regole.RAL_MIN} a {regole.RAL_MAX})"
        )
    if mensilita not in regole.MENSILITA_AMMESSE:
        raise ValueError(
            f"Numero di mensilità non ammesso: {mensilita} "
            f"(ammessi: {regole.MENSILITA_AMMESSE})"
        )

    contributi = calcola_contributi(ral)
    reddito = calcola_reddito_imponibile(ral, contributi.totale)
    irpef_lorda = calcola_irpef_lorda(reddito)
    detrazione_lavoro = calcola_detrazione_lavoro(reddito)
    cuneo = calcola_cuneo(reddito)
    irpef_netta = calcola_irpef_netta(
        irpef_lorda.totale, detrazione_lavoro, cuneo.detrazione
    )
    add_regionale = calcola_addizionale_regionale(reddito, irpef_netta)
    add_comunale = calcola_addizionale_comunale(reddito, irpef_netta)

    netto_annuale = (
        ral
        - contributi.totale
        - irpef_netta
        - add_regionale.totale
        - add_comunale
        + cuneo.somma
    )
    netto_mensile = netto_annuale / Decimal(mensilita)
    percentuale_netto = netto_annuale / ral

    return RisultatoCalcolo(
        ral=ral,
        mensilita=mensilita,
        contributo_ordinario=contributi.ordinario,
        contributo_aggiuntivo=contributi.aggiuntivo,
        contributi_totali=contributi.totale,
        reddito_imponibile=reddito,
        irpef_lorda=irpef_lorda.totale,
        dettaglio_irpef=irpef_lorda.dettaglio,
        detrazione_lavoro=detrazione_lavoro,
        detrazione_cuneo=cuneo.detrazione,
        irpef_netta=irpef_netta,
        somma_cuneo=cuneo.somma,
        addizionale_regionale=add_regionale.totale,
        dettaglio_addizionale_regionale=add_regionale.dettaglio,
        addizionale_comunale=add_comunale,
        netto_annuale=netto_annuale,
        netto_mensile=netto_mensile,
        percentuale_netto=percentuale_netto,
    )
