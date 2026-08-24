"""Interfaccia Streamlit V0 — Quanto vale davvero la tua RAL?

REGOLA ARCHITETTURALE: questo file NON contiene alcuna formula fiscale,
contributiva o di validazione del dominio. Il flusso è esclusivamente:

    input utente → calcola_netto() → RisultatoCalcolo → formattazione

Gli unici helper definiti qui sono di PRESENTAZIONE (formato monetario
e percentuale in stile italiano). Ogni valore mostrato proviene dai
campi di RisultatoCalcolo; le aggregazioni (addizionali totali,
benefici totali) sono somme di campi già calcolati dal motore, fatte
solo per compattare la visualizzazione.

Avvio:  streamlit run app.py
"""

from decimal import Decimal, ROUND_HALF_UP

import streamlit as st

from calcolatore import calcola_netto, per_output
import regole_fiscali_2026 as regole


# ─────────────────────────────────────────────────────────────────────────
# Helper di presentazione (solo formattazione, nessun calcolo fiscale)
# ─────────────────────────────────────────────────────────────────────────

def formatta_euro(valore: Decimal) -> str:
    """Decimal → stringa monetaria in stile italiano.

    23425.48 → "€ 23.425,48". Passa da per_output() per garantire
    l'arrotondamento di presentazione deciso nel motore (ROUND_HALF_UP
    a 2 decimali), poi converte i separatori: il formato Python usa
    virgola per le migliaia e punto per i decimali, l'italiano il
    contrario — lo swap passa da un segnaposto temporaneo.
    """
    arrotondato = per_output(valore)
    testo = f"{arrotondato:,.2f}"                     # "23,425.48"
    testo = testo.replace(",", "@").replace(".", ",").replace("@", ".")
    return f"€ {testo}"


def formatta_percentuale(frazione: Decimal) -> str:
    """Frazione → percentuale italiana a 1 decimale.

    0.7437... → "74,4%". Stesso criterio di arrotondamento della
    presentazione monetaria (ROUND_HALF_UP), applicato a 1 decimale.
    """
    percento = (frazione * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{percento}".replace(".", ",") + "%"


# ─────────────────────────────────────────────────────────────────────────
# Configurazione pagina e hero
# ─────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Quanto vale davvero la tua RAL?",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Quanto vale davvero la tua RAL?")
st.markdown("Dal lordo al netto, con una stima basata sulla normativa 2026.")
st.caption("Milano · Normativa 2026")

st.divider()

# ─────────────────────────────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────────────────────────────

col_ral, col_mensilita = st.columns([2, 1])

with col_ral:
    ral_input = st.number_input(
        "Retribuzione Annua Lorda (RAL)",
        min_value=20_000,
        max_value=100_000,
        value=35_000,
        step=500,
        help="Da €20.000 a €100.000 — il perimetro della V1 del prototipo.",
    )

with col_mensilita:
    # st.segmented_control esiste da Streamlit 1.40: se la versione
    # installata non lo offre, si ripiega su un radio orizzontale.
    # In entrambi i casi il default è 13 mensilità.
    if hasattr(st, "segmented_control"):
        mensilita_input = st.segmented_control(
            "Mensilità", options=[12, 13, 14], default=13
        )
        if mensilita_input is None:  # il controllo permette la deselezione
            mensilita_input = 13
    else:
        mensilita_input = st.radio(
            "Mensilità", options=[12, 13, 14], index=1, horizontal=True
        )

calcola = st.button("Calcola il netto", type="primary")

# ─────────────────────────────────────────────────────────────────────────
# Calcolo e risultato
# ─────────────────────────────────────────────────────────────────────────

if calcola:
    try:
        # Conversione sicura UI → motore: Decimal(str(...)) evita di
        # ereditare l'errore binario di un eventuale float della UI.
        risultato = calcola_netto(Decimal(str(ral_input)), int(mensilita_input))
    except ValueError as errore:
        st.error(
            "Il calcolo non è possibile con questi valori: "
            f"{errore}"
        )
    else:
        st.divider()

        # ── Numero principale: il netto mensile medio ──
        st.markdown(f"# {formatta_euro(risultato.netto_mensile)}")
        st.markdown(
            f"**netto mensile medio** · su {risultato.mensilita} mensilità"
        )

        # ── Netto annuo e percentuale della RAL ──
        st.markdown(
            f"{formatta_euro(risultato.netto_annuale)} netto annuo stimato · "
            f"{formatta_percentuale(risultato.percentuale_netto)} della RAL"
        )

        st.divider()

        # ── Riepilogo essenziale (tutti i valori da RisultatoCalcolo) ──
        st.subheader("Riepilogo")

        addizionali_totali = (
            risultato.addizionale_regionale + risultato.addizionale_comunale
        )
        benefici_totali = (
            risultato.somma_cuneo + risultato.trattamento_integrativo
        )

        riepilogo = [
            ("RAL", formatta_euro(risultato.ral)),
            ("Contributi previdenziali", f"− {formatta_euro(risultato.contributi_totali)}"),
            ("Reddito imponibile", formatta_euro(risultato.reddito_imponibile)),
            ("IRPEF netta", f"− {formatta_euro(risultato.irpef_netta)}"),
            ("Addizionali (regionale + comunale)", f"− {formatta_euro(addizionali_totali)}"),
            ("Benefici fiscali", f"+ {formatta_euro(benefici_totali)}"),
            ("Netto annuo", formatta_euro(risultato.netto_annuale)),
        ]
        for voce, importo in riepilogo:
            col_voce, col_importo = st.columns([3, 1])
            col_voce.markdown(voce)
            col_importo.markdown(f"**{importo}**")

st.divider()

# ─────────────────────────────────────────────────────────────────────────
# Assunzioni del calcolo
# ─────────────────────────────────────────────────────────────────────────

with st.expander("Assunzioni del calcolo"):
    st.markdown(
        f"""
- Lavoratore dipendente del settore privato
- Contratto a tempo indeterminato, full-time
- Rapporto di lavoro per l'intero anno, con un unico datore di lavoro
- Residenza fiscale a Milano, Regione Lombardia, per tutto l'anno
- Nessun altro reddito oltre quello da lavoro dipendente
- Nessun familiare a carico
- Nessuna agevolazione o detrazione personale particolare
- RAL ammessa: da {formatta_euro(regole.RAL_MIN)} a {formatta_euro(regole.RAL_MAX)}
        """
    )
