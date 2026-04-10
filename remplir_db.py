"""
fichier permettant de remplir la base de données avec des données d'exemple
il n'est pas nécessaire de l'exécuter à chaque fois, mais il peut être utile pour tester l'application avec des données réalistes.
utiliser les roles suivants : etudiant, professeur, admin
"""

from database import SessionLocal, UserRole

# On ouvre une connexion à la base
db = SessionLocal()

# --- Création d'instances (lignes) ---

# Exemple 2 : Un professeur
prof_1 = UserRole(email="julien.blondiaux@epfedu.fr", role="professeur")

# Exemple 3 : Un administrateur
admin_1 = UserRole(email="marie.bouafou@epfedu.fr", role="admin")

# --- Ajout à la session et Sauvegarde ---

# On ajoute les objets à la "session" (le panier avant de payer)
db.add(prof_1)
db.add(admin_1)

# On valide (commit) pour écrire réellement dans le fichier SQLite
try:
    db.commit()
    print(" Données insérées avec succès !")
except Exception as e:
    print(f" Erreur : {e}")
    db.rollback()  # Annule tout si ça rate
finally:
    db.close()  # Ferme proprement la connexion
