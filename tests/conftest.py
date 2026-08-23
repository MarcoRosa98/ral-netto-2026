"""Configurazione pytest: rende importabili i moduli del progetto.

I test vivono in tests/ ma importano calcolatore e regole_fiscali_2026
dalla radice del progetto: aggiungiamo la radice al path di ricerca.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
