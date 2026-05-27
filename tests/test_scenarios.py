"""
Ce fichier se concentre sur les règles métier (Business Logic) et l'expérience de l'utilisateur final.
Il ne cherche pas seulement à savoir si le code plante ou pas, il cherche à savoir si l'application fait ce que le client a demandé (les User Stories)
"""

import pytest
from fastapi.testclient import TestClient
from requests import session
from sqlmodel import SQLModel, Session, create_engine
from unittest.mock import patch
import os
import shutil


# Importation de l'application et des dépendances à surcharger
from app import app, get_session
from auth import get_current_user
from models import Template, Sondage, Section, Question, Option, Module


# 🚨 METS ICI LES CHEMINS VERS TES FICHIERS (Utilise des chemins absolus de préférence)
# Remplace par les vrais noms/emplacements de tes bases de données actuelles
VRAIE_BDD_DEV = os.path.abspath(
    "C:\\Users\\j_blo\\Desktop\\OceENS II\\projet-OceENS\\OceENS\\database\\db_oceens_rempli.db"
)
BDD_POUR_LES_TESTS = os.path.abspath(
    "C:\\Users\\j_blo\\Desktop\\OceENS II\\projet-OceENS\\OceENS\\database\\db_oceens_test.db"
)

# ──────────────────────────────────────────────────────────────────────────────
# 🎛️ FIXTURES & CONFIGURATION DE TEST
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(name="session")
def session_fixture():
    """Crée une copie fraîche de la BDD pour CHAQUE test et gère proprement Windows."""
    if not os.path.exists(VRAIE_BDD_DEV):
        raise FileNotFoundError(f"BDD introuvable : {VRAIE_BDD_DEV}")

    # Copie physique du fichier
    shutil.copy(VRAIE_BDD_DEV, BDD_POUR_LES_TESTS)

    engine = create_engine(
        f"sqlite:///{BDD_POUR_LES_TESTS}", connect_args={"check_same_thread": False}
    )

    # Utilisation de try/finally pour garantir le nettoyage, même en cas de crash
    try:
        with Session(engine) as session:
            yield session
    finally:
        # 🚨 CRUCIAL POUR WINDOWS : Ferme de force toutes les connexions au fichier
        engine.dispose()

        if os.path.exists(BDD_POUR_LES_TESTS):
            try:
                os.remove(BDD_POUR_LES_TESTS)
            except PermissionError:
                pass  # Évite de bloquer pytest si Windows met quelques millisecondes de trop à relâcher le fichier


@pytest.fixture(name="client")
def client_fixture(session):
    """Configure le client de test avec la session de BDD en mémoire."""

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    # follow_redirects=False est CRUCIAL pour pouvoir intercepter les codes 302/307
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture(name="seed_data")
def seed_data_fixture(session):
    """Injecte des données initiales minimales seulement si elles n'existent pas."""
    from models import Template, Section, Question, Option, Sondage, Module
    from sqlmodel import select  # 💡 Import indispensable pour les requêtes

    # 1. Gestion du Template
    template = session.exec(select(Template).where(Template.id_template == 1)).first()
    if not template:
        template = Template(id_template=1, nom="Évaluation Semestre 1")
        session.add(template)
        session.commit()

    # 2. Gestion de la Section
    section = session.exec(
        select(Section).where(Section.id_template == 1, Section.id_section == 1)
    ).first()
    if not section:
        section = Section(id_section=1, id_template=1, nom="Avis Global", ordre=1)
        session.add(section)
        session.commit()

    # 3. Gestion de la Question
    question = session.exec(
        select(Question).where(
            Question.id_template == 1,
            Question.id_section == 1,
            Question.id_question == 1,
        )
    ).first()
    if not question:
        question = Question(
            id_question=1,
            id_template=1,
            id_section=1,
            intitule="Le cours était-il clair ?",
            question_type="unique",
            categorie="cours",
        )
        session.add(question)
        session.commit()

    # 4. Gestion de l'Option
    option = session.exec(
        select(Option).where(
            Option.id_template == 1,
            Option.id_section == 1,
            Option.id_question == 1,
            Option.id_option == 1,
        )
    ).first()
    if not option:
        option = Option(
            id_option=1, id_template=1, id_section=1, id_question=1, intitule="Oui"
        )
        session.add(option)
        session.commit()

    # 5. Gestion du Sondage (Résout l'erreur 'Sondages.Id_Template','Sondages.Id_Sondage')
    sondage = session.exec(
        select(Sondage).where(Sondage.id_template == 1, Sondage.id_sondage == 1)
    ).first()
    if not sondage:
        sondage = Sondage(
            id_template=1,
            id_sondage=1,
            campus="Paris-Cachan",
            formation="Informatique",
            semestre="S1",
            annee_scolaire="2025-2026",
            url="/questionnaire/1/1",
            statut=1,
            id_user=1,
        )
        session.add(sondage)
        session.commit()

    # 6. Gestion du Module (Prévient une future erreur similaire)
    module = session.exec(select(Module).where(Module.id_module == 101)).first()
    if not module:
        module = Module(
            id_module=101,
            nom="Mathématiques",
            enseignant="John Doe",
            ue="UE Scientifique",
            ue_optionnelle=False,
            choix_enseignant=False,
            id_template=1,
            id_sondage=1,
        )
        session.add(module)
        session.commit()

    # On rafraîchit les trois objets principaux dont le test a besoin
    template = session.exec(select(Template).where(Template.id_template == 1)).first()
    sondage = session.exec(
        select(Sondage).where(Sondage.id_template == 1, Sondage.id_sondage == 1)
    ).first()
    module = session.exec(select(Module).where(Module.id_module == 101)).first()

    # 🚨 LA CORRECTION : On referme la transaction implicite ouverte par les 3 requêtes ci-dessus
    session.commit()

    return {"template": template, "sondage": sondage, "module": module}


def mock_auth(role=None):
    """Helper pour simuler l'état d'authentification (rôle ou anonyme)."""
    if role is None:
        app.dependency_overrides[get_current_user] = lambda: None
        return patch("app.get_current_user", return_value=None)
    else:
        user_payload = {
            "name": f"Test {role}",
            "email": f"{role}@epfedu.fr",
            "role": role,
        }
        app.dependency_overrides[get_current_user] = lambda: user_payload
        return patch("app.get_current_user", return_value=user_payload)


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 1. ROUTE D'ACCUEIL (`/`) ET REDIRECTIONS
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_1_accueil_anonyme(client):
    """Scénario 1 : Un visiteur anonyme arrive sur / -> affiche index.html (200)."""
    with mock_auth(role=None):
        response = client.get("/")
        assert response.status_code == 200


def test_scenario_2_accueil_redirect_admin(client):
    """Scénario 2 : Un admin connecté arrive sur / -> redirigé vers son dashboard."""
    with mock_auth(role="admin"):
        response = client.get("/")
        assert response.status_code in [302, 307]
        assert response.headers["location"] == "/dashboard/admin"


def test_scenario_3_accueil_redirect_etudiant(client):
    """Scénario 3 : Un étudiant connecté arrive sur / -> redirigé vers son dashboard."""
    with mock_auth(role="etudiant"):
        response = client.get("/")
        assert response.status_code in [302, 307]
        assert response.headers["location"] == "/dashboard/etudiant"


def test_scenario_4_accueil_redirect_professeur(client):
    """Scénario 4 : Un professeur connecté arrive sur / -> redirigé vers son dashboard."""
    with mock_auth(role="professeur"):
        response = client.get("/")
        assert response.status_code in [302, 307]
        assert response.headers["location"] == "/dashboard/professeur"


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 2. ACCÈS AUX DASHBOARDS PAR RÔLE (`/dashboard/{role}`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_5_etancheite_des_roles(client):
    """Scénario 5 : Un étudiant tente d'aller sur le dashboard admin -> renvoyé chez lui."""
    with mock_auth(role="etudiant"):
        response = client.get("/dashboard/admin")
        assert response.status_code in [302, 307]
        assert response.headers["location"] == "/dashboard/etudiant"


def test_scenario_6_role_inexistant(client):
    """Scénario 6 : Demande d'un dashboard invalide -> redirigé vers la racine /."""
    with mock_auth(role="admin"):
        response = client.get("/dashboard/visiteur")
        assert response.status_code in [302, 307]
        assert response.headers["location"] == "/"


def test_scenario_7_acces_legitime_dashboard(client):
    """Scénario 7 : Un professeur accède à son propre dashboard -> Succès (200)."""
    with mock_auth(role="professeur"):
        response = client.get("/dashboard/professeur")
        assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 3. GESTION DU PARAMÉTRAGE (`/parametrage` et `/api/parametrage`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_8_ihm_parametrage_unauthorized(client, seed_data):
    """Scénario 8 : Un étudiant tente d'accéder à l'IHM de paramétrage -> Bloqué (403)."""
    with mock_auth(role="etudiant"):
        response = client.get("/parametrage")
        assert response.status_code == 403


def test_scenario_9_api_parametrage_access(client, seed_data):
    #  ON SIMULE LA CONNEXION D'UN ADMIN
    with mock_auth(role="admin"):
        response = client.get("/api/parametrage")
        assert response.status_code == 200


def test_scenario_10_api_parametrage_format(client, seed_data):
    """Scénario 10 : L'API renvoie bien les structures attendues (JSON)."""
    with mock_auth(role="admin"):
        response = client.get("/api/parametrage")
        json_data = response.json()
        assert "templates" in json_data
        assert "campusList" in json_data
        assert "filieres" in json_data
        assert "profsList" in json_data


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 4. CRÉATION D'UN SONDAGE (`/api/sondage`)
# ──────────────────────────────────────────────────────────────────────────────

# Conteneur JSON valide pour SondageFullCreate
VALID_SONDAGE_PAYLOAD = {
    "id_template": 1,
    "campus": "Troyes",
    "formation": "Génie Industriel",
    "semestre": "S2",
    "annee_scolaire": "2025-2026",
    "ues": [
        {
            "id": 1,
            "nom": "UE Scientifique",
            "optionnel": False,
            "modules": [
                {
                    "id": 201,
                    "nom": "Physique",
                    "choix_enseignant_exclusif": False,
                    "professeurs": [{"id": 9, "prenom": "Jane", "nom": "Smith"}],
                }
            ],
        }
    ],
}


def test_scenario_11_sondage_security_matrix(client):
    """Scénario 11 : L'étudiant est interdit de créer un sondage (403)."""
    with mock_auth(role="etudiant"):
        response = client.post("/api/sondage", json=VALID_SONDAGE_PAYLOAD)
        assert response.status_code == 403


def test_scenario_12_creation_sondage_nominal(client, seed_data):
    """Scénario 12 : L'admin crée un sondage valide avec succès (200)."""
    with mock_auth(role="admin"):
        response = client.post("/api/sondage", json=VALID_SONDAGE_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sondage cree avec succes"
        assert "id_sondage" in data
        assert "questionnaire_url" in data


def test_scenario_13_incrementation_id_sondage(client, seed_data, session):
    """Scénario 13 : Deux sondages sur le même template incrémentent l'id_sondage (id passe à 2)."""
    from sqlmodel import select, func
    from models import Sondage  # Vérifie le nom de ton modèle

    max_id_avant = session.exec(select(func.max(Sondage.id_sondage))).one()

    if max_id_avant is None:
        max_id_avant = 0
    id_attendu = max_id_avant + 1

    # On valide/ferme la transaction ouverte par le select ci-dessus
    session.commit()

    with mock_auth(role="admin"):
        # seed_data contient déjà l'id_sondage = 1 pour le template 1
        response = client.post("/api/sondage", json=VALID_SONDAGE_PAYLOAD)
        assert response.status_code in [200, 201]
        assert response.json()["id_sondage"] == id_attendu


def test_scenario_14_creation_sondage_invalid_pydantic(client):
    """Scénario 14 : Envoi d'un JSON incomplet (Pydantic rejette avec un 422)."""
    with mock_auth(role="admin"):
        incomplete_payload = {"id_template": 1, "campus": "Montpellier"}
        response = client.post("/api/sondage", json=incomplete_payload)
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 5. CONSULTATION D'UN QUESTIONNAIRE (`/questionnaire/{id_template}/{id_sondage}`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_15_questionnaire_introuvable(client):
    """Scénario 15 : Demande d'un sondage inexistant -> Erreur 404."""
    response = client.get("/questionnaire/999/999")
    assert response.status_code == 404
    assert "Sondage introuvable." in response.text


def test_scenario_16_questionnaire_affichage_nominal(client, seed_data):
    """Scénario 16 : Demande d'un sondage existant -> Affichage HTML réussi (200)."""
    response = client.get("/questionnaire/1/1")
    assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 6. SOUMISSION DES RÉPONSES (`/api/questionnaire/.../reponses`)
# ──────────────────────────────────────────────────────────────────────────────

VALID_SUBMISSION_PAYLOAD = {
    "reponses": [
        {
            "id_section": 1,
            "id_question": 1,
            "valeur": "Oui",
            "module_id": 101,
            "enseignant": "John Doe",
        }
    ]
}


def test_scenario_17_soumission_nominal_succes(client, seed_data):
    """Scénario 17 : Un répondant soumet des réponses valides -> Enregistré (200)."""
    response = client.post(
        "/api/questionnaire/1/1/reponses", json=VALID_SUBMISSION_PAYLOAD
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Reponses enregistrees avec succes"
    assert "id_repondant" in data


def test_scenario_18_soumission_sondage_fantome(client):
    """Scénario 18 : Soumission sur un sondage inexistant -> Erreur 404."""
    response = client.post(
        "/api/questionnaire/999/999/reponses", json=VALID_SUBMISSION_PAYLOAD
    )
    assert response.status_code == 404
    assert response.json() == {"error": "Sondage introuvable"}
