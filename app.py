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

# ---------- Question 3
with onglet3:
    st.subheader("La pluie explique-t-elle les rendements ? Pour quelles cultures ?")
    correlations = {
        culture: lignes["pluie_mm"].corr(lignes["rendement_t_ha"])
        for culture, lignes in filtre.groupby("culture")
        if len(lignes) >= 5
    }
    if not correlations:
        st.info("Pas assez de récoltes pour mesurer un lien : élargissez les filtres.")
    else:
        lien = pd.Series(correlations).sort_values(ascending=False)
        nuage = filtre[filtre["culture"].isin(lien.index)].copy()
        titres = {culture: f"{culture}  (r = {nombre(r, 2)})" for culture, r in lien.items()}
        nuage["titre"] = nuage["culture"].map(titres)
        ordre_titres = list(titres.values())

        points = (
            alt.Chart()
            .mark_circle(size=60, opacity=0.75)
            .encode(
                x=alt.X("pluie_mm:Q", title="Pluie de la saison (mm)", scale=alt.Scale(zero=False)),
                y=alt.Y("rendement_t_ha:Q", title="Rendement (t/ha)", scale=alt.Scale(zero=False)),
                color=alt.Color("culture:N", scale=ECHELLE_CULTURES, legend=None),
                tooltip=[
                    alt.Tooltip("departement", title="Département"),
                    alt.Tooltip("annee", title="Année"),
                    alt.Tooltip("saison", title="Saison"),
                    alt.Tooltip("pluie_mm", title="Pluie (mm)"),
                    alt.Tooltip("rendement_t_ha", title="Rendement (t/ha)", format=".2f"),
                ],
            )
        )
        droite = (
            alt.Chart()
            .transform_regression("pluie_mm", "rendement_t_ha")
            .mark_line(color="#2B2B2B", strokeWidth=2)
            .encode(x="pluie_mm:Q", y="rendement_t_ha:Q")
        )
        nuages = (
            alt.layer(points, droite, data=nuage)
            .properties(width=175, height=170)
            .facet(
                facet=alt.Facet("titre:N", sort=ordre_titres, title=None, header=alt.Header(labelFontSize=13, labelFontWeight="bold")),
                columns=4,
            )
            .resolve_scale(y="independent")
            .properties(title="Un point = une culture, une saison, un département. La droite résume la tendance.")
        )
        st.altair_chart(nuages)

        plus_fort, plus_faible = lien.index[0], lien.index[-1]
        if lien.iloc[0] >= 0.5:
            debut = "Oui : plus il pleut, plus le rendement monte."
        else:
            debut = "Le lien avec la pluie reste faible."
        phrase = (
            f"{debut} Le lien est le plus fort pour **{plus_fort}** "
            f"(r = {nombre(lien.iloc[0], 2)}, la pluie explique environ {100 * lien.iloc[0] ** 2:.0f} % des écarts de rendement)"
        )
        if len(lien) > 1:
            phrase += f" et le plus faible pour **{plus_faible}** (r = {nombre(lien.iloc[-1], 2)})"
            if plus_faible == "Riz":
                phrase += ", une culture souvent irriguée, donc moins dépendante de la pluie"
        phrase += "."
        if filtre["saison"].nunique() == 2:
            saisons = filtre.groupby("saison")[["production_t", "production_attendue_t"]].sum()
            indices = 100 * saisons["production_t"] / saisons["production_attendue_t"]
            phrase += (
                f" Les automnes, plus secs, rendent {nombre(indices['Automne'])} % de la référence, "
                f"contre {nombre(indices['Printemps'])} % au printemps."
            )
        st.success(f"**Ce qu'on en conclut :** {phrase}")
        st.caption("r est le coefficient de corrélation : 1 = lien parfait, 0 = aucun lien. Une corrélation ne prouve pas à elle seule la cause.")

# ---------- Question 4
with onglet4:
    st.subheader("Quelles cultures progressent ou reculent entre 2023 et 2025 ?")
    if not {2023, 2025} <= set(annees):
        st.info("Gardez 2023 et 2025 dans le filtre des années pour comparer le début et la fin de la période.")
    else:
        par_culture = filtre.groupby(["culture", "annee"])[["production_t", "surface_ha"]].sum().unstack().dropna()
        variations = pd.DataFrame(index=par_culture.index)
        variations["Production"] = 100 * (par_culture[("production_t", 2025)] / par_culture[("production_t", 2023)] - 1)
        variations["Surface"] = 100 * (par_culture[("surface_ha", 2025)] / par_culture[("surface_ha", 2023)] - 1)
        rendement_2023 = par_culture[("production_t", 2023)] / par_culture[("surface_ha", 2023)]
        rendement_2025 = par_culture[("production_t", 2025)] / par_culture[("surface_ha", 2025)]
        variations["Rendement"] = 100 * (rendement_2025 / rendement_2023 - 1)
        variations = variations.sort_values("Production", ascending=False)

        longue = variations.reset_index().melt(id_vars="culture", var_name="mesure", value_name="variation")
        barres = (
            alt.Chart(
                longue,
                title=alt.Title(
                    "Variation entre 2023 et 2025",
                    subtitle="La production change si l'on plante plus d'hectares (surface) ou si chaque hectare rend plus (rendement).",
                ),
            )
            .mark_bar()
            .encode(
                x=alt.X("culture:N", sort=variations.index.tolist(), title=None, axis=alt.Axis(labelAngle=0)),
                xOffset=alt.XOffset("mesure:N", sort=["Production", "Surface", "Rendement"]),
                y=alt.Y("variation:Q", title="Variation (%)"),
                color=alt.Color(
                    "mesure:N",
                    scale=alt.Scale(domain=["Production", "Surface", "Rendement"], range=["#A71E36", "#B0B0B0", "#4C78A8"]),
                    legend=alt.Legend(title=None, orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("culture", title="Culture"),
                    alt.Tooltip("mesure", title="Mesure"),
                    alt.Tooltip("variation", title="Variation (%)", format="+.1f"),
                ],
            )
        )
        zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#2B2B2B").encode(y="y:Q")
        st.altair_chart((barres + zero).properties(height=380), width="stretch")

        hausse, baisse = variations.iloc[0], variations.iloc[-1]

        def cause(ligne):
            if abs(ligne["Surface"]) >= abs(ligne["Rendement"]):
                return f"surtout parce que les surfaces ont {'augmenté' if ligne['Surface'] > 0 else 'baissé'} de {abs(ligne['Surface']):.0f} %"
            return f"surtout parce que le rendement a {'augmenté' if ligne['Rendement'] > 0 else 'baissé'} de {abs(ligne['Rendement']):.0f} %"

        def sens(ligne):
            return "progresse" if ligne["Production"] > 0 else "recule"

        phrase = f"**{hausse.name}** {sens(hausse)} de {abs(hausse['Production']):.0f} %, {cause(hausse)}."
        if len(variations) > 1:
            phrase = "La meilleure évolution : " + phrase
            phrase += f" La pire : **{baisse.name}** {sens(baisse)} de {abs(baisse['Production']):.0f} %, {cause(baisse)}."
            en_hausse = (variations["Production"] > 0).sum()
            phrase += f" Au total, {en_hausse} culture{'s' if en_hausse > 1 else ''} sur {len(variations)} progresse{'nt' if en_hausse > 1 else ''}."
        st.success(f"**Ce qu'on en conclut :** {phrase}")
        st.caption("10 récoltes manquent en 2023 et 2025 (productions vides dans le fichier brut) : les petites variations sont à lire avec prudence.")

with onglet5:
    st.info("Cette partie arrive bientôt.")
