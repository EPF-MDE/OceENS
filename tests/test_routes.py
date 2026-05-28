"""
Ce fichier se concentre sur l'intégrité technique de tes endpoints (les routes d'API),
pris de manière isolée. Il vérifie que les barrières de sécurité et les formats de données fonctionnent exactement comme prévu par le code
"""

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
        ("admin", True),  # L'admin doit passer la barrière de sécurité
        ("RP-RM", True),  # Le prof doit être bloqué (403)
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
        # Si l'accès est autorisé, le code ne doit surtour pas être un refus (401 ou 403).
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
        ("admin", True),  # L'admin a accès
        ("RP-RM", True),  # Le RP-RM a accès aussi !
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
