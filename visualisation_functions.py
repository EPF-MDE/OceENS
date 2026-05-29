import os
import webbrowser
import pandas as pd
import plotly.express as px
from sondage_loader import load_sondage_complet

# -----------------------------------------------------------------------------
# 1. FONCTIONS DE GRAPHIQUES NETTES ET SANS WARNINGS
# -----------------------------------------------------------------------------


def generer_camembert_satisfaction(df_q: pd.DataFrame, title_prefix: str):
    """Génère un camembert ordonné pour les échelles de satisfaction strictes."""
    if df_q.empty:
        return None

    col_texte = next(
        (c for c in ["Question", "intitule", "Intitule"] if c in df_q.columns), None
    )
    intitule_question = df_q[col_texte].iloc[0] if col_texte else "Question"

    col_reponse = next(
        (
            c
            for c in ["Valeur_Reponse", "valeur", "Valeur", "reponse"]
            if c in df_q.columns
        ),
        None,
    )
    if not col_reponse:
        return None

    df_q = df_q.copy()

    # Nettoyage des espaces pour s'assurer de la correspondance exacte
    df_q[col_reponse] = df_q[col_reponse].astype(str).str.strip()

    ordre_satisfaction = [
        "Très satisfait",
        "Plutôt satisfait",
        "Moyennement satisfait",
        "Pas du tout satisfait",
    ]

    # Filtrer uniquement les lignes qui possèdent une vraie valeur de satisfaction pour éviter le warning Pandas
    df_filtré = df_q[df_q[col_reponse].isin(ordre_satisfaction)].copy()
    if df_filtré.empty:
        # Si aucune valeur ne correspond (ex: Oui/Non), on bascule sur un traitement générique
        return generer_camembert_generique(df_q, title_prefix)

    df_filtré[col_reponse] = pd.Categorical(
        df_filtré[col_reponse], categories=ordre_satisfaction, ordered=True
    )
    df_filtré = df_filtré.sort_values(col_reponse)

    couleurs_map = {
        "Très satisfait": "#2ca02c",
        "Plutôt satisfait": "#9467bd",
        "Moyennement satisfait": "#ff7f0e",
        "Pas du tout satisfait": "#d62728",
    }

    fig = px.pie(
        df_filtré,
        names=col_reponse,
        title=f"<b>{title_prefix}</b> - {intitule_question}",
        color=col_reponse,
        color_discrete_map=couleurs_map,
        hole=0.3,
    )
    fig.update_traces(textinfo="percent+label", textposition="inside")
    return fig


def generer_camembert_generique(df_q: pd.DataFrame, title_prefix: str):
    """Génère un camembert classique pour les questions de type Oui/Non, NPS, etc."""
    if df_q.empty:
        return None

    col_texte = next(
        (c for c in ["Question", "intitule", "Intitule"] if c in df_q.columns), None
    )
    intitule_question = df_q[col_texte].iloc[0] if col_texte else "Question"

    col_reponse = next(
        (
            c
            for c in ["Valeur_Reponse", "valeur", "Valeur", "reponse"]
            if c in df_q.columns
        ),
        None,
    )
    if not col_reponse:
        return None

    fig = px.pie(
        df_q,
        names=col_reponse,
        title=f"<b>{title_prefix}</b> - {intitule_question}",
        hole=0.3,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(textinfo="percent+label", textposition="inside")
    return fig


def generer_histogramme_motifs(df_m: pd.DataFrame, title_prefix: str):
    """Génère un histogramme horizontal propre pour les motifs d'insatisfaction."""
    if df_m.empty:
        return None

    col_texte = next(
        (c for c in ["Question", "intitule", "Intitule"] if c in df_m.columns), None
    )
    intitule_question = df_m[col_texte].iloc[0] if col_texte else "Question"

    col_reponse = next(
        (
            c
            for c in ["Valeur_Reponse", "valeur", "Valeur", "reponse"]
            if c in df_m.columns
        ),
        None,
    )
    if not col_reponse:
        return None

    df_counts = df_m[col_reponse].value_counts(normalize=True).reset_index()
    df_counts.columns = ["Motif", "Proportion"]
    df_counts["Pourcentage"] = df_counts["Proportion"] * 100

    fig = px.bar(
        df_counts,
        x="Pourcentage",
        y="Motif",
        orientation="h",
        title=f"<b>{title_prefix}</b> - {intitule_question}<br><sup>(Motifs d'insatisfaction recensés)</sup>",
        text="Pourcentage",
        color_discrete_sequence=["#d62728"],
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Pourcentage (%)",
        yaxis_title="",
    )
    return fig


# -----------------------------------------------------------------------------
# 2. LE CHEF D'ORCHESTRE AVEC DECOUPLEMENT STRICT DES TYPES
# -----------------------------------------------------------------------------


def generer_tous_les_graphes_du_sondage(sondage_obj, df: pd.DataFrame) -> dict:
    f_charts_html = {}
    print(f"\n📊 [CHEF D'ORCHESTRE] Navigation ordonnée dans : {sondage_obj.formation}")

    col_question_id = next(
        (c for c in ["Question_ID", "id_question", "Id_Question"] if c in df.columns),
        None,
    )
    col_section_id = next(
        (c for c in ["Section_ID", "id_section", "Id_Section"] if c in df.columns), None
    )

    if not col_question_id:
        print(f"❌ ERREUR : Colonne d'ID de question introuvable.")
        return f_charts_html

    for section in sondage_obj.sections:
        print(f"\n📁 Section : '{section.nom}'")

        for question in section.questions:
            q_type = getattr(
                question, "question_type", getattr(question, "type_question", None)
            )
            q_id = question.id_question

            # Sécurité de filtrage par section si disponible
            if (
                col_section_id
                and hasattr(section, "id_section")
                and section.id_section is not None
            ):
                df_question = df[
                    (df[col_question_id] == q_id)
                    & (df[col_section_id] == section.id_section)
                ]
            else:
                df_question = df[df[col_question_id] == q_id]

            nb_reponses = len(df_question)
            if nb_reponses == 0:
                continue

            q_type_str = str(q_type).strip().upper() if q_type else ""
            title_label = f"{section.nom} (Q{q_id})"
            cle_unique = f"chart_{section.nom.replace(' ', '_')}_{q_id}"

            # 🔥 CORRECTION DU ROUTAGE : L'ordre des vérifications évite les conflits de mots-clés
            if "INSATISFACTION" in q_type_str or "MOTIF" in q_type_str:
                fig = generer_histogramme_motifs(df_question, title_label)
                if fig:
                    f_charts_html[cle_unique] = fig.to_html(
                        full_html=False, include_plotlyjs="cdn"
                    )
                    print(f"      ✅ [Histogramme] Généré pour l'insatisfaction")

            elif "SATISFACTION" in q_type_str:
                fig = generer_camembert_satisfaction(df_question, title_label)
                if fig:
                    f_charts_html[cle_unique] = fig.to_html(
                        full_html=False, include_plotlyjs="cdn"
                    )
                    print(f"      ✅ [Camembert] Généré pour la satisfaction")

            elif "OUI_NON" in q_type_str or "NPS" in q_type_str:
                fig = generer_camembert_generique(df_question, title_label)
                if fig:
                    f_charts_html[cle_unique] = fig.to_html(
                        full_html=False, include_plotlyjs="cdn"
                    )
                    print(f"      ✅ [Camembert Générique] Généré pour {q_type_str}")

    return f_charts_html


# -----------------------------------------------------------------------------
# 3. BLOC DE TEST RUNNER
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    DB_FILE = "database/db_oceens.db"

    print("=" * 60)
    print("      DEBUT DU TEST DU CHEF D'ORCHESTRE WEB (PRO INDESTRUCTIBLE)")
    print("=" * 60)

    try:
        sondage = load_sondage_complet(DB_FILE, id_template=1, id_sondage=1)
        records = sondage.to_flat_dataframe_records()

        if len(records) == 0:
            print("❌ ERREUR : Aucun enregistrement renvoyé.")
        else:
            df_plat = pd.DataFrame(records)
            dictionnaire_graphes = generer_tous_les_graphes_du_sondage(sondage, df_plat)

            print("\n[VÉRIFICATION DES RÉSULTATS FINAUX]")
            print(
                f"-> Nombre total de graphiques HTML générés : {len(dictionnaire_graphes)}"
            )

            if dictionnaire_graphes:
                html_page_de_test = """
                <!DOCTYPE html>
                <html lang="fr">
                <head>
                    <meta charset="UTF-8">
                    <title>Test Dashboard Visuel</title>
                    <style>
                        body { font-family: sans-serif; margin: 40px; background-color: #f4f6f9; }
                        .container { max-width: 1000px; margin: auto; }
                        .header { background: #1e293b; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                        .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Dashboard de Test Visuel Corrigé 🚀</h1>
                """
                html_page_de_test += f"<p>Formation : {sondage.formation} | Année : {sondage.annee_scolaire}</p></div>"

                for q_key, chart_html in dictionnaire_graphes.items():
                    html_page_de_test += f"<div class='card'>{chart_html}</div>"

                html_page_de_test += "</div></body></html>"

                file_name = "preview_dashboard_test.html"
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(html_page_de_test)

                webbrowser.open(f"file:///{os.path.abspath(file_name)}")
                print(
                    "\n✨ Nettoyage terminé ! Ton navigateur affiche désormais le rendu exact."
                )

    except Exception as e:
        print(f"\n❌ Le test a planté : {e}")
