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


def ordre_saison(table):
    """Numéro de saison dans le temps : printemps 2023 = 0, automne 2023 = 1, printemps 2024 = 2..."""
    return (table["annee"] - 2023) * 2 + (table["saison"] == "Automne")


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

# ------------------------------------------------------------------ Indicateurs
par_saison = (
    filtre.assign(ordre=ordre_saison(filtre))
    .groupby("ordre")[["production_t", "valeur_htg", "production_attendue_t"]]
    .sum()
)
# La pluie est donnée une fois par saison et par département : on ne la compte pas une fois par culture.
pluies = filtre.drop_duplicates(["annee", "saison", "departement"])
pluie_par_saison = pluies.assign(ordre=ordre_saison(pluies)).groupby("ordre")["pluie_mm"].mean()

production = filtre["production_t"].sum()
valeur = filtre["valeur_htg"].sum()
indice = production / filtre["production_attendue_t"].sum()

evolution = None
if len(annees) >= 2:
    par_annee = filtre.groupby("annee")["production_t"].sum()
    premiere, derniere = min(annees), max(annees)
    if premiere in par_annee and derniere in par_annee:
        variation = 100 * (par_annee[derniere] / par_annee[premiere] - 1)
        evolution = f"{variation:+.0f} % de {premiere} à {derniere}"

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Production (milliers de tonnes)",
    nombre(production / 1000),
    evolution,
    border=True,
    chart_data=(par_saison["production_t"] / 1000).round(1).tolist(),
    help="Total des tonnes récoltées. La courbe suit les saisons, du printemps 2023 à l'automne 2025.",
)
col2.metric(
    "Valeur (milliards de gourdes)",
    nombre(valeur / 1e9, 2),
    border=True,
    chart_data=(par_saison["valeur_htg"] / 1e9).round(2).tolist(),
    help="Tonnes × 1 000 × prix au kilo de chaque culture.",
)
col3.metric(
    "Rendement / référence",
    f"{nombre(100 * indice)} %",
    f"{100 * (indice - 1):+.0f} points",
    border=True,
    chart_data=(100 * par_saison["production_t"] / par_saison["production_attendue_t"]).round(0).tolist(),
    help="Production réelle divisée par la production attendue avec le rendement de référence de chaque culture. "
    "100 % = la référence. Permet de comparer des cultures très différentes.",
)
col4.metric(
    "Pluie moyenne par saison",
    f"{nombre(pluies['pluie_mm'].mean())} mm",
    border=True,
    chart_data=pluie_par_saison.round(0).tolist(),
    chart_type="bar",
    help="Moyenne des pluies des saisons et départements choisis.",
)
st.caption(
    f"{len(filtre)} récoltes retenues. Les petites courbes suivent les saisons dans le temps : "
    "on y voit le rendement monter chaque printemps, plus pluvieux, et baisser chaque automne."
)

st.write(f"Le fichier propre compte {len(filtre)} lignes.")
st.dataframe(filtre.head(10), hide_index=True)
