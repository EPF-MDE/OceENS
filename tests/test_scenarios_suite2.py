"""
SUITE de test_scenarios.py — Scénarios 19 à 32

Ce fichier continue le fichier test_scenarios.py existant (scénarios 1–18).
Il couvre les cas non testés : soumission de réponses (cas d'erreur),
modules précédents, import d'étudiants, gestion des rôles utilisateurs,
et les fonctions utilitaires pures.

Structure identique au fichier original :
- Même fixture `session` (copie physique de la BDD de dev)
- Même fixture `client` (surcharge de get_session)
- Même fixture `seed_data` (données minimales)
- Même helper `mock_auth`
"""

import io
import os
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select, text

from app import app, get_session
from auth import get_current_user, _is_email_allowed
from models import Template, Sondage, Section, Question, Option, Module, User, Repondre


# ─── CHEMINS BDD (identiques à test_scenarios.py original) ────────────────────
VRAIE_BDD_DEV = os.path.abspath(
    "C:\\Users\\j_blo\\Desktop\\OceENS II\\projet-OceENS\\OceENS\\database\\db_oceens_rempli.db"
)
BDD_POUR_LES_TESTS = os.path.abspath(
    "C:\\Users\\j_blo\\Desktop\\OceENS II\\projet-OceENS\\OceENS\\database\\db_oceens_test_suite2.db"
)


# ─── FIXTURES (identiques au fichier original) ────────────────────────────────


@pytest.fixture(name="session")
def session_fixture():
    """Crée une copie fraîche de la BDD pour CHAQUE test."""
    if not os.path.exists(VRAIE_BDD_DEV):
        raise FileNotFoundError(f"BDD introuvable : {VRAIE_BDD_DEV}")

    shutil.copy(VRAIE_BDD_DEV, BDD_POUR_LES_TESTS)

    engine = create_engine(
        f"sqlite:///{BDD_POUR_LES_TESTS}", connect_args={"check_same_thread": False}
    )

    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()
        if os.path.exists(BDD_POUR_LES_TESTS):
            try:
                os.remove(BDD_POUR_LES_TESTS)
            except PermissionError:
                pass


@pytest.fixture(name="client")
def client_fixture(session):
    """Configure le client de test avec la session de BDD surchargée."""

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.clear()


@pytest.fixture(name="seed_data")
def seed_data_fixture(session):
    """Injecte des données minimales si elles n'existent pas encore."""

    # Template
    template = session.exec(select(Template).where(Template.id_template == 1)).first()
    if not template:
        template = Template(id_template=1, nom="Évaluation Semestre 1")
        session.add(template)
        session.commit()

    # Section
    section = session.exec(
        select(Section).where(Section.id_template == 1, Section.id_section == 1)
    ).first()
    if not section:
        section = Section(id_section=1, id_template=1, nom="Avis Global", ordre=1)
        session.add(section)
        session.commit()

    # Question
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

    # Option
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

    # Sondage
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

    # Module
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

    # Rafraîchissement
    template = session.exec(select(Template).where(Template.id_template == 1)).first()
    sondage = session.exec(
        select(Sondage).where(Sondage.id_template == 1, Sondage.id_sondage == 1)
    ).first()
    module = session.exec(select(Module).where(Module.id_module == 101)).first()
    session.commit()

    return {"template": template, "sondage": sondage, "module": module}


def mock_auth(role=None):
    """Helper pour simuler l'état d'authentification."""
    from unittest.mock import patch

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


# Payload réutilisable pour les tests de soumission
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


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 6 (SUITE). SOUMISSION DES RÉPONSES — CAS D'ERREUR
# Rappel : les scénarios 17 (succès) et 18 (sondage fantôme) sont dans le fichier original.
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_19_soumission_utilisateur_non_authentifie(client, seed_data):
    """
    Scénario 19 : Un utilisateur anonyme tente de soumettre des réponses → 401 ou 403.

    La route /api/questionnaire/.../reponses appelle get_current_user(request).
    Sans utilisateur en session, cette fonction lève une HTTPException 401.
    Ce test vérifie que le mur d'authentification est bien là, même sans Depends().
    """
    with mock_auth(role=None):
        response = client.post(
            "/api/questionnaire/1/1/reponses", json=VALID_SUBMISSION_PAYLOAD
        )
    assert response.status_code in [401, 403]


def test_scenario_20_soumission_etudiant_non_assigne(client, seed_data, session):
    """
    Scénario 20 : Un étudiant valide mais non assigné au sondage tente de répondre → 403.

    La route fait deux vérifications dans l'ordre :
      1. L'utilisateur existe-t-il en BDD (par email) ?  → sinon 403 "non trouvé"
      2. A-t-il une ligne dans Repondre pour ce sondage ? → sinon 403 "non assigné"

    Ce test couvre le cas 2 : l'utilisateur est en BDD mais absent de Repondre.
    On insère donc le User avec le même email que celui renvoyé par get_current_user,
    mais on ne crée PAS de ligne Repondre.
    """
    EMAIL = "non_assigne@epfedu.fr"

    # SQL brut : on détecte les vrais noms de colonnes via PRAGMA
    # pour être indépendant du mapping SQLAlchemy
    cols = {
        r[1].lower(): r[1]
        for r in session.execute(text("PRAGMA table_info(Users)")).fetchall()
    }
    mail_col = cols.get("mail", "Mail")
    role_col = cols.get("role", "Role")
    pk_col = next((v for k, v in cols.items() if k in ("id_user", "id")), "Id_User")

    already = session.execute(
        text(f"SELECT 1 FROM Users WHERE {mail_col} = :e"), {"e": EMAIL}
    ).first()
    if not already:
        max_id = session.execute(text(f"SELECT MAX({pk_col}) FROM Users")).scalar() or 0
        session.execute(
            text(
                f"INSERT INTO Users ({pk_col}, {mail_col}, {role_col}) VALUES (:id, :m, :r)"
            ),
            {"id": max_id + 1, "m": EMAIL, "r": "Etudiant"},
        )
        session.commit()

    # get_current_user retourne cet email → la route le trouve en BDD
    # mais il n'a PAS de ligne dans Repondre → doit retourner 403
    app.dependency_overrides[get_current_user] = lambda: {
        "name": "Non Assigné",
        "email": EMAIL,
        "role": "Etudiant",
    }
    response = client.post(
        "/api/questionnaire/1/1/reponses", json=VALID_SUBMISSION_PAYLOAD
    )
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert (
        "autorisé" in response.json()["error"] or "assigné" in response.json()["error"]
    )


def test_scenario_21_soumission_doublon_interdit(client, seed_data, session):
    """
    Scénario 21 : Un étudiant soumet ses réponses deux fois → 409 Conflict au second envoi.

    La route vérifie repondre.repondu. Si True, elle retourne 409 avec le message
    "Vous avez déjà soumis vos réponses pour ce sondage."

    On crée un User + une ligne Repondre déjà marquée repondu=True pour simuler
    une soumission préalable.

    Note : le nom du champ SQLAlchemy doit correspondre exactement à la colonne BDD.
    Si la colonne s'appelle "Date_soumission" dans le schéma, on passe None ici
    (la route ne lit pas ce champ, elle vérifie seulement repondu=True).
    """
    EMAIL = "deja_repondu@epfedu.fr"

    # SQL brut pour Users
    ucols = {
        r[1].lower(): r[1]
        for r in session.execute(text("PRAGMA table_info(Users)")).fetchall()
    }
    mail_col = ucols.get("mail", "Mail")
    role_col = ucols.get("role", "Role")
    pk_col = next((v for k, v in ucols.items() if k in ("id_user", "id")), "Id_User")

    row = session.execute(
        text(f"SELECT {pk_col} FROM Users WHERE {mail_col} = :e"), {"e": EMAIL}
    ).first()
    if not row:
        max_id = session.execute(text(f"SELECT MAX({pk_col}) FROM Users")).scalar() or 0
        new_id = max_id + 1
        session.execute(
            text(
                f"INSERT INTO Users ({pk_col}, {mail_col}, {role_col}) VALUES (:id, :m, :r)"
            ),
            {"id": new_id, "m": EMAIL, "r": "Etudiant"},
        )
        session.commit()
        user_id = new_id
    else:
        user_id = row[0]

    # SQL brut pour Repondre : on détecte les colonnes disponibles
    rcols = {
        r[1].lower(): r[1]
        for r in session.execute(text("PRAGMA table_info(Repondre)")).fetchall()
    }
    rid_template = rcols.get("id_template", "Id_Template")
    rid_sondage = rcols.get("id_sondage", "Id_Sondage")
    rid_user = rcols.get("id_user", "Id_User")
    rrepondu = rcols.get("repondu", "Repondu")

    session.execute(
        text(
            f"INSERT INTO Repondre ({rid_template}, {rid_sondage}, {rid_user}, {rrepondu}) "
            f"VALUES (:t, :s, :u, 1)"
        ),
        {"t": 1, "s": 1, "u": user_id},
    )
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: {
        "name": "Déjà Répondu",
        "email": EMAIL,
        "role": "Etudiant",
    }
    response = client.post(
        "/api/questionnaire/1/1/reponses", json=VALID_SUBMISSION_PAYLOAD
    )
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "déjà soumis" in response.json()["error"]


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 7. MODULES DE L'ANNÉE PRÉCÉDENTE (`/api/modules-precedents`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_22_modules_precedents_params_manquants(client):
    """
    Scénario 22 : Appel sans paramètres → retourne des listes vides (200), pas une erreur.

    La route vérifie en tête : if not semestre or not formation or not annee_scolaire.
    Si l'un des trois manque, elle retourne {"ues": [], "profsList": []} sans toucher la BDD.
    Ce test vérifie ce comportement de "réponse vide propre" plutôt qu'un 422.
    """
    response = client.get("/api/modules-precedents")
    assert response.status_code == 200
    data = response.json()
    assert data == {"ues": [], "profsList": []}


def test_scenario_23_modules_precedents_annee_precedente_inexistante(client, seed_data):
    """
    Scénario 23 : Paramètres valides mais aucun sondage pour l'année N-1 → listes vides (200).

    La BDD de test ne contient des données que pour 2025-2026 (seed_data).
    On demande 2026-2027 → la route cherche 2025-2026 (qui existe) mais pour
    une formation différente → introuvable → retourne {"ues": [], "profsList": []}.

    Cela vérifie que la route ne plante pas sur un sondage_precedent=None.
    """
    response = client.get(
        "/api/modules-precedents",
        params={
            "semestre": "S1",
            "formation": "Formation Inexistante",
            "annee_scolaire": "2026-2027",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ues"] == []
    assert data["profsList"] == []


def test_scenario_24_modules_precedents_annee_trouvee(client, seed_data, session):
    """
    Scénario 24 : Sondage de l'année N-1 trouvé → retourne les UEs et modules (200).

    On insère un sondage pour 2024-2025 (= N-1 de 2025-2026) avec un module,
    puis on demande 2025-2026. La route doit retrouver le sondage 2024-2025
    et retourner ses modules correctement structurés.

    Note : la table Sondages a une contrainte NOT NULL sur Id_User — on réutilise
    l'id_user=1 du seed_data pour satisfaire cette contrainte sans créer de données
    supplémentaires.
    """
    # SQL brut pour Sondages : on détecte les vrais noms de colonnes
    scols = {
        r[1].lower(): r[1]
        for r in session.execute(text("PRAGMA table_info(Sondages)")).fetchall()
    }
    # Trouver un id_user existant pour satisfaire la contrainte NOT NULL
    upk = next((v for k, v in scols.items() if k in ("id_user", "id")), "Id_User")
    any_uid = session.execute(text(f"SELECT MIN({upk}) FROM Users")).scalar() or 1

    # Construire l'INSERT dynamiquement avec les colonnes présentes
    def sc(name):
        return scols.get(name.lower(), name)

    session.execute(
        text(
            f"INSERT INTO Sondages ({sc('Id_Template')}, {sc('Id_Sondage')}, "
            f"{sc('Campus')}, {sc('Formation')}, {sc('Semestre')}, "
            f"{sc('Annee_scolaire')}, {sc('Url')}, {sc('Statut')}, {sc('Id_User')}) "
            f"VALUES (1, 99, :campus, :formation, :sem, :annee, :url, 1, :uid)"
        ),
        {
            "campus": "Paris-Cachan",
            "formation": "Informatique",
            "sem": "S1",
            "annee": "2024-2025",
            "url": "/questionnaire/1/99",
            "uid": any_uid,
        },
    )
    session.commit()

    # SQL brut pour Modules
    mcols = {
        r[1].lower(): r[1]
        for r in session.execute(text("PRAGMA table_info(Modules)")).fetchall()
    }

    def mc(name):
        return mcols.get(name.lower(), name)

    session.execute(
        text(
            f"INSERT INTO Modules ({mc('Id_Module')}, {mc('Nom')}, {mc('Enseignant')}, "
            f"{mc('UE')}, {mc('UE_optionnelle')}, {mc('Choix_enseignant')}, "
            f"{mc('Id_Template')}, {mc('Id_Sondage')}) "
            f"VALUES (999, :nom, :ens, :ue, 0, 0, 1, 99)"
        ),
        {"nom": "Algorithmique", "ens": "Alice Martin", "ue": "UE Info"},
    )
    session.commit()

    response = client.get(
        "/api/modules-precedents",
        params={
            "semestre": "S1",
            "formation": "Informatique",
            "annee_scolaire": "2025-2026",
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Il doit y avoir au moins une UE et au moins un prof
    assert len(data["ues"]) >= 1
    assert len(data["profsList"]) >= 1
    assert data["annee_precedente"] == "2024-2025"
    assert data["sondage_id"] == 99


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 8. IMPORT D'ÉTUDIANTS (`/api/import-etudiants`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_25_import_sondage_inexistant(client, seed_data):
    """
    Scénario 25 : Import sur un sondage inexistant (id_template=999) → 404.

    La route vérifie l'existence du sondage avant de traiter le fichier.
    Ce test s'assure que le guard "sondage introuvable" fonctionne et renvoie 404
    même si le fichier est valide.
    """
    # On crée un vrai fichier xlsx minimal avec openpyxl
    try:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["email"])
        ws.append(["etudiant@epfedu.fr"])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        xlsx_content = buffer.read()
    except ImportError:
        pytest.skip("openpyxl non disponible")

    response = client.post(
        "/api/import-etudiants",
        data={"id_sondage": "999", "id_template": "999"},
        files={
            "file": (
                "etudiants.xlsx",
                io.BytesIO(xlsx_content),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 404
    assert "introuvable" in response.json()["error"].lower()


def test_scenario_26_import_format_invalide(client, seed_data):
    """
    Scénario 26 : Envoi d'un fichier .csv au lieu de .xlsx → 400 immédiat.

    La validation du type de fichier est la première chose que fait la route.
    Elle ne doit pas essayer de lire le fichier : le rejet doit être immédiat et clair.
    """
    fake_csv = io.BytesIO(b"email\ntest@epfedu.fr\n")
    response = client.post(
        "/api/import-etudiants",
        data={"id_sondage": "1", "id_template": "1"},
        files={"file": ("liste.csv", fake_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "xlsx" in response.json()["error"].lower()


def test_scenario_27_import_nominal_succes(client, seed_data, session):
    """
    Scénario 27 : Import réussi d'un .xlsx valide contenant des emails → 200 avec compteurs.

    On construit un vrai fichier xlsx avec openpyxl, on le passe à la route,
    et on vérifie que la réponse contient les compteurs attendus :
    - nb_emails_lus ≥ 1
    - la somme nb_users_crees + nb_users_existants == nb_emails_lus

    Ce test est le "happy path" de l'import.
    """
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl non disponible")

    wb = openpyxl.Workbook()
    ws = wb.active
    # Pas d'en-tête : la route lit la colonne 1 directement
    ws.append(["nouveau1@epfedu.fr"])
    ws.append(["nouveau2@epfedu.fr"])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = client.post(
        "/api/import-etudiants",
        data={"id_sondage": "1", "id_template": "1"},
        files={
            "file": (
                "etudiants.xlsx",
                buffer,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nb_emails_lus"] == 2
    assert data["nb_users_crees"] + data["nb_users_existants"] == data["nb_emails_lus"]
    assert "nb_repondre_inseres" in data


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 9. GESTION DES RÔLES UTILISATEURS (`/api/users` et `PUT /api/users/{id}/role`)
# ──────────────────────────────────────────────────────────────────────────────


def test_scenario_28_update_role_succes(client, seed_data, session):
    """
    Scénario 28 : Modifier le rôle d'un utilisateur existant → 200 avec le nouveau rôle.

    On crée un user directement en BDD, puis on change son rôle via l'API.
    La réponse doit refléter le nouveau rôle et les infos du user.
    """
    # Créer un user cible
    user_cible = User(id_user=8001, mail="cible@epfedu.fr", role="Etudiant")
    session.add(user_cible)
    session.commit()

    response = client.put("/api/users/8001/role", json={"role": "Admin"})

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "Admin"
    assert data["mail"] == "cible@epfedu.fr"


def test_scenario_29_update_role_user_inexistant(client, seed_data):
    """
    Scénario 29 : Tenter de modifier le rôle d'un user qui n'existe pas → 404.

    La route fait session.get(User, id_user). Si None, elle retourne 404.
    Ce test vérifie que l'erreur est propre (404) et non un crash (500).
    """
    response = client.put("/api/users/99999/role", json={"role": "Etudiant"})
    assert response.status_code == 404
    assert "introuvable" in response.json()["detail"].lower()


def test_scenario_30_update_role_invalide(client, seed_data):
    """
    Scénario 30 : Envoyer un rôle hors de la liste autorisée → 422.

    VALID_USER_ROLES = {"Admin", "Etudiant", "RP-RM"}.
    Tout autre valeur (y compris casse incorrecte comme "admin") doit retourner 422
    avec un message expliquant que le rôle est invalide.
    """
    response = client.put("/api/users/1/role", json={"role": "SuperHero"})
    assert response.status_code == 422
    assert "invalide" in response.json()["detail"].lower()


def test_scenario_31_liste_users_retourne_tableau(client, seed_data, session):
    """
    Scénario 31 : GET /api/users retourne bien une liste d'objets avec les bons champs.

    On vérifie le format de la réponse : tableau JSON, chaque item a id_user, mail, role.
    La BDD de test contient au moins un user (injecté par seed_data ou la vraie BDD).
    """
    response = client.get("/api/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    if len(data) > 0:
        premier = data[0]
        assert "id_user" in premier
        assert "mail" in premier
        assert "role" in premier


# ──────────────────────────────────────────────────────────────────────────────
# 🎯 10. FONCTIONS UTILITAIRES PURES (sans BDD, sans HTTP)
# ──────────────────────────────────────────────────────────────────────────────
# Ces tests sont rapides et stables : ils testent les fonctions de logique pure
# directement, sans passer par le serveur HTTP.


class TestIsEmailAllowed:
    """
    Tests unitaires de la fonction _is_email_allowed() dans auth.py.

    Cette fonction vérifie si un email appartient à un domaine autorisé
    (défini via la variable d'env ALLOWED_DOMAINS).
    """

    def test_scenario_32a_domaine_autorise(self, monkeypatch):
        """
        Scénario 32a : Email d'un domaine présent dans ALLOWED_DOMAINS → True.
        """
        import auth

        monkeypatch.setattr(auth, "ALLOWED_DOMAINS", ["epfedu.fr", "example.com"])
        assert auth._is_email_allowed("etudiant@epfedu.fr") is True

    def test_scenario_32b_domaine_non_autorise(self, monkeypatch):
        """
        Scénario 32b : Email d'un domaine absent → False.

        Un attaquant avec un compte @gmail.com ne doit pas pouvoir se connecter.
        """
        import auth

        monkeypatch.setattr(auth, "ALLOWED_DOMAINS", ["epfedu.fr"])
        assert auth._is_email_allowed("pirate@gmail.com") is False

    def test_scenario_32c_email_vide(self, monkeypatch):
        """
        Scénario 32c : Email vide ("") → False, sans lever d'exception.

        La fonction commence par `if not email: return False`.
        Ce test vérifie qu'elle ne plante pas sur une chaîne vide.
        """
        import auth

        monkeypatch.setattr(auth, "ALLOWED_DOMAINS", ["epfedu.fr"])
        assert auth._is_email_allowed("") is False

    def test_scenario_32d_insensibilite_casse_domaine(self, monkeypatch):
        """
        Scénario 32d : Le domaine est comparé en minuscules → True même avec majuscules.

        La fonction applique .lower() sur le domaine extrait.
        Ce test vérifie que "EPFedu.FR" est reconnu si "epfedu.fr" est dans ALLOWED_DOMAINS.
        """
        import auth

        monkeypatch.setattr(auth, "ALLOWED_DOMAINS", ["epfedu.fr"])
        assert auth._is_email_allowed("user@EPFedu.FR") is True


class TestRoleToDashboardSlug:
    """
    Tests unitaires de role_to_dashboard_slug() dans app.py.

    Cette fonction convertit le rôle BDD ("Admin", "RP-RM:...") en slug de route.
    """

    def test_scenario_33a_admin(self):
        """
        Scénario 33a : "Admin" → "admin".
        """
        from app import role_to_dashboard_slug

        assert role_to_dashboard_slug("Admin") == "admin"

    def test_scenario_33b_rprm_simple(self):
        """
        Scénario 33b : "RP-RM" (sans suffixe) → "rprm".

        La condition est startswith("RP-RM") donc "RP-RM" seul doit donner "rprm".
        """
        from app import role_to_dashboard_slug

        assert role_to_dashboard_slug("RP-RM") == "rprm"

    def test_scenario_33c_rprm_avec_formation(self):
        """
        Scénario 33c : "RP-RM:MDE_P2027-MIN_P2027" → "rprm".

        Le cas le plus courant en production : un RP-RM a une formation associée.
        """
        from app import role_to_dashboard_slug

        assert role_to_dashboard_slug("RP-RM:MDE_P2027-MIN_P2027") == "rprm"

    def test_scenario_33d_etudiant(self):
        """
        Scénario 33d : "Etudiant" → "etudiant".
        """
        from app import role_to_dashboard_slug

        assert role_to_dashboard_slug("Etudiant") == "etudiant"

    def test_scenario_33e_role_inconnu(self):
        """
        Scénario 33e : Rôle inconnu ("Visiteur") → "etudiant" (fallback par défaut).

        La fonction n'a pas de cas "else unknown" : tout ce qui n'est pas Admin ou RP-RM
        tombe dans le else → "etudiant". C'est le comportement sécurisé attendu.
        """
        from app import role_to_dashboard_slug

        assert role_to_dashboard_slug("Visiteur") == "etudiant"
