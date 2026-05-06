"""=============================================================================
Script de remplissage initial de la base de données (données de test)
=============================================================================

Ce script permet de peupler la base de données SQLite avec des utilisateurs
et leurs rôles correspondants. Utile pour :
- Tester l'application avec des données réalistes
- Ajouter manuellement des utilisateurs
- Initialiser les données d'administration

Utilisation :
    python remplir_db.py

Rôles disponibles :
    - "etudiant" : Accès au dashboard étudiant (défaut)
    - "professeur" : Accès au dashboard professeur
    - "admin" : Accès au dashboard administrateur

Note : Ce script ne doit être exécuté qu'une fois (ou adapté pour éviter
les doublons si les emails sont unique primaire).
"""

from database import SessionLocal, UserRole

# ┌─ Ouverture de la connexion à la base de données ───────────────────────────┐
# SessionLocal() crée une nouvelle session/connexion à la BDD
db = SessionLocal()
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Création d'instances utilisateur ─────────────────────────────────────────┐
# Crée les objets Python qui représentent les lignes de table

# Exemple 1 : Un simple étudiant (rôle par défaut, pas besoin de le spécifier)
# etudiant_1 = UserRole(email="jules.dupont@epfedu.fr")  # Rôle par défaut: "etudiant"

# Exemple 2 : Un professeur
prof_1 = UserRole(email="julien.blondiaux@epfedu.fr", role="professeur")

# Exemple 3 : Un administrateur
admin_1 = UserRole(email="marie.bouafou@epfedu.fr", role="admin")
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Ajout à la session et validation ─────────────────────────────────────────┐
# La session fonctionne comme un "panier" avant de payer
# On ajoute les objets, puis on valide (commit) pour écrire dans la BDD

# Ajoute les utilisateurs à la session
db.add(prof_1)
db.add(admin_1)
# db.add(etudiant_1)  # Décommentez si vous voulez ajouter l'étudiant

# Valide les changements (écrit les données dans le fichier SQLite)
try:
    db.commit()
    print("✓ Données insérées avec succès !")
except Exception as e:
    # En cas d'erreur (ex: email déjà existant), annule tout
    print(f"✗ Erreur : {e}")
    db.rollback()  # Annule la transaction en cas de problème
finally:
    # Ferme la connexion proprement (importante pour libérer les ressources)
    db.close()
# └───────────────────────────────────────────────────────────────────────────┘
