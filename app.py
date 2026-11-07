"""Tableau de bord des récoltes agricoles 2023-2025, présenté au ministère de l'agriculture."""

from pathlib import Path

import altair as alt
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
ECHELLE_CULTURES = alt.Scale(domain=list(COULEURS), range=list(COULEURS.values()))

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

# ------------------------------------------------------------------ Une partie par question
onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs(
    ["1. Poids des cultures", "2. Rendements", "3. Pluie", "4. Évolution 2023-2025", "5. Par habitant"]
)

# ---------- Question 1
with onglet1:
    st.subheader("Quelles cultures pèsent le plus, en tonnes puis en valeur ?")
    poids = filtre.groupby("culture", as_index=False).agg(
        production_t=("production_t", "sum"),
        valeur_htg=("valeur_htg", "sum"),
        prix_htg_kg=("prix_htg_kg", "first"),
    )
    poids["milliers_t"] = poids["production_t"] / 1000
    poids["valeur_milliards"] = poids["valeur_htg"] / 1e9
    poids["rang_tonnes"] = poids["production_t"].rank(ascending=False, method="first").astype(int)
    poids["rang_valeur"] = poids["valeur_htg"].rank(ascending=False, method="first").astype(int)

    couleur = alt.Color("culture:N", scale=ECHELLE_CULTURES, legend=None)
    gauche, milieu, droite = st.columns(3)
    with gauche:
        barres_tonnes = (
            alt.Chart(poids, title="En tonnes")
            .mark_bar()
            .encode(
                x=alt.X("milliers_t:Q", title="Milliers de tonnes"),
                y=alt.Y("culture:N", sort="-x", title=None),
                color=couleur,
                tooltip=[alt.Tooltip("culture", title="Culture"), alt.Tooltip("production_t", title="Tonnes", format=",.0f")],
            )
        )
        st.altair_chart(barres_tonnes, width="stretch")
    with milieu:
        barres_valeur = (
            alt.Chart(poids, title="En valeur")
            .mark_bar()
            .encode(
                x=alt.X("valeur_milliards:Q", title="Milliards de gourdes"),
                y=alt.Y("culture:N", sort="-x", title=None),
                color=couleur,
                tooltip=[
                    alt.Tooltip("culture", title="Culture"),
                    alt.Tooltip("valeur_milliards", title="Milliards HTG", format=".2f"),
                    alt.Tooltip("prix_htg_kg", title="Prix (HTG/kg)"),
                ],
            )
        )
        st.altair_chart(barres_valeur, width="stretch")
    with droite:
        # Graphique de pente : chaque culture relie son rang en tonnes (à gauche) à son rang en valeur (à droite).
        rangs = pd.concat(
            [
                poids.assign(position=0, rang=poids["rang_tonnes"]),
                poids.assign(position=1, rang=poids["rang_valeur"]),
            ]
        )
        rangs["etiquette"] = rangs["culture"] + " (" + rangs["rang"].astype(str) + ")"
        echelle_x = alt.X("position:Q", scale=alt.Scale(domain=[-0.9, 1.9]), axis=None)
        echelle_y = alt.Y("rang:Q", scale=alt.Scale(reverse=True, domain=[0.5, len(poids) + 0.5]), axis=None)
        pente = (
            alt.Chart(rangs, title=alt.Title("Le classement change-t-il ?", subtitle="Rang en tonnes → rang en valeur"))
            .mark_line(point=True, strokeWidth=3)
            .encode(x=echelle_x, y=echelle_y, color=couleur, detail="culture:N")
        )
        texte_gauche = (
            alt.Chart(rangs[rangs["position"] == 0])
            .mark_text(align="right", dx=-8)
            .encode(x=echelle_x, y=echelle_y, text="etiquette:N")
        )
        texte_droite = (
            alt.Chart(rangs[rangs["position"] == 1])
            .mark_text(align="left", dx=8)
            .encode(x=echelle_x, y=echelle_y, text="etiquette:N")
        )
        st.altair_chart(pente + texte_gauche + texte_droite, width="stretch")

    premier_tonnes = poids.loc[poids["production_t"].idxmax()]
    premier_valeur = poids.loc[poids["valeur_htg"].idxmax()]
    part_valeur = 100 * premier_valeur["valeur_htg"] / poids["valeur_htg"].sum()
    if premier_tonnes["culture"] == premier_valeur["culture"]:
        phrase = (
            f"**{premier_tonnes['culture']}** arrive en tête en tonnes ({nombre(premier_tonnes['production_t'])} t) "
            f"comme en valeur ({nombre(premier_valeur['valeur_milliards'], 1)} milliards de gourdes)."
        )
    else:
        phrase = (
            f"En tonnes, **{premier_tonnes['culture']}** arrive en tête ({nombre(premier_tonnes['production_t'])} t), "
            f"mais en valeur c'est **{premier_valeur['culture']}** : {nombre(premier_valeur['valeur_milliards'], 1)} "
            f"milliards de gourdes, {part_valeur:.0f} % de la valeur totale."
        )
    gains = poids.assign(gain=poids["rang_tonnes"] - poids["rang_valeur"]).sort_values("gain", ascending=False)
    meilleur_gain = gains.iloc[0]
    if meilleur_gain["gain"] > 0:
        phrase += (
            f" Le classement change : **{meilleur_gain['culture']}** gagne {meilleur_gain['gain']} places, "
            f"grâce à son prix de {nombre(meilleur_gain['prix_htg_kg'])} HTG le kilo."
        )
    st.success(f"**Ce qu'on en conclut :** {phrase}")

# ---------- Question 2
with onglet2:
    st.subheader("Où les rendements sont-ils les meilleurs, culture par culture ?")
    somme = filtre.groupby(["culture", "departement"], as_index=False)[
        ["production_t", "surface_ha", "production_attendue_t"]
    ].sum()
    # Rendement d'un groupe = somme des tonnes / somme des hectares (pas la moyenne des rendements).
    somme["rendement_t_ha"] = somme["production_t"] / somme["surface_ha"]
    somme["indice"] = somme["production_t"] / somme["production_attendue_t"]
    somme["texte"] = somme["rendement_t_ha"].map(lambda v: nombre(v, 2))
    ordre_departements = somme.groupby("departement")["indice"].mean().sort_values(ascending=False).index.tolist()

    base = alt.Chart(
        somme,
        title=alt.Title(
            "Rendement en tonnes par hectare",
            subtitle="Vert : au-dessus du rendement de référence de la culture. Rouge : en dessous.",
        ),
    ).encode(
        x=alt.X("departement:N", sort=ordre_departements, title=None, axis=alt.Axis(labelAngle=-30, orient="top")),
        y=alt.Y("culture:N", title=None),
    )
    cases = base.mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color(
            "indice:Q",
            scale=alt.Scale(scheme="redyellowgreen", domainMid=1),
            legend=alt.Legend(title="Rendement / référence", format=".0%"),
        ),
        tooltip=[
            alt.Tooltip("culture", title="Culture"),
            alt.Tooltip("departement", title="Département"),
            alt.Tooltip("rendement_t_ha", title="Rendement (t/ha)", format=".2f"),
            alt.Tooltip("indice", title="Par rapport à la référence", format=".0%"),
        ],
    )
    valeurs = base.mark_text(fontSize=12).encode(text="texte:N")
    st.altair_chart((cases + valeurs).properties(height=340), width="stretch")

    meilleurs = somme.loc[somme.groupby("culture")["rendement_t_ha"].idxmax()].sort_values("indice", ascending=False)
    meilleurs["ecart"] = 100 * (meilleurs["indice"] - 1)
    st.dataframe(
        meilleurs[["culture", "departement", "rendement_t_ha", "ecart"]],
        hide_index=True,
        column_config={
            "culture": "Culture",
            "departement": "Meilleur département",
            "rendement_t_ha": st.column_config.NumberColumn("Rendement (t/ha)", format="%.2f"),
            "ecart": st.column_config.NumberColumn("Écart à la référence", format="%+.0f %%"),
        },
    )
    champion = meilleurs["departement"].value_counts()
    premier = meilleurs.iloc[0]
    if filtre["departement"].nunique() == 1:
        phrase = "Avec un seul département choisi, on compare ses cultures à leur référence. "
    elif champion.iloc[0] == len(meilleurs):
        phrase = f"**{champion.index[0]}** a le meilleur rendement pour toutes les cultures choisies. "
    else:
        phrase = (
            f"Il n'y a pas un département champion pour tout : **{champion.index[0]}** est en tête pour "
            f"{champion.iloc[0]} culture{'s' if champion.iloc[0] > 1 else ''} sur {len(meilleurs)}. "
        )
    phrase += (
        f"Le record relatif est **{premier['culture']}** en **{premier['departement']}** : "
        f"{nombre(premier['rendement_t_ha'], 2)} t/ha, {premier['ecart']:.0f} % au-dessus de la référence."
    )
    st.success(f"**Ce qu'on en conclut :** {phrase}")

with onglet3:
    st.info("Cette partie arrive bientôt.")
with onglet4:
    st.info("Cette partie arrive bientôt.")

with onglet5:
    st.info("Cette partie arrive bientôt.")
