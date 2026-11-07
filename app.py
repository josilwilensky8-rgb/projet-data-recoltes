"""Tableau de bord des récoltes agricoles 2023-2025, présenté au ministère de l'agriculture."""

from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

# Une couleur fixe par culture, la même que dans le notebook.
COULEURS = {
    "Banane": "#E3B505",
    "Igname": "#8C564B",
    "Riz": "#4C78A8",
    "Maïs": "#F58518",
    "Sorgho": "#B279A2",
    "Haricot": "#A71E36",
    "Pois congo": "#54A24B",
}

st.set_page_config(page_title="Les récoltes agricoles", page_icon="🌾", layout="wide")


@st.cache_data
def charger_donnees():
    """Lit le fichier propre écrit par le notebook : le nettoyage n'est pas refait ici."""
    return pd.read_csv(DOSSIER / "recoltes_propre.csv")


def nombre(valeur, decimales=0):
    """Écrit un nombre à la française : 1 234 567,8."""
    texte = f"{valeur:,.{decimales}f}"
    return texte.replace(",", " ").replace(".", ",")


recoltes = charger_donnees()

st.title("🌾 Les récoltes agricoles, 2023-2025")
st.markdown(
    "La direction départementale de l'agriculture a suivi **7 cultures** dans les **10 départements**, au printemps "
    "et à l'automne, de 2023 à 2025. Ce tableau de bord dit au ministère quelles cultures pèsent le plus, où les "
    "rendements sont les meilleurs, et si la pluie explique les mauvaises années."
)
st.caption(
    "**Source :** direction départementale de l'agriculture (données fictives) : récoltes, prix, pluies et population. "
    "Nettoyage et jointures dans `exploration.ipynb`. Projet final, Python pour l'analyse de données, ESIH 2026."
)

# ------------------------------------------------------------------ Filtres
st.sidebar.header("Filtres")
st.sidebar.caption("Ils changent les indicateurs et tous les graphiques.")

annees = st.sidebar.multiselect("Années", [2023, 2024, 2025], default=[2023, 2024, 2025])
saison = st.sidebar.selectbox("Saison", ["Les deux saisons", "Printemps", "Automne"])
tous_departements = sorted(recoltes["departement"].unique())
departements = st.sidebar.multiselect("Départements", tous_departements, default=tous_departements)
cultures = st.sidebar.multiselect("Cultures", list(COULEURS), default=list(COULEURS))

filtre = recoltes[
    recoltes["annee"].isin(annees)
    & recoltes["departement"].isin(departements)
    & recoltes["culture"].isin(cultures)
]
if saison != "Les deux saisons":
    filtre = filtre[filtre["saison"] == saison]

if filtre.empty:
    st.warning("Aucune récolte ne correspond à ces filtres : gardez au moins une année, un département et une culture.")
    st.stop()

st.write(f"Le fichier propre compte {len(filtre)} lignes.")
st.dataframe(filtre.head(10), hide_index=True)
