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
from database import SessionLocal, UserAuth

# ┌─ Ouverture de la connexion à la base de données ───────────────────────────┐
# SessionLocal() crée une nouvelle session/connexion à la BDD db_oceens.db
db = SessionLocal()
# └───────────────────────────────────────────────────────────────────────────┘

# Liste des utilisateurs de test et leurs nouveaux rôles à insérer ou mettre à jour
users_to_seed = [
    {"mail": "marie.bouafou@epfedu.fr", "role": "Admin"},
    {"mail": "maxime.morotti@epfedu.fr", "role": "Admin"},
    {"mail": "julien.blondiaux@epfedu.fr", "role": "RP-RM:MDE_P2027-MIN_P2027"},
    {"mail": "martin.demerdjiev@epfedu.fr", "role": "RP-RM:MDE_P2027"},
    {"mail": "charlotte.ribon@epfedu.fr", "role": "Etudiant"}
]

try:
    for u_data in users_to_seed:
        email = u_data["mail"].lower()
        role = u_data["role"]
        
        # Vérifie si l'utilisateur existe déjà
        user = db.query(UserAuth).filter(UserAuth.mail == email).first()
        if user:
            # Met à jour le rôle de l'utilisateur existant
            user.role = role
            print(f"Mise a jour : {email} -> role : {role}")
        else:
            # Crée un nouvel utilisateur
            new_user = UserAuth(mail=email, role=role)
            db.add(new_user)
            print(f"Creation : {email} -> role : {role}")
            
    db.commit()
    print("Database de test mise a jour avec succes !")
except Exception as e:
    print(f"Erreur : {e}")
    db.rollback()
finally:
    db.close()
# └───────────────────────────────────────────────────────────────────────────┘
