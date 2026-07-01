import sqlite3
from dataclasses import dataclass, field
from typing import List, Dict, Any

# -----------------------------------------------------------------------------
# 0. Fonction utilitaire de nettoyage des textes (Correction Encodage)
# -----------------------------------------------------------------------------


def clean_mojibake(text: Any) -> str:
    """
    Détecte et répare automatiquement les caractères accentués mal encodés
    provenant de la base de données (ex: 'prÃªts' -> 'prêts').
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    try:
        # Tente de restaurer la chaîne si elle a été encodée en UTF-8 puis lue en Latin-1
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # En cas d'échec, application d'un dictionnaire de secours pour les cas fréquents
        replacements = {
            "Ã©": "é",
            "Ã¨": "è",
            "Ã ": "à",
            "Ã§": "ç",
            "Ã¹": "ù",
            "Ã¢": "â",
            "Ãª": "ê",
            "Ã®": "î",
            "Ã´": "ô",
            "Ã‰": "É",
            "Ã ": "À",
            "Ãª": "ê",
            "Ã»": "û",
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text


# -----------------------------------------------------------------------------
# 1. Définition des Dataclasses (Modèles propres pour la Visualisation)
# -----------------------------------------------------------------------------


@dataclass
class OptionData:
    id_option: int
    intitule: str


@dataclass
class ReponseData:
    id_reponse: int
    valeur: str
    id_module: int | None = None
    ue: str = ""
    module: str = ""
    enseignant: str = ""


@dataclass
class QuestionData:
    id_question: int
    intitule: str
    categorie: str
    type_question: str
    options: List[OptionData] = field(default_factory=list)
    reponses: List[ReponseData] = field(default_factory=list)


@dataclass
class SectionData:
    id_section: int
    nom: str
    ordre: int
    questions: List[QuestionData] = field(default_factory=list)


@dataclass
class ModuleData:
    id_module: int
    nom: str
    ue: str
    enseignant: str  # Corrigé au singulier d'après la structure réelle


@dataclass
class SondageComplet:
    """Objet racine contenant tout le contexte et les données nettoyées d'un sondage"""

    id_template: int
    id_sondage: int
    campus: str
    formation: str
    semestre: str
    annee_scolaire: str  # Corrigé d'après models.py (scolaire en minuscule)
    modules: List[ModuleData] = field(default_factory=list)
    sections: List[SectionData] = field(default_factory=list)

    def to_flat_dataframe_records(self) -> List[Dict[str, Any]]:
        """
        Génère une liste de dictionnaires à plat, idéale pour Pandas :
        df = pd.DataFrame(sondage.to_flat_dataframe_records())
        """
        records = []
        for section in self.sections:
            for question in section.questions:
                for reponse in question.reponses:
                    records.append(
                        {
                            "Campus": self.campus,
                            "Formation": self.formation,
                            "Semestre": self.semestre,
                            "Annee_Scolaire": self.annee_scolaire,
                            "UE": reponse.ue,
                            "Module": reponse.module,
                            "Enseignant": reponse.enseignant,
                            "Section": section.nom,
                            "Question_ID": question.id_question,
                            "Question": question.intitule,
                            "Type_Question": question.type_question,
                            "Categorie": question.categorie,
                            "Reponse_ID": reponse.id_reponse,
                            "Valeur_Reponse": reponse.valeur,
                        }
                    )
        return records


# -----------------------------------------------------------------------------
# 2. Le chargeur de données (Loader)
# -----------------------------------------------------------------------------


def load_sondage_complet(
    db_path: str, id_template: int, id_sondage: int
) -> SondageComplet:
    """
    Se connecte à la base SQLite, extrait les données du sondage cible,
    nettoie les chaînes de caractères et structure le tout sous forme d'objet.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Accès aux colonnes par nom
    cursor = conn.cursor()

    def get_row_field(row: sqlite3.Row, *possible_names) -> str:
        keys = row.keys()
        for name in possible_names:
            if name in keys:
                return row[name]
        return ""

    # --- A. Infos du sondage ---
    cursor.execute(
        "SELECT * FROM Sondages WHERE Id_Template = ? AND Id_Sondage = ?",
        (id_template, id_sondage),
    )
    row_sondage = cursor.fetchone()
    if not row_sondage:
        conn.close()
        raise ValueError(
            f"Sondage introuvable (Template: {id_template}, Sondage: {id_sondage})"
        )

    sondage = SondageComplet(
        id_template=row_sondage["Id_Template"],
        id_sondage=row_sondage["Id_Sondage"],
        campus=clean_mojibake(row_sondage["Campus"]),
        formation=clean_mojibake(row_sondage["Formation"]),
        semestre=clean_mojibake(row_sondage["Semestre"]),
        annee_scolaire=clean_mojibake(row_sondage["Annee_scolaire"]),
    )

    # --- B. Récupération des Modules ---
    cursor.execute(
        "SELECT * FROM Modules WHERE Id_Template = ? AND Id_Sondage = ?",
        (id_template, id_sondage),
    )
    for row in cursor.fetchall():
        sondage.modules.append(
            ModuleData(
                id_module=row["Id_Module"],
                nom=clean_mojibake(row["Nom"]),
                ue=clean_mojibake(row["UE"]),
                enseignant=clean_mojibake(row["Enseignant"]),
            )
        )
    modules_by_id = {module.id_module: module for module in sondage.modules}

    # --- C. Récupération des Sections ---
    cursor.execute(
        "SELECT * FROM Sections WHERE Id_Template = ? ORDER BY Ordre", (id_template,)
    )
    sections_dict = {}
    for row in cursor.fetchall():
        sec = SectionData(
            id_section=row["Id_Section"],
            nom=clean_mojibake(row["Nom"]),
            ordre=row["Ordre"],
        )
        sections_dict[sec.id_section] = sec
        sondage.sections.append(sec)

    # --- D. Récupération des Questions ---
    cursor.execute("SELECT * FROM Questions WHERE Id_Template = ?", (id_template,))
    questions_dict = {}
    for row in cursor.fetchall():
        q = QuestionData(
            id_question=row["Id_Question"],
            intitule=clean_mojibake(
                get_row_field(row, "Intitulé", "IntitulÃ©", "Intitule")
            ),
            categorie=clean_mojibake(
                get_row_field(row, "Catégorie", "CatÃ©gorie", "Categorie")
            ),
            type_question=clean_mojibake(row["Type"]),
        )
        questions_dict[(row["Id_Section"], row["Id_Question"])] = q
        if row["Id_Section"] in sections_dict:
            sections_dict[row["Id_Section"]].questions.append(q)

    # --- E. Récupération des Options de réponses (QCM/QCU) ---
    cursor.execute("SELECT * FROM Options WHERE Id_Template = ?", (id_template,))
    for row in cursor.fetchall():
        opt = OptionData(
            id_option=row["Id_Option"],
            intitule=clean_mojibake(
                get_row_field(row, "Intitulé", "IntitulÃ©", "Intitule")
            ),
        )
        q_key = (row["Id_Section"], row["Id_Question"])
        if q_key in questions_dict:
            questions_dict[q_key].options.append(opt)

    # --- F. Récupération des Réponses soumises ---

    cursor.execute(
        "SELECT * FROM Reponses WHERE Id_Template = ? AND Id_Sondage = ?",
        (id_template, id_sondage),
    )

    for row in cursor.fetchall():
        id_module = row["Id_Module"]
        module = modules_by_id.get(id_module)

        #enseignant_reponse = row["Enseignant"]
        enseignant_reponse = row["Enseignant"] if "Enseignant" in row.keys() else ""

        enseignant_module = module.enseignant if module else ""

        rep = ReponseData(
            id_reponse=row["Id_Reponse"],
            valeur=clean_mojibake(row["Valeur"]),
            id_module=id_module,
            ue=clean_mojibake(module.ue) if module else "",
            module=clean_mojibake(module.nom) if module else "",
            enseignant=clean_mojibake(enseignant_reponse or enseignant_module),
        )

        q_key = (row["Id_Section"], row["Id_Question"])
        if q_key in questions_dict:
            questions_dict[q_key].reponses.append(rep)

    conn.close()
    return sondage


# -----------------------------------------------------------------------------
# 3. Exemple d'exécution et d'exploration pédagogique
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import pandas as pd

    # Étape 1 : Définition du chemin de la base (à adapter si nécessaire)
    DB_FILE = "database/db_oceens.db"

    print("=" * 60)
    print("ÉTAPES DE CHARGEMENT ET STRUCTURE DES OBJETS PYTHON")
    print("=" * 60)

    try:
        # Étape 2 : Chargement des données brutes SQL vers l'Objet Racine
        # (Ici on prend id_template=1 et id_sondage=1 à titre d'exemple)
        sondage_obj = load_sondage_complet(DB_FILE, id_template=1, id_sondage=1)

        # --- COMPRENDRE L'OBJET RACINE ---
        print(f"\n[1] OBJET RACINE REÇU : <SondageComplet>")
        print(f"    └── Formation : {sondage_obj.formation}")
        print(f"    └── Campus    : {sondage_obj.campus}")
        print(f"    └── Année     : {sondage_obj.annee_scolaire}")
        print(f"    └── Semestre  : {sondage_obj.semestre}")

        # --- COMPRENDRE LES MODULES ASSOCIES ---
        print(f"\n[2] LISTE DES MODULES RATTACHÉS (.modules) :")
        for mod in sondage_obj.modules[
            :3
        ]:  # On affiche les 3 premiers pour ne pas saturer le terminal
            print(
                f"    └── Module ID {mod.id_module} : {mod.nom} ({mod.ue}) - Enseignant : {mod.enseignant}"
            )
        if len(sondage_obj.modules) > 3:
            print(f"    ... et {len(sondage_obj.modules) - 3} autres modules.")

        # --- COMPRENDRE L'IMBRICATION : SECTIONS -> QUESTIONS -> REPONSES ---
        print(
            f"\n[3] EXPLORATION DE L'ARBORESCENCE (Sections > Questions > Réponses) :"
        )

        # On inspecte uniquement la première section pour comprendre la structure
        if sondage_obj.sections:
            premiere_section = sondage_obj.sections[0]
            print(
                f'    ├── Section inspectée : "{premiere_section.nom}" (Ordre: {premiere_section.ordre})'
            )
            print(f"    │   └── Contient {len(premiere_section.questions)} questions.")

            # On inspecte la première question de cette section
            if premiere_section.questions:
                premiere_quest = premiere_section.questions[0]
                print(
                    f'    │   ├── Question inspectée [ID {premiere_quest.id_question}] : "{premiere_quest.intitule}"'
                )
                print(
                    f"    │   │   ├── Type : {premiere_quest.type_question} | Catégorie : {premiere_quest.categorie}"
                )
                print(
                    f"    │   │   ├── Nombre d'options de choix (si QCM) : {len(premiere_quest.options)}"
                )
                print(
                    f"    │   │   └── Nombre de réponses collectées pour cette question : {len(premiere_quest.reponses)}"
                )

                # Aperçu des 3 premières réponses des étudiants à CETTE question précise
                if premiere_quest.reponses:
                    print(
                        f"    │   │       └── Échantillon de réponses brutes (objets Python) :"
                    )
                    for rep in premiere_quest.reponses[:3]:
                        print(
                            f"    │   │           └── <ReponseData> ID: {rep.id_reponse} -> Valeur: '{rep.valeur}'"
                        )

        # --- COMPRENDRE LE PASSAGE DIRECT AU DATAFRAME PANDAS ---
        print("\n" + "=" * 60)
        print("PASSAGE DIRECT AU FORMAT TABLEAU (PANDAS DATAFRAME)")
        print("=" * 60)

        # 1. On extrait la liste de dictionnaires à plat
        dictionnaires_plats = sondage_obj.to_flat_dataframe_records()
        print(
            f"\n[4] L'objet a 'aplatis' l'arborescence en une liste de {len(dictionnaires_plats)} lignes."
        )
        print(f"    Exemple de la toute première ligne (Dictionnaire standard) :")
        if dictionnaires_plats:
            print(f"    {dictionnaires_plats[0]}")

        # 2. On instancie le DataFrame Pandas
        df = pd.DataFrame(dictionnaires_plats)

        print(f"\n[5] DATAFRAME PANDAS CRÉÉ DIRECTEMENT :")
        print(
            f"    └── Dimensions du tableau : {df.shape[0]} lignes (réponses) et {df.shape[1]} colonnes (variables)."
        )
        print(f"\n👇 APERÇU DU TABLEAU PANDAS (df.head()) :")

        # Configuration de pandas pour bien afficher toutes les colonnes dans ton terminal
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 1000)

        # On affiche les 5 premières lignes
        print(df.head(5))
    except Exception as e:
        print(f"\n❌ Erreur lors de l'exploration : {e}")
