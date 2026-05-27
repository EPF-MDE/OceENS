"""=============================================================================
Gestion de la base de données SQLite et des rôles utilisateurs
=============================================================================

Ce module configure :
- SQLAlchemy : ORM (Object-Relational Mapping) pour Python
- SQLite : Base de données fichier léger (database/db_oceens.db)
- Fonction get_or_create_user : Récupère ou crée un utilisateur dans la table Users

Rôles supportés : "Etudiant" (défaut), "Admin", "RP-RM:..." (responsable pédagogique)
"""

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# ┌─ Configuration de la base de données ──────────────────────────────────────┐
# On utilise désormais la base de données principale du projet
# au lieu d'une base séparée (roles.db)
DATABASE_URL = "sqlite:///./database/db_oceens.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour Uvicorn (multi-thread)
)
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Déclaration du modèle de base ───────────────────────────────────────────┐
Base = declarative_base()


class UserAuth(Base):
    """
    Modèle SQLAlchemy miroir de la table Users existante dans db_oceens.db

    Colonnes :
    - Id_User (INTEGER, PK, auto-increment) : Identifiant unique
    - Mail (STRING) : Adresse email de l'utilisateur
    - Role (STRING) : Rôle de l'utilisateur (défaut: "Etudiant")

    Exemple :
        julien@epfedu.fr   →  Etudiant
        admin@epfedu.fr    →  Admin
        prof@epfedu.fr     →  RP-RM:MDE_P2027-MIN_P2027
    """
    __tablename__ = "Users"

    id_user = Column("Id_User", Integer, primary_key=True, autoincrement=True)
    mail = Column("Mail", String)
    role = Column("Role", String, default="Etudiant")
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Session factory pour les requêtes à la BDD ──────────────────────────────┐
SessionLocal = sessionmaker(bind=engine)
# └───────────────────────────────────────────────────────────────────────────┘


def get_or_create_user(email: str) -> str:
    """
    Récupère le rôle d'un utilisateur, ou le crée automatiquement.

    Logique :
    1. Ouvre une connexion à la BDD (database/db_oceens.db)
    2. Cherche l'utilisateur par email (case-insensitive) dans la table Users
    3. Si trouvé → retourne son rôle
    4. Si non trouvé → insère un nouvel utilisateur avec le rôle "Etudiant"
    5. Retourne le rôle

    Args :
        email : Adresse email de l'utilisateur (provenant de Microsoft Graph)

    Return :
        String : "Admin", "Etudiant", "RP-RM:...", ou "Etudiant" (si créé)

    Exemple :
        role = get_or_create_user("julien@epfedu.fr")  # → "Etudiant" (créé)
        role = get_or_create_user("admin@epfedu.fr")    # → "Admin" (existant)
    """
    db = SessionLocal()

    try:
        # Requête : cherche l'utilisateur par email (case-insensitive)
        user = db.query(UserAuth).filter(
            UserAuth.mail == email.lower()
        ).first()

        if user:
            # Utilisateur trouvé → retourne son rôle
            return user.role if user.role else "Etudiant"

        # Utilisateur non trouvé → auto-inscription avec rôle par défaut
        new_user = UserAuth(
            mail=email.lower(),
            role="Etudiant"
        )
        db.add(new_user)
        db.commit()

        return "Etudiant"

    finally:
        # Ferme proprement la connexion
        db.close()
