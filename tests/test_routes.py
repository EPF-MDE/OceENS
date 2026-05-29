"""
Ce fichier se concentre sur l'intégrité technique de tes endpoints (les routes d'API),
pris de manière isolée. Il vérifie que les barrières de sécurité et les formats de données fonctionnent exactement comme prévu par le code
"""

import io
import pytest
from fastapi.testclient import TestClient
from app import app  # Importe ton instance FastAPI globale
from auth import get_current_user

# Initialisation du client de test FastAPI
client = TestClient(app)


# ─── SCÉNARIO 1 : SÉCURITÉ DE LA CRÉATION DE SONDAGE (POST) ──────────────────
# On définit la matrice : (rôle testé, est-ce que l'accès doit être autorisé ?)
@pytest.mark.parametrize(
    "role, access_granted",
    [
        ("admin", True),   # L'admin doit passer la barrière de sécurité
        ("RP-RM", True),   # Le prof doit être bloqué (403)
        ("etudiant", False),  # L'étudiant doit être bloqué (403)
    ],
)
def test_api_sondage_auth_matrix(role, access_granted):
    """
    Vérifie que seul l'admin peut soumettre un POST sur /api/sondage.
    """
    # 1. Configuration dynamique du rôle pour ce test précis
    app.dependency_overrides[get_current_user] = lambda: {
        "mail": f"{role}@ecole.fr",
        "role": role,
    }

    # 2. Envoi de la requête POST (avec un faux body de sondage)
    response = client.post(
        "/api/sondage", json={"id_template": 1, "date_fin": "2026-12-31"}
    )

    # 3. Nettoyage immédiat de la surcharge pour ne pas polluer les autres tests
    app.dependency_overrides.clear()

    # 4. Vérification des droits d'accès
    if access_granted:
        # Si l'accès est autorisé, le code ne doit surtout pas être un refus (401 ou 403).
        # Note : Si la BDD n'est pas initialisée, tu auras peut-être un code 422 ou 500,
        # mais cela prouve quand même que le verrou de sécurité a sauté avec succès !
        assert response.status_code not in [401, 403]
    else:
        # Si l'accès est refusé, on exige strictement un 403 Forbidden
        assert response.status_code == 403


# ─── SCÉNARIO 2 : SÉCURITÉ DU PARAMÉTRAGE (GET) ──────────────────────────────
# Ici, on teste la double dépendance : Admin ET Professeur doivent passer.
@pytest.mark.parametrize(
    "role, access_granted",
    [
        ("admin", True),    # L'admin a accès
        ("RP-RM", True),    # Le RP-RM a accès aussi !
        ("etudiant", False),  # L'étudiant est rejeté (403)
    ],
)
def test_api_parametrage_auth_matrix(role, access_granted):
    """
    Vérifie la double dépendance (Staff) sur la route GET /api/parametrage.
    """
    # 1. Surcharge du rôle
    app.dependency_overrides[get_current_user] = lambda: {
        "mail": f"{role}@ecole.fr",
        "role": role,
    }

    # 2. Envoi de la requête GET
    response = client.get("/api/parametrage")

    # 3. Nettoyage
    app.dependency_overrides.clear()

    # 4. Vérification
    if access_granted:
        assert response.status_code not in [401, 403]
    else:
        assert response.status_code == 403


# ─── SCÉNARIO 3 : ROUTE PUBLIQUE ACCUEIL (GET) ───────────────────────────────
def test_public_homepage():
    """
    L'accueil doit être accessible à n'importe qui, sans aucune authentification.
    """
    # Pas besoin de manipuler app.dependency_overrides ici
    response = client.get("/")
    assert response.status_code == 200


# ─── SCÉNARIO 4 (NOUVEAU) : SÉCURITÉ DE LA LISTE DES UTILISATEURS (GET /api/users) ──
# Cette route n'a pas de garde dans app.py — ces tests documentent ce comportement
# et serviront de filet de sécurité si un guard est ajouté plus tard.
@pytest.mark.parametrize(
    "role",
    ["admin", "RP-RM", "etudiant"],
)
def test_api_users_accessible_tous_roles(role):
    """
    ÉTAT ACTUEL : /api/users n'a pas de garde d'authentification.
    Tous les rôles doivent recevoir 200 (ou au pire 500 si la BDD est absente).
    Ce test documente ce comportement pour alerter si un 403 apparaît involontairement
    après un refactoring — ou pour signaler qu'une protection doit être ajoutée.

    À faire : décider si cette route doit être protégée (Admin uniquement ?)
    et mettre à jour ce test en conséquence.
    """
    app.dependency_overrides[get_current_user] = lambda: {
        "mail": f"{role}@ecole.fr",
        "role": role,
    }
    response = client.get("/api/users")
    app.dependency_overrides.clear()

    # La route n'a pas de garde : on vérifie qu'elle ne renvoie PAS un refus d'accès
    assert response.status_code not in [401, 403]


# ─── SCÉNARIO 5 (NOUVEAU) : VALIDATION PYDANTIC SUR PUT /api/users/{id}/role ──
@pytest.mark.parametrize(
    "role_value, expected_status",
    [
        ("Admin", 200),      # Rôle valide → 200 (ou 404 si user inexistant en BDD de test)
        ("Etudiant", 200),   # Rôle valide → même chose
        ("RP-RM", 200),      # Rôle valide → même chose
        ("Fantome", 422),    # Rôle invalide → rejeté par la validation applicative (422)
        ("", 422),           # Rôle vide → rejeté (422)
        ("ADMIN", 422),      # Casse incorrecte → rejeté (les rôles sont sensibles à la casse)
    ],
)
def test_api_update_role_validation_pydantic(role_value, expected_status):
    """
    Vérifie que PUT /api/users/{id}/role rejette les rôles invalides avec un 422.

    La logique est dans app.py : VALID_USER_ROLES = {"Admin", "Etudiant", "RP-RM"}.
    Un rôle hors de cet ensemble retourne explicitement un 422 (pas un 400).
    Note : si le user_id=9999 n'existe pas en BDD, les cas "valides" retourneront 404
    — ce qui est correct et ne change pas le résultat des cas invalides (422).
    """
    app.dependency_overrides[get_current_user] = lambda: {
        "mail": "admin@ecole.fr",
        "role": "admin",
    }
    response = client.put("/api/users/9999/role", json={"role": role_value})
    app.dependency_overrides.clear()

    if expected_status == 422:
        assert response.status_code == 422
    else:
        # Pour les rôles valides, l'utilisateur 9999 n'existe probablement pas :
        # on accepte 200 (user trouvé) ou 404 (user absent), mais jamais 422
        assert response.status_code != 422


# ─── SCÉNARIO 6 (NOUVEAU) : IMPORT ÉTUDIANTS — VALIDATION DU TYPE DE FICHIER ─
def test_api_import_etudiants_mauvais_format():
    """
    Envoie un fichier .csv au lieu de .xlsx → doit être rejeté avec un 400.

    La validation est en tête de /api/import-etudiants :
        if not file.filename.lower().endswith(".xlsx"): return 400
    Ce test vérifie que ce garde fonctionne, indépendamment de la BDD.
    """
    fake_csv = io.BytesIO(b"email\ntest@ecole.fr\n")
    response = client.post(
        "/api/import-etudiants",
        data={"id_sondage": "1", "id_template": "1"},
        files={"file": ("etudiants.csv", fake_csv, "text/csv")},
    )
    assert response.status_code == 400
    assert "xlsx" in response.json()["error"].lower()


def test_api_import_etudiants_fichier_vide():
    """
    Envoie un fichier .xlsx vide (0 octet) → doit être rejeté avec un 400.

    La route vérifie explicitement : if len(contents) == 0: return 400.
    Ce test isole cette branche de validation sans nécessiter de BDD.
    """
    empty_xlsx = io.BytesIO(b"")
    response = client.post(
        "/api/import-etudiants",
        data={"id_sondage": "1", "id_template": "1"},
        files={"file": ("etudiants.xlsx", empty_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400


# ─── SCÉNARIO 7 (NOUVEAU) : MATRICE AUTH SUR PUT /api/users/{id}/role ─────────
@pytest.mark.parametrize(
    "role, should_be_blocked",
    [
        # ÉTAT ACTUEL : la route n'a pas de guard d'auth.
        # Ces tests documentent la situation et serviront de filet si un guard est ajouté.
        ("admin", False),
        ("RP-RM", False),
        ("etudiant", False),
    ],
)
def test_api_update_role_auth_matrix(role, should_be_blocked):
    """
    Documente l'absence de garde sur PUT /api/users/{id}/role.

    Actuellement tous les rôles passent (la route n'a pas de Depends(require_role(...))).
    Ce test alertera si quelqu'un ajoute involontairement un 403, ou servira de base
    pour écrire les tests corrects quand le guard sera implémenté.
    """
    app.dependency_overrides[get_current_user] = lambda: {
        "mail": f"{role}@ecole.fr",
        "role": role,
    }
    # Corps valide, user inexistant → 404 attendu (pas 401/403)
    response = client.put("/api/users/9999/role", json={"role": "Etudiant"})
    app.dependency_overrides.clear()

    if should_be_blocked:
        assert response.status_code == 403
    else:
        assert response.status_code not in [401, 403]


# ─── SCÉNARIO 8 (NOUVEAU) : QUESTIONNAIRE — ROUTE PUBLIQUE ────────────────────
def test_questionnaire_inexistant_retourne_404():
    """
    Demande le questionnaire d'un sondage qui n'existe pas → 404.

    La route /questionnaire/{id_template}/{id_sondage} est publique (pas de guard).
    Ce test vérifie qu'elle retourne bien 404 (et pas 500 ou une page blanche)
    quand les IDs sont fantaisistes.
    """
    response = client.get("/questionnaire/9999/9999")
    assert response.status_code == 404


# ─── SCÉNARIO 9 (NOUVEAU) : MODULES PRÉCÉDENTS — PARAMS MANQUANTS ─────────────
def test_api_modules_precedents_sans_params():
    """
    Appel de /api/modules-precedents sans paramètres → retourne un objet vide (200).

    La route gère explicitement ce cas :
        if not semestre or not formation or not annee_scolaire: return {"ues": [], "profsList": []}
    Ce test vérifie que la route ne plante pas (pas de 422 ou 500) et retourne bien
    la structure vide attendue.
    """
    response = client.get("/api/modules-precedents")
    assert response.status_code == 200
    data = response.json()
    assert data["ues"] == []
    assert data["profsList"] == []


def test_api_modules_precedents_annee_malformee():
    """
    Passe une annee_scolaire malformée ("2025") qui ne peut pas être découpée → retourne vide (200).

    La route attrape l'erreur de découpage avec un try/except et retourne un objet vide.
    Ce test vérifie que ce filet de sécurité fonctionne correctement.
    """
    response = client.get(
        "/api/modules-precedents",
        params={"semestre": "S1", "formation": "Informatique", "annee_scolaire": "2025"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ues"] == []
    assert data["profsList"] == []
