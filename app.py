"""Interfaccia Streamlit — Quanto vale davvero la tua RAL?

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
    testo = f"{arrotondato:,.2f}"
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
        help="Da €20.000 a €100.000 — intervallo supportato dal modello.",
    )

with col_mensilita:
    if hasattr(st, "segmented_control"):
        mensilita_input = st.segmented_control(
            "Mensilità", options=[12, 13, 14], default=13
        )
        if mensilita_input is None:
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
        risultato = calcola_netto(Decimal(str(ral_input)), int(mensilita_input))
    except ValueError as errore:
        st.error(
            "Il calcolo non è possibile con questi valori: "
            f"{errore}"
        )
    else:
        st.divider()

        st.markdown(f"# {formatta_euro(risultato.netto_mensile)}")
        st.markdown(
            f"**netto mensile medio** · su {risultato.mensilita} mensilità"
        )

        st.markdown(
            f"{formatta_euro(risultato.netto_annuale)} netto annuo stimato · "
            f"{formatta_percentuale(risultato.percentuale_netto)} della RAL"
        )

        st.divider()

        st.subheader("Riepilogo")

        addizionali_totali = (
            risultato.addizionale_regionale + risultato.addizionale_comunale
        )
        benefici_totali = (
            risultato.somma_cuneo + risultato.trattamento_integrativo
        )

        riepilogo = [
            ("RAL", formatta_euro(risultato.ral)),
            (
                "Contributi previdenziali",
                f"− {formatta_euro(risultato.contributi_totali)}",
            ),
            ("Reddito imponibile", formatta_euro(risultato.reddito_imponibile)),
            ("IRPEF netta", f"− {formatta_euro(risultato.irpef_netta)}"),
            (
                "Addizionali (regionale + comunale)",
                f"− {formatta_euro(addizionali_totali)}",
            ),
        ]

        if risultato.somma_cuneo > 0:
            riepilogo.append(
                (
                    "Somma cuneo fiscale",
                    f"+ {formatta_euro(risultato.somma_cuneo)}",
                )
            )

        if risultato.trattamento_integrativo > 0:
            riepilogo.append(
                (
                    "Trattamento integrativo",
                    f"+ {formatta_euro(risultato.trattamento_integrativo)}",
                )
            )

        riepilogo.append(
            ("Netto annuo", formatta_euro(risultato.netto_annuale))
        )

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
- Profilo contributivo ordinario FPLD per la quota a carico del lavoratore
- Residenza fiscale a Milano, Regione Lombardia, per tutto l'anno
- Nessun altro reddito oltre quello da lavoro dipendente
- Nessun familiare a carico
- Nessuna agevolazione o detrazione personale particolare
- RAL ammessa: da {formatta_euro(regole.RAL_MIN)} a {formatta_euro(regole.RAL_MAX)}
        """
    )

# ─────────────────────────────────────────────────────────────────────────
# Fonti normative e istituzionali
# ─────────────────────────────────────────────────────────────────────────

with st.expander("📚 Fonti normative e istituzionali"):
    st.markdown(
        """
**Periodo d'imposta di riferimento: 2026**

Il modello è stato costruito utilizzando fonti normative e istituzionali.
I simulatori esterni sono stati utilizzati soltanto come benchmark di
validazione, non come fonte delle regole.

### IRPEF
- **Art. 11 del TUIR (D.P.R. 22 dicembre 1986, n. 917)** — disciplina
  dell'IRPEF per scaglioni.
- **Legge 30 dicembre 2025, n. 199, art. 1, comma 3** — per il 2026
  l'aliquota del secondo scaglione è ridotta dal 35% al **33%**.
- Aliquote utilizzate dal modello: **23% / 33% / 43%**.

[Consulta la Legge 30 dicembre 2025, n. 199 su Normattiva](https://www.normattiva.it/eli/stato/LEGGE/2025/12/30/199/CONSOLIDATED)

### Detrazione per lavoro dipendente
- **Art. 13 del TUIR** — detrazione per redditi di lavoro dipendente.
- **Legge 30 dicembre 2024, n. 207** — interventi sulla disciplina
  applicabile, incluso l'importo di €1.955 per il primo livello di reddito.

[Consulta la Legge 30 dicembre 2024, n. 207 su Normattiva](https://www.normattiva.it/eli/stato/LEGGE/2024/12/30/207/ORIGINAL)

### Riduzione del cuneo fiscale
- **Legge 30 dicembre 2024, n. 207, art. 1, commi 4–6** — somma riconosciuta
  per i redditi fino a €20.000 e ulteriore detrazione per i redditi
  superiori a €20.000 e fino a €40.000.

### Contributi previdenziali
- **INPS, Circolare n. 101 del 29 novembre 2024** — profilo ordinario FPLD
  e quota IVS a carico del lavoratore pari al **9,19%**.
- **INPS, Circolare n. 6 del 30 gennaio 2026** — prima fascia di retribuzione
  pensionabile 2026 pari a **€56.224** e contributo aggiuntivo dell'**1%**
  sulla quota eccedente.

[Circolare INPS n. 101/2024](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2024.11.circolare-numero-101-del-29-11-2024_14714.html)

[Circolare INPS n. 6/2026](https://www.inps.it/it/it/inps-comunica/atti/circolari-messaggi-e-normativa/dettaglio.circolari-e-messaggi.2026.01.circolare-numero-6-del-30-01-2026_15151.html)

### Addizionale regionale — Lombardia
- **Regione Lombardia — Addizionale regionale all'IRPEF**.
- Aliquote progressive utilizzate: **1,23% / 1,58% / 1,72% / 1,73%**.

[Consulta la fonte ufficiale di Regione Lombardia](https://www.regione.lombardia.it/bollo-auto-e-tributi-regionali/red-addizionale-regionale-irpef)

### Addizionale comunale — Milano
- **Comune di Milano — Addizionale comunale IRPEF**.
- Aliquota utilizzata: **0,8%**.
- Esenzione per reddito imponibile non superiore a **€23.000**.

[Consulta la fonte ufficiale del Comune di Milano](https://www.comune.milano.it/argomenti/tributi/addizionale-comunale-irpef)

---

Per il dettaglio delle formule, delle assunzioni, dei test e della
metodologia di validazione è disponibile la documentazione completa
nella repository GitHub.
        """
    )

    st.link_button(
        "Apri la documentazione completa su GitHub",
        "https://github.com/MarcoRosa98/ral-netto-2026/tree/main",
    )
