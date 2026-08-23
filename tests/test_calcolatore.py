"""Test del motore di calcolo — periodo d'imposta 2026.

PRINCIPI DELLA SUITE
1. Ogni valore atteso è calcolato A MANO e il conto è scritto nel
   commento del test: gli attesi non sono copiati dall'output del
   codice (test tautologici), sono verifiche indipendenti.
2. Le soglie normative si riferiscono quasi tutte al REDDITO
   IMPONIBILE, non alla RAL: i test unitari passano direttamente
   l'imponibile alle funzioni (che sono pure). L'helper
   ral_da_imponibile serve solo ai test end-to-end, dove l'unico
   input possibile è la RAL.
3. Pattern per ogni soglia: soglia-1 / soglia / soglia+1, più il
   passo da UN CENTESIMO (soglia ± 0,01) sui confini più delicati,
   perché il dominio è monetario: il primo valore oltre la soglia
   non è +1 euro, è +1 centesimo.
   Errore intercettato: un confronto > scritto come >= o viceversa.
4. Il décalage del cuneo B è a precisione PIENA (la L. 207/2024 non
   prevede troncamenti): i test lo proteggono esplicitamente da chi
   volesse reintrodurre il troncamento "per coerenza" con l'art. 13.
5. DUE LIVELLI DI DOMINIO. Il perimetro di PRODOTTO (RAL 20.000-100.000,
   imponibile minimo 18.162) è applicato solo da calcola_netto: i test
   e2e vivono lì dentro. Le funzioni pure implementano le regole su
   tutto il loro spazio, e i test UNITARI le coprono anche sotto il
   perimetro (fasce cuneo 7,1%/5,3%, trattamento integrativo, detrazione
   base 1.955, incapienza): regole corrette e protette da regressioni
   anche se oggi irraggiungibili dal prodotto — se la V2 riaprisse il
   perimetro, nulla andrebbe riscritto.
"""

from decimal import Decimal

import pytest

import regole_fiscali_2026 as regole
from calcolatore import (
    applica_scaglioni,
    calcola_addizionale_comunale,
    calcola_addizionale_regionale,
    calcola_contributi,
    calcola_cuneo,
    calcola_detrazione_lavoro,
    calcola_irpef_lorda,
    calcola_irpef_netta,
    calcola_netto,
    calcola_reddito_imponibile,
    calcola_trattamento_integrativo,
    per_output,
)

D = Decimal  # abbreviazione locale per leggibilità


# ─────────────────────────────────────────────────────────────────────────
# Helper dei test
# ─────────────────────────────────────────────────────────────────────────

def ral_da_imponibile(imponibile: Decimal) -> Decimal:
    """Inversa di calcola_reddito_imponibile, valida per RAL <= 56.224.

    imponibile = RAL x (1 - 0,0919)  →  RAL = imponibile / 0,9081

    Serve ai test end-to-end per colpire una soglia definita
    sull'imponibile partendo dalla RAL. Sopra 56.224 la formula non
    vale (contributo aggiuntivo): nessun test la usa in quel range.
    """
    return imponibile / (D("1") - regole.ALIQUOTA_IVS_LAVORATORE)


def assert_vicino(ottenuto: Decimal, atteso: Decimal, tolleranza=D("0.0001")):
    """Confronto con tolleranza per i test e2e che passano da
    ral_da_imponibile: la divisione introduce un errore ~1e-24 che
    l'uguaglianza esatta potrebbe non perdonare."""
    assert abs(ottenuto - atteso) < tolleranza, f"{ottenuto} != {atteso}"


def test_helper_ral_da_imponibile_round_trip():
    """Perché esiste: se l'helper e calcola_reddito_imponibile
    divergessero, TUTTI i test e2e sulle soglie testerebbero il punto
    sbagliato della curva senza che nessuno se ne accorga."""
    for imp in [D("18162"), D("23000"), D("35000"), D("50000")]:
        ral = ral_da_imponibile(imp)
        contributi = calcola_contributi(ral)
        assert_vicino(calcola_reddito_imponibile(ral, contributi.totale), imp)


# ─────────────────────────────────────────────────────────────────────────
# Validazione del perimetro del prototipo
# ─────────────────────────────────────────────────────────────────────────

class TestValidazioneInput:
    """Perché esiste: il motore deve conoscere il proprio perimetro
    (RAL 20.000-100.000, mensilità 12/13/14) indipendentemente dal
    chiamante. Errori intercettati: RAL negative o zero che
    produrrebbero netti nonsense o DivisionByZero; input fuori dai
    limiti dichiarati nella specifica accettati in silenzio."""

    def test_ral_minima_accettata(self):
        assert calcola_netto(D("20000"), 12).ral == D("20000")

    def test_ral_massima_accettata(self):
        assert calcola_netto(D("100000"), 12).ral == D("100000")

    def test_ral_sotto_il_minimo_rifiutata(self):
        # 19.999,99: un centesimo sotto il minimo di prodotto
        with pytest.raises(ValueError):
            calcola_netto(D("19999.99"), 12)

    def test_ral_sopra_il_massimo_rifiutata(self):
        with pytest.raises(ValueError):
            calcola_netto(D("100000.01"), 12)

    def test_ral_zero_rifiutata(self):
        # prima della validazione: DivisionByZero sulla percentuale
        with pytest.raises(ValueError):
            calcola_netto(D("0"), 12)

    def test_ral_negativa_rifiutata(self):
        # prima della validazione: produceva un "netto" negativo nonsense
        with pytest.raises(ValueError):
            calcola_netto(D("-1000"), 12)

    def test_tutte_le_mensilita_ammesse(self):
        for m in (12, 13, 14):
            assert calcola_netto(D("30000"), m).mensilita == m

    def test_mensilita_fuori_lista_rifiutate(self):
        for m in (0, 11, 15):
            with pytest.raises(ValueError):
                calcola_netto(D("30000"), m)


# ─────────────────────────────────────────────────────────────────────────
# Contributi previdenziali — soglia 56.224 (definita sulla RAL)
# ─────────────────────────────────────────────────────────────────────────

class TestContributi:
    """Unica soglia del modello definita direttamente sulla RAL.
    Errore intercettato: eccedenza calcolata con >= invece di >,
    oppure aggiuntivo applicato a tutta la RAL invece che all'eccedenza."""

    def test_sotto_soglia_nessun_aggiuntivo(self):
        # 56.223 x 0,0919 = 5.166,8937 | eccedenza 0
        c = calcola_contributi(D("56223"))
        assert c.aggiuntivo == D("0")
        assert c.totale == D("5166.8937")

    def test_soglia_esatta_nessun_aggiuntivo(self):
        # eccedenza = 56.224 - 56.224 = 0
        c = calcola_contributi(D("56224"))
        assert c.aggiuntivo == D("0")

    def test_soglia_piu_uno_aggiuntivo_su_un_euro(self):
        # eccedenza = 1 → aggiuntivo = 1 x 0,01 = 0,01
        c = calcola_contributi(D("56225"))
        assert c.aggiuntivo == D("0.01")

    def test_soglia_al_centesimo(self):
        # il primo valore sopra soglia è +1 CENTESIMO, non +1 euro:
        # eccedenza = 0,01 → aggiuntivo = 0,0001
        assert calcola_contributi(D("56223.99")).aggiuntivo == D("0")
        assert calcola_contributi(D("56224.01")).aggiuntivo == D("0.0001")

    def test_caso_manuale_ral_60000(self):
        # ordinario = 60.000 x 0,0919 = 5.514
        # eccedenza = 60.000 - 56.224 = 3.776 → aggiuntivo = 37,76
        # totale = 5.551,76
        c = calcola_contributi(D("60000"))
        assert c.ordinario == D("5514.00")
        assert c.aggiuntivo == D("37.76")
        assert c.totale == D("5551.76")


# ─────────────────────────────────────────────────────────────────────────
# applica_scaglioni — meccanica generica della progressione
# ─────────────────────────────────────────────────────────────────────────

class TestApplicaScaglioni:
    """Testata sulla lista IRPEF perché è il caso d'uso principale.
    Errori intercettati: passaggio di testimone del limite inferiore
    sbagliato, quota calcolata su tutta la base invece che sulla fetta,
    mancato break sotto soglia."""

    def test_base_zero_nessuno_scaglione(self):
        totale, dettaglio = applica_scaglioni(D("0"), regole.SCAGLIONI_IRPEF)
        assert totale == D("0")
        assert dettaglio == ()

    def test_soglia_27999_sotto_il_confine(self):
        # 27.999 x 0,23 = 6.439,77 — completa il pattern soglia-1
        totale, dettaglio = applica_scaglioni(D("27999"), regole.SCAGLIONI_IRPEF)
        assert totale == D("6439.77")
        assert len(dettaglio) == 1

    def test_soglia_28000_resta_nel_primo_scaglione(self):
        # 28.000 x 0,23 = 6.440 — qui EMERGE il 6.440 della specifica,
        # mai scritto nel file delle regole
        totale, dettaglio = applica_scaglioni(D("28000"), regole.SCAGLIONI_IRPEF)
        assert totale == D("6440")
        assert len(dettaglio) == 1

    def test_soglia_28001_apre_il_secondo_scaglione(self):
        # 6.440 + 1 x 0,33 = 6.440,33
        totale, dettaglio = applica_scaglioni(D("28001"), regole.SCAGLIONI_IRPEF)
        assert totale == D("6440.33")
        assert len(dettaglio) == 2
        assert dettaglio[1].quota_imponibile == D("1")

    def test_soglia_49999_dentro_il_secondo_scaglione(self):
        # 6.440 + 21.999 x 0,33 = 6.440 + 7.259,67 = 13.699,67
        totale, dettaglio = applica_scaglioni(D("49999"), regole.SCAGLIONI_IRPEF)
        assert totale == D("13699.67")
        assert len(dettaglio) == 2

    def test_soglia_50000_chiude_il_secondo_scaglione(self):
        # 6.440 + 22.000 x 0,33 = 6.440 + 7.260 = 13.700 (emerge il 13.700)
        totale, dettaglio = applica_scaglioni(D("50000"), regole.SCAGLIONI_IRPEF)
        assert totale == D("13700")
        assert len(dettaglio) == 2

    def test_soglia_50001_apre_il_terzo_scaglione(self):
        # 13.700 + 1 x 0,43 = 13.700,43
        totale, dettaglio = applica_scaglioni(D("50001"), regole.SCAGLIONI_IRPEF)
        assert totale == D("13700.43")
        assert len(dettaglio) == 3

    def test_dettaglio_completo_a_60000(self):
        # quote: 28.000 | 22.000 | 10.000
        # imposte: 6.440 | 7.260 | 4.300 → totale 18.000
        totale, dettaglio = applica_scaglioni(D("60000"), regole.SCAGLIONI_IRPEF)
        assert totale == D("18000")
        assert [r.quota_imponibile for r in dettaglio] == [
            D("28000"), D("22000"), D("10000")
        ]
        assert [r.imposta for r in dettaglio] == [
            D("6440"), D("7260"), D("4300")
        ]

    def test_restituisce_tuple_immutabili(self):
        """Perché esiste: frozen=True sui dataclass non basta se il
        dettaglio è una lista mutabile (r.dettaglio.clear() passava!).
        Errore intercettato: regressione da tuple a list che
        riaprirebbe la mutabilità dall'esterno."""
        _, dettaglio = applica_scaglioni(D("35000"), regole.SCAGLIONI_IRPEF)
        assert isinstance(dettaglio, tuple)


def test_irpef_lorda_delega_ad_applica_scaglioni():
    """Perché esiste: calcola_irpef_lorda è un involucro; questo test
    fissa il contratto (totale + dettaglio) senza duplicare i casi
    già coperti sopra. Errore intercettato: lista scaglioni sbagliata
    passata alla funzione generica."""
    r = calcola_irpef_lorda(D("35000"))
    # 6.440 + 7.000 x 0,33 = 6.440 + 2.310 = 8.750
    assert r.totale == D("8750")
    assert len(r.dettaglio) == 2
    assert isinstance(r.dettaglio, tuple)


# ─────────────────────────────────────────────────────────────────────────
# Detrazione lavoro dipendente — soglie 15.000/28.000/50.000, bonus 25k/35k
# ─────────────────────────────────────────────────────────────────────────

class TestDetrazioneLavoro:
    """Errori intercettati: fascia sbagliata ai confini (>= vs >),
    troncamento sostituito da arrotondamento, bonus con confini errati."""

    def test_soglia_14999_importo_fisso(self):
        assert calcola_detrazione_lavoro(D("14999")) == D("1955")

    def test_soglia_15000_importo_fisso(self):
        assert calcola_detrazione_lavoro(D("15000")) == D("1955")

    def test_soglia_15001_entra_in_fascia_decrescente(self):
        # rapporto = 12.999/13.000 = 0,99992... → troncato 0,9999
        # 1.910 + 1.190 x 0,9999 = 1.910 + 1.189,881 = 3.099,881
        assert calcola_detrazione_lavoro(D("15001")) == D("3099.881")

    def test_troncamento_non_arrotondamento(self):
        # R=20.000: rapporto = 8.000/13.000 = 0,615384... → TRONCATO 0,6153
        # (arrotondato sarebbe 0,6154 → 2.642,326: il test distingue)
        # 1.910 + 1.190 x 0,6153 = 2.642,207
        assert calcola_detrazione_lavoro(D("20000")) == D("2642.207")

    def test_bonus_soglia_24999(self):
        # rapporto = 3.001/13.000 = 0,230846... → 0,2308
        # 1.910 + 1.190 x 0,2308 = 1.910 + 274,652 = 2.184,652 — senza bonus
        assert calcola_detrazione_lavoro(D("24999")) == D("2184.652")

    def test_bonus_soglia_min_esclusa(self):
        # R=25.000: rapporto = 3.000/13.000 = 0,23076... → 0,2307
        # 1.910 + 1.190 x 0,2307 = 2.184,533 — SENZA bonus (25.000 non è > 25.000)
        assert calcola_detrazione_lavoro(D("25000")) == D("2184.533")

    def test_bonus_min_piu_uno_incluso(self):
        # R=25.001: rapporto = 2.999/13.000 = 0,23069... → 0,2306
        # 1.910 + 1.190 x 0,2306 = 2.184,414 + 65 = 2.249,414
        assert calcola_detrazione_lavoro(D("25001")) == D("2249.414")

    def test_soglia_27999_ancora_fascia_2(self):
        # rapporto = 1/13.000 = 0,0000769... → troncato 0,0000
        # 1.910 + 1.190 x 0 + 65 = 1.975 — il troncamento azzera il
        # rapporto già un euro PRIMA della soglia: comportamento
        # normativo della regola delle 4 cifre, non un bug
        assert calcola_detrazione_lavoro(D("27999")) == D("1975.0000")

    def test_cambio_fascia_a_28000(self):
        # R=28.000: fascia 2, rapporto = 0/13.000 = 0 → 1.910 + 65 = 1.975
        # (28.000 è ancora <= soglia 2, e il bonus si applica: 25k < 28k <= 35k)
        assert calcola_detrazione_lavoro(D("28000")) == D("1975.0000")

    def test_cambio_fascia_a_28001(self):
        # R=28.001: fascia 3, rapporto = 21.999/22.000 = 0,99995... → 0,9999
        # 1.910 x 0,9999 = 1.909,809 + 65 = 1.974,809
        assert calcola_detrazione_lavoro(D("28001")) == D("1974.809")

    def test_bonus_soglia_34999(self):
        # rapporto = 15.001/22.000 = 0,681863... → 0,6818 (stesso
        # troncamento di 35.000: la granularità delle 4 cifre rende
        # uguali i due valori) → 1.302,238 + 65 = 1.367,238
        assert calcola_detrazione_lavoro(D("34999")) == D("1367.238")

    def test_bonus_soglia_max_inclusa(self):
        # R=35.000: rapporto = 15.000/22.000 = 0,68181... → 0,6818
        # 1.910 x 0,6818 = 1.302,238 + 65 = 1.367,238
        assert calcola_detrazione_lavoro(D("35000")) == D("1367.238")

    def test_bonus_max_piu_uno_escluso(self):
        # R=35.001: rapporto = 14.999/22.000 = 0,68177... → 0,6817
        # 1.910 x 0,6817 = 1.302,047 — senza bonus
        assert calcola_detrazione_lavoro(D("35001")) == D("1302.047")

    def test_soglia_49999_troncamento_azzera(self):
        # rapporto = 1/22.000 = 0,0000454... → troncato 0,0000 → 0
        # (stessa dinamica di 27.999: la detrazione muore un euro prima)
        assert calcola_detrazione_lavoro(D("49999")) == D("0.0000")

    def test_soglia_50000_rapporto_zero(self):
        # rapporto = 0/22.000 = 0 → detrazione 0 (via formula, non via else)
        assert calcola_detrazione_lavoro(D("50000")) == D("0.0000")

    def test_oltre_50000_zero(self):
        # ramo else esplicito
        assert calcola_detrazione_lavoro(D("50001")) == D("0")


# ─────────────────────────────────────────────────────────────────────────
# Cuneo fiscale — fasce A: 8.500/15.000/20.000; B: 32.000/40.000
# ─────────────────────────────────────────────────────────────────────────

class TestCuneo:
    """Errori intercettati: percentuale A applicata per scaglioni invece
    che sull'intero reddito; sovrapposizione dei meccanismi A e B (devono
    essere mutuamente esclusivi); confini del décalage B; reintroduzione
    del troncamento nel décalage (la norma non lo prevede)."""

    def test_fascia_71_a_8499(self):
        # 8.499 x 0,071 = 603,429
        c = calcola_cuneo(D("8499"))
        assert c.somma == D("603.429")

    def test_fascia_71_soglia_esatta(self):
        # 8.500 x 0,071 = 603,50
        c = calcola_cuneo(D("8500"))
        assert c.somma == D("603.500")
        assert c.detrazione == D("0")

    def test_salto_a_8501(self):
        # 8.501 x 0,053 = 450,553 — aliquota su TUTTO il reddito:
        # la discontinuità di -152,947 è normativa, non un bug
        c = calcola_cuneo(D("8501"))
        assert c.somma == D("450.553")

    def test_fascia_53_a_14999(self):
        # 14.999 x 0,053 = 794,947
        assert calcola_cuneo(D("14999")).somma == D("794.947")

    def test_fascia_53_soglia_15000(self):
        # 15.000 x 0,053 = 795
        assert calcola_cuneo(D("15000")).somma == D("795.000")

    def test_fascia_48_soglia_15001(self):
        # 15.001 x 0,048 = 720,048
        c = calcola_cuneo(D("15001"))
        assert c.somma == D("720.048")

    def test_fascia_48_a_19999(self):
        # 19.999 x 0,048 = 959,952
        assert calcola_cuneo(D("19999")).somma == D("959.952")

    def test_ultima_fascia_a_20000(self):
        # 20.000 x 0,048 = 960; B non attivo (20.000 non è > 20.000)
        c = calcola_cuneo(D("20000"))
        assert c.somma == D("960.000")
        assert c.detrazione == D("0")

    def test_passaggio_a_b_al_centesimo(self):
        # il confine A/B al centesimo: 19.999,99 è ancora fascia A,
        # 20.000,01 è già detrazione B piena
        prima = calcola_cuneo(D("19999.99"))
        dopo = calcola_cuneo(D("20000.01"))
        assert prima.somma == D("959.99952")
        assert prima.detrazione == D("0")
        assert dopo.somma == D("0")
        assert dopo.detrazione == D("1000")

    def test_passaggio_a_b_a_20001(self):
        # A: nessuna fascia matcha → 0; B: detrazione piena 1.000
        c = calcola_cuneo(D("20001"))
        assert c.somma == D("0")
        assert c.detrazione == D("1000")

    def test_b_piena_a_31999(self):
        assert calcola_cuneo(D("31999")).detrazione == D("1000")

    def test_b_piena_fino_a_32000(self):
        c = calcola_cuneo(D("32000"))
        assert c.detrazione == D("1000")

    def test_decalage_a_32001_precisione_piena(self):
        # rapporto = 7.999/8.000 = 0,999875 ESATTO (denominatore 8.000
        # = 2^6 x 5^3: la divisione termina) → 1.000 x 0,999875 = 999,875
        # NON 999,80: il troncamento a 4 cifre appartiene all'art. 13,
        # la L. 207/2024 non lo prevede per il décalage del cuneo.
        # Questo test protegge la correzione emersa in revisione.
        c = calcola_cuneo(D("32001"))
        assert c.detrazione == D("999.875")

    def test_decalage_a_39999(self):
        # rapporto = 1/8.000 = 0,000125 esatto → 1.000 x 0,000125 = 0,125
        # (con il vecchio troncamento sarebbe stato 0,0001 → 0,10)
        assert calcola_cuneo(D("39999")).detrazione == D("0.125")

    def test_decalage_azzerato_a_40000(self):
        # rapporto = 0/8.000 = 0 (via formula)
        c = calcola_cuneo(D("40000"))
        assert c.detrazione == D("0")

    def test_fuori_da_tutto_a_40001(self):
        c = calcola_cuneo(D("40001"))
        assert c.somma == D("0")
        assert c.detrazione == D("0")

    def test_mai_entrambe_le_componenti(self):
        """I meccanismi sono alternativi per costruzione normativa:
        se un refactoring li facesse coesistere, il netto verrebbe
        gonfiato due volte."""
        for r in ["5000", "12000", "18000", "25000", "36000", "50000"]:
            c = calcola_cuneo(D(r))
            assert c.somma == 0 or c.detrazione == 0


# ─────────────────────────────────────────────────────────────────────────
# IRPEF netta — incapienza
# ─────────────────────────────────────────────────────────────────────────

class TestIrpefNetta:
    """Errore intercettato: rimozione del max(0, ...) — un'IRPEF
    negativa finirebbe SOMMATA al netto come credito inesistente."""

    def test_caso_pieno(self):
        # 6.265,89 - (2.044,258 + 1.000) = 3.221,632
        assert calcola_irpef_netta(
            D("6265.89"), D("2044.258"), D("1000")
        ) == D("3221.632")

    def test_incapienza_azzera(self):
        # 1.840 - 1.955 = -115 → max() → 0
        assert calcola_irpef_netta(D("1840"), D("1955"), D("0")) == D("0")

    def test_pareggio_esatto(self):
        assert calcola_irpef_netta(D("1955"), D("1955"), D("0")) == D("0")


# ─────────────────────────────────────────────────────────────────────────
# Trattamento integrativo — capienza 1.880 (derivata), soglia 15.000
# ─────────────────────────────────────────────────────────────────────────

class TestTrattamentoIntegrativo:
    """Errori intercettati: capienza testata sulla netta invece che
    sulla lorda; confine > scritto come >= sulla soglia di capienza;
    soglia reddito con confine sbagliato."""

    def test_sotto_capienza(self):
        # lorda 1.840 <= 1.880 (= 1.955 - 75, derivata) → 0
        assert calcola_trattamento_integrativo(D("8000"), D("1840")) == D("0")

    def test_capienza_esatta_non_spetta(self):
        # lorda ESATTAMENTE 1.880: la norma chiede >, non >=
        assert calcola_trattamento_integrativo(D("8174"), D("1880")) == D("0")

    def test_appena_sopra_capienza_spetta(self):
        # lorda 1.880,02 > 1.880 → 1.200
        assert calcola_trattamento_integrativo(D("8174"), D("1880.02")) == D("1200")

    def test_soglia_reddito_14999(self):
        # lorda coerente: 14.999 x 0,23 = 3.449,77 > 1.880 → spetta
        assert calcola_trattamento_integrativo(D("14999"), D("3449.77")) == D("1200")

    def test_soglia_reddito_inclusa(self):
        # R = 15.000 esatto, lorda 3.450 > 1.880 → spetta
        assert calcola_trattamento_integrativo(D("15000"), D("3450")) == D("1200")

    def test_oltre_soglia_reddito_zero(self):
        # regola del MODELLO (non della normativa generale): vedi README
        assert calcola_trattamento_integrativo(D("15001"), D("3450.23")) == D("0")


def test_semplificazione_ti_giustificata_su_tutta_la_fascia_15_28k():
    """Perché esiste: il modello impone TI = 0 per R > 15.000 sulla base
    di una PROPRIETÀ, non di una regola normativa: nella fascia
    15.001-28.000 la sola detrazione da lavoro (unica ammessa dalle
    assunzioni) non supera mai l'IRPEF lorda, quindi la condizione di
    incapienza della normativa generale non si verifica mai.

    Questo test DIMOSTRA la proprietà scandagliando tutta la fascia.
    Errore intercettato: se in futuro cambiassero scaglioni IRPEF o
    parametri della detrazione rendendo la proprietà falsa, questo
    test fallirebbe segnalando che la semplificazione non è più
    giustificata (e va rivisto calcola_trattamento_integrativo).

    Margine minimo verificato: ~350 euro subito sopra 15.000.
    """
    margine_minimo = None
    r = D("15001")
    while r <= D("28000"):
        lorda = calcola_irpef_lorda(r).totale
        detrazione = calcola_detrazione_lavoro(r)
        margine = lorda - detrazione
        assert margine > 0, (
            f"A R={r} la detrazione lavoro ({detrazione}) supera l'IRPEF "
            f"lorda ({lorda}): la semplificazione TI=0 per R>15.000 "
            f"non è più giustificata dalle assunzioni del modello"
        )
        if margine_minimo is None or margine < margine_minimo:
            margine_minimo = margine
        r += D("1")

    # il punto più stretto è subito sopra 15.000: ~350,35 di capienza
    assert margine_minimo > D("350")


# ─────────────────────────────────────────────────────────────────────────
# Addizionale regionale Lombardia — soglie 15.000/28.000/50.000
# ─────────────────────────────────────────────────────────────────────────

class TestAddizionaleRegionale:
    """Errori intercettati: guardia sull'IRPEF netta mancante; scaglioni
    regionali confusi con quelli IRPEF (le soglie coincidono in parte!)."""

    def test_azzerata_se_irpef_netta_zero(self):
        a = calcola_addizionale_regionale(D("27243"), D("0"))
        assert a.totale == D("0")
        assert a.dettaglio == ()

    def test_soglia_14999(self):
        # 14.999 x 0,0123 = 184,4877
        a = calcola_addizionale_regionale(D("14999"), D("100"))
        assert a.totale == D("184.4877")
        assert len(a.dettaglio) == 1

    def test_soglia_15000_solo_primo_scaglione(self):
        # 15.000 x 0,0123 = 184,50
        a = calcola_addizionale_regionale(D("15000"), D("100"))
        assert a.totale == D("184.500")
        assert len(a.dettaglio) == 1

    def test_soglia_15001_apre_secondo_scaglione(self):
        # 184,50 + 1 x 0,0158 = 184,5158
        a = calcola_addizionale_regionale(D("15001"), D("100"))
        assert a.totale == D("184.5158")
        assert len(a.dettaglio) == 2

    def test_confine_28000(self):
        # 27.999: 184,50 + 12.999 x 0,0158 = 184,50 + 205,3842 = 389,8842
        # 28.000: 184,50 + 13.000 x 0,0158 = 184,50 + 205,40 = 389,90
        # 28.001: 389,90 + 1 x 0,0172 = 389,9172
        assert calcola_addizionale_regionale(D("27999"), D("1")).totale == D("389.8842")
        assert calcola_addizionale_regionale(D("28000"), D("1")).totale == D("389.900")
        a = calcola_addizionale_regionale(D("28001"), D("1"))
        assert a.totale == D("389.9172")
        assert len(a.dettaglio) == 3

    def test_confine_50000(self):
        # 49.999: 389,90 + 21.999 x 0,0172 = 389,90 + 378,3828 = 768,2828
        # 50.000: 389,90 + 22.000 x 0,0172 = 389,90 + 378,40 = 768,30
        # 50.001: 768,30 + 1 x 0,0173 = 768,3173
        assert calcola_addizionale_regionale(D("49999"), D("1")).totale == D("768.2828")
        assert calcola_addizionale_regionale(D("50000"), D("1")).totale == D("768.300")
        a = calcola_addizionale_regionale(D("50001"), D("1"))
        assert a.totale == D("768.3173")
        assert len(a.dettaglio) == 4

    def test_tutti_gli_scaglioni_a_60000(self):
        # 15.000x0,0123 + 13.000x0,0158 + 22.000x0,0172 + 10.000x0,0173
        # = 184,50 + 205,40 + 378,40 + 173,00 = 941,30
        # (verificata due volte in colonna: 184,50+205,40=389,90;
        #  +378,40=768,30; +173,00=941,30)
        a = calcola_addizionale_regionale(D("60000"), D("100"))
        assert a.totale == D("941.300")
        assert len(a.dettaglio) == 4


# ─────────────────────────────────────────────────────────────────────────
# Addizionale comunale Milano — soglia di ESENZIONE 23.000
# ─────────────────────────────────────────────────────────────────────────

class TestAddizionaleComunale:
    """Errore intercettato: soglia trattata come franchigia (0,8% sulla
    sola eccedenza) invece che come esenzione (0,8% su tutto)."""

    def test_azzerata_se_irpef_netta_zero(self):
        assert calcola_addizionale_comunale(D("27243"), D("0")) == D("0")

    def test_soglia_22999_esente(self):
        assert calcola_addizionale_comunale(D("22999"), D("100")) == D("0")

    def test_soglia_esatta_esente(self):
        assert calcola_addizionale_comunale(D("23000"), D("100")) == D("0")

    def test_soglia_piu_uno_su_tutto_l_imponibile(self):
        # 23.001 x 0,008 = 184,008 — NON 1 x 0,008 = 0,008:
        # è il test che distingue esenzione da franchigia
        assert calcola_addizionale_comunale(D("23001"), D("100")) == D("184.008")

    def test_soglia_al_centesimo(self):
        # 22.999,99 → esente; 23.000,01 x 0,008 = 184,00008 su tutto:
        # un centesimo di reddito in più costa ~184 euro di addizionale
        assert calcola_addizionale_comunale(D("22999.99"), D("100")) == D("0")
        assert calcola_addizionale_comunale(D("23000.01"), D("100")) == D("184.00008")


# ─────────────────────────────────────────────────────────────────────────
# Arrotondamento di presentazione
# ─────────────────────────────────────────────────────────────────────────

class TestPerOutput:
    """Perché esiste: la regola di arrotondamento dell'output è una
    SCELTA dichiarata (ROUND_HALF_UP), non il default di contesto di
    Decimal (ROUND_HALF_EVEN). Errore intercettato: un quantize senza
    rounding esplicito che tornasse silenziosamente al default."""

    def test_arrotonda_al_centesimo(self):
        assert per_output(D("23425.4846")) == D("23425.48")

    def test_half_up_non_half_even(self):
        # 2,675 → HALF_UP dà 2,68; 2,685 → HALF_UP dà 2,69
        # (HALF_EVEN darebbe 2,68 in ENTRAMBI i casi: il secondo
        # assert distingue le due regole)
        assert per_output(D("2.675")) == D("2.68")
        assert per_output(D("2.685")) == D("2.69")


# ─────────────────────────────────────────────────────────────────────────
# End-to-end — calcoli manuali di riferimento completi
# ─────────────────────────────────────────────────────────────────────────

class TestEndToEnd:
    """Ogni caso è stato calcolato interamente a mano componente per
    componente (i conti sono nei commenti). Errore intercettato:
    qualunque regressione nella COMPOSIZIONE delle funzioni, anche se
    ogni funzione singolarmente resta corretta (es. segno sbagliato
    nella formula finale, componente dimenticata o contata due volte)."""

    def test_ral_30000_caso_di_riferimento(self):
        # contributi = 30.000 x 0,0919 = 2.757 | imponibile = 27.243
        # IRPEF lorda = 27.243 x 0,23 = 6.265,89 (primo scaglione)
        # detr. lavoro = 1.910 + 1.190 x 0,0582 + 65 = 2.044,258
        #   (rapporto 757/13.000 = 0,05823... → troncato 0,0582)
        # detr. cuneo B = 1.000 (20k < 27.243 <= 32k)
        # IRPEF netta = 6.265,89 - 3.044,258 = 3.221,632
        # TI = 0 | somma cuneo = 0
        # regionale = 184,50 + 12.243 x 0,0158 = 377,9394
        # comunale = 27.243 x 0,008 = 217,944
        # netto = 30.000 - 2.757 - 3.221,632 - 377,9394 - 217,944
        #       = 23.425,4846
        r = calcola_netto(D("30000"), 13)
        assert r.contributi_totali == D("2757.00")
        assert r.reddito_imponibile == D("27243.00")
        assert r.irpef_lorda == D("6265.8900")
        assert r.detrazione_lavoro == D("2044.2580")
        assert r.detrazione_cuneo == D("1000")
        assert r.irpef_netta == D("3221.632")
        assert r.trattamento_integrativo == D("0")
        assert r.somma_cuneo == D("0")
        assert r.addizionale_regionale == D("377.9394")
        assert r.addizionale_comunale == D("217.944")
        assert r.netto_annuale == D("23425.4846")
        # mensile = 23.425,4846 / 13 = 1.801,9603538... → UI: 1.801,96
        assert per_output(r.netto_mensile) == D("1801.96")

    def test_ral_60000_attiva_contributo_aggiuntivo(self):
        # contributi = 5.514 + 37,76 = 5.551,76 | imponibile = 54.448,24
        # IRPEF lorda = 13.700 + 4.448,24 x 0,43 = 15.612,7432
        # detr. lavoro = 0 (R > 50.000) | cuneo = 0/0 | TI = 0
        # IRPEF netta = 15.612,7432
        # regionale = 184,50 + 205,40 + 378,40 + 4.448,24 x 0,0173
        #           = 768,30 + 76,954552 = 845,254552
        # comunale = 54.448,24 x 0,008 = 435,58592
        # netto = 60.000 - 5.551,76 - 15.612,7432 - 845,254552 - 435,58592
        #       = 37.554,656328
        # mensile x14 = 2.682,475452 → UI: 2.682,48
        r = calcola_netto(D("60000"), 14)
        assert r.contributo_aggiuntivo == D("37.76")
        assert r.detrazione_lavoro == D("0")
        assert r.irpef_netta == D("15612.7432")
        assert r.netto_annuale == D("37554.656328")
        assert per_output(r.netto_mensile) == D("2682.48")

    def test_ral_20000_minimo_del_dominio(self):
        # contributi = 20.000 x 0,0919 = 1.838 | imponibile = 18.162
        # IRPEF lorda = 18.162 x 0,23 = 4.177,26 (primo scaglione)
        # detr. lavoro: rapporto = (28.000-18.162)/13.000 = 9.838/13.000
        #   = 0,75676... → troncato 0,7567
        #   → 1.910 + 1.190 x 0,7567 = 1.910 + 900,473 = 2.810,473
        #   (nessun bonus: 18.162 <= 25.000)
        # cuneo: fascia A 4,8% (15.000 < R <= 20.000, l'UNICA fascia A
        #   raggiungibile nel dominio) → somma = 18.162 x 0,048 = 871,776
        #   detrazione B = 0 (serve R > 20.000)
        # IRPEF netta = 4.177,26 - 2.810,473 = 1.366,787
        # TI = 0 (R > 15.000: nel dominio 20k-100k è SEMPRE 0)
        # regionale = 184,50 + 3.162 x 0,0158 = 184,50 + 49,9596 = 234,4596
        # comunale = 0 (18.162 <= 23.000)
        # netto = 20.000 - 1.838 - 1.366,787 - 234,4596 + 871,776
        #       = 17.432,5294 (87,16% della RAL)
        # mensile = 17.432,5294 / 13 = 1.340,9638 → UI: 1.340,96
        r = calcola_netto(D("20000"), 13)
        assert r.contributi_totali == D("1838.00")
        assert r.reddito_imponibile == D("18162.00")
        assert r.irpef_lorda == D("4177.26")
        assert r.detrazione_lavoro == D("2810.473")
        assert r.somma_cuneo == D("871.776")
        assert r.detrazione_cuneo == D("0")
        assert r.irpef_netta == D("1366.787")
        assert r.trattamento_integrativo == D("0")
        assert r.addizionale_regionale == D("234.4596")
        assert r.addizionale_comunale == D("0")
        assert r.netto_annuale == D("17432.5294")
        assert r.percentuale_netto < 1
        assert per_output(r.netto_mensile) == D("1340.96")

    def test_mensilita_non_tocca_il_calcolo_fiscale(self):
        """La mensilità deve influire SOLO sulla divisione finale."""
        r12 = calcola_netto(D("30000"), 12)
        r14 = calcola_netto(D("30000"), 14)
        assert r12.netto_annuale == r14.netto_annuale
        assert r12.irpef_netta == r14.irpef_netta
        assert_vicino(r12.netto_mensile * 12, r14.netto_mensile * 14)

    def test_cliff_addizionale_milano_end_to_end(self):
        """La discontinuità a imponibile 23.000 attraverso TUTTO il
        motore: superata la soglia di ESENZIONE, lo 0,8% colpisce
        l'intero imponibile (~184 euro di colpo). È il cliff più
        rilevante rimasto nel dominio 20k-100k (quello del trattamento
        integrativo a 15.000 è sotto il minimo di prodotto). Errore
        intercettato: qualunque modifica che 'lisci' artificialmente
        una discontinuità normativa."""
        prima = calcola_netto(ral_da_imponibile(D("22999")), 12)
        dopo = calcola_netto(ral_da_imponibile(D("23001")), 12)
        assert prima.addizionale_comunale == D("0")
        assert dopo.addizionale_comunale > D("180")
        assert dopo.netto_annuale < prima.netto_annuale

    def test_risultato_realmente_immutabile(self):
        """frozen=True + tuple: né i campi né i dettagli devono essere
        modificabili dall'esterno (r.dettaglio_irpef.clear() passava
        quando i dettagli erano liste)."""
        r = calcola_netto(D("30000"), 13)
        with pytest.raises(Exception):
            r.netto_annuale = D("0")
        assert isinstance(r.dettaglio_irpef, tuple)
        assert isinstance(r.dettaglio_addizionale_regionale, tuple)
        assert not hasattr(r.dettaglio_irpef, "clear")


# ─────────────────────────────────────────────────────────────────────────
# Monotonia — scansione del netto al crescere della RAL
# ─────────────────────────────────────────────────────────────────────────

# Discontinuità NORMATIVE attese in cui il netto può scendere,
# espresse in termini di reddito IMPONIBILE (la variabile giusta):
#   23.000 → esenzione addizionale comunale Milano (0,8% su tutto)
#   35.000 → perdita del bonus 65 € della detrazione lavoro
# FUORI dal dominio di prodotto (a RAL 20.000 l'imponibile è già 18.162):
#   8.174 (capienza TI), 8.500 e 15.000 (fasce cuneo A), 15.000 (perdita
#   trattamento integrativo). Se la V2 abbassasse RAL_MIN, la soglia
#   15.000 andrebbe REINSERITA qui.
DISCONTINUITA_ATTESE = [D("23000"), D("35000")]


# Il troncamento a 4 cifre dell'art. 13 rende la detrazione lavoro una
# funzione A GRADINI: scende di IMPORTO x 0,0001 ogni volta che il
# rapporto attraversa un multiplo di 0,0001 (~ogni 1,3 € di reddito in
# fascia 2, ~2,2 € in fascia 3). Sono micro-discontinuità NORMATIVE,
# invisibili a passo 100 €, che la scansione a centesimi rileva: il
# calo massimo di un singolo gradino è 1.910 x 0,0001 = 0,191 €.
MICRO_CALO_TRONCAMENTO = (
    regole.DETRAZIONE_LAVORO_IMPORTO_FISSO * Decimal("0.0001")
)


def _verifica_monotonia(
    ral_iniziale: Decimal,
    ral_finale: Decimal,
    passo: Decimal,
    tolleranza_micro: Decimal = Decimal("0"),
):
    """Scansiona il netto al crescere della RAL: ogni calo è ammesso
    solo se l'intervallo di imponibile attraversato contiene una
    discontinuità normativa nota, oppure se rientra nella tolleranza
    per i gradini del troncamento (usata solo dalla scansione fine)."""
    ral = ral_iniziale
    precedente = calcola_netto(ral, 12)

    while ral < ral_finale:
        ral_successiva = ral + passo
        corrente = calcola_netto(ral_successiva, 12)

        calo = precedente.netto_annuale - corrente.netto_annuale
        if calo > tolleranza_micro:
            # tutte le soglie in whitelist sono INCLUSIVE (beneficio per
            # R <= soglia, perso per R > soglia): il calo avviene passando
            # da <= soglia a > soglia, quindi la condizione è
            # precedente <= soglia < corrente (non < soglia <=: con un
            # campione ESATTAMENTE sulla soglia il calo verrebbe rifiutato)
            attraversa_soglia_nota = any(
                precedente.reddito_imponibile <= soglia < corrente.reddito_imponibile
                for soglia in DISCONTINUITA_ATTESE
            )
            assert attraversa_soglia_nota, (
                f"Calo del netto NON previsto tra RAL {ral} e {ral_successiva}: "
                f"{precedente.netto_annuale} → {corrente.netto_annuale} "
                f"(imponibile {precedente.reddito_imponibile} → "
                f"{corrente.reddito_imponibile})"
            )

        precedente = corrente
        ral = ral_successiva


def test_netto_monotono_salvo_discontinuita_normative():
    """Perché esiste: rete di sicurezza GLOBALE. Ogni calo del netto
    al crescere della RAL deve corrispondere a una discontinuità
    normativa nota. Errore intercettato: qualunque bug di composizione
    che crei un calo NON previsto (es. somma cuneo sottratta per
    errore). Al contempo NON pretende monotonia assoluta: le
    discontinuità di legge non vanno 'corrette' (requisito esplicito
    della specifica)."""
    _verifica_monotonia(D("20000"), D("100000"), D("100"))


def test_monotonia_fine_intorno_alle_soglie():
    """Perché esiste: il passo da 100 euro della scansione globale
    potrebbe non vedere un'anomalia stretta (calo e recupero dentro
    lo stesso passo). Intorno a ogni discontinuità nota scansioniamo
    a passi di UN CENTESIMO (±2 euro di RAL): copertura globale a
    maglia larga + microscopia locale sui punti critici.

    La tolleranza MICRO_CALO_TRONCAMENTO ammette i gradini del
    troncamento art. 13 (max 0,191 €), scoperti proprio da questa
    scansione: sono normativi, non bug. Qualunque calo PIÙ GRANDE
    fuori whitelist resta un errore."""
    for soglia in DISCONTINUITA_ATTESE:
        centro = ral_da_imponibile(soglia)
        _verifica_monotonia(
            centro - D("2"), centro + D("2"), D("0.01"),
            tolleranza_micro=MICRO_CALO_TRONCAMENTO,
        )


def test_ogni_discontinuita_attesa_esiste_davvero():
    """Il duale del test globale: verifica che le due discontinuità
    della whitelist producano DAVVERO un calo. Errore intercettato:
    una whitelist troppo permissiva che mascheri regressioni (se una
    discontinuità sparisse dalla normativa implementata, questo test
    obbligherebbe a rimuoverla anche dalla whitelist)."""
    for soglia in DISCONTINUITA_ATTESE:
        prima = calcola_netto(ral_da_imponibile(soglia - 1), 12)
        dopo = calcola_netto(ral_da_imponibile(soglia + 1), 12)
        assert dopo.netto_annuale < prima.netto_annuale, (
            f"La discontinuità attesa a imponibile {soglia} non produce "
            f"alcun calo: whitelist da aggiornare"
        )
