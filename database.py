"""=============================================================================
Gestion de la base de données SQLite et des rôles utilisateurs
=============================================================================

Ce module configure :
- SQLAlchemy : ORM (Object-Relational Mapping) pour Python
- SQLite : Base de données fichier léger
- Modèle UserRole : Table pour stocker email et rôle de chaque utilisateur

Rôles supportés : "etudiant", "professeur", "admin"
"""

from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

# ┌─ Configuration de la base de données ──────────────────────────────────────┐
# DATABASE_URL = "sqlite:///./roles.db" signifie :
#   - sqlite : utilise SQLite
#   - ./roles.db : crée un fichier roles.db dans le répertoire courant
#   - check_same_thread=False : autorise les appels depuis plusieurs threads
DATABASE_URL = "sqlite:///./roles.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour Uvicorn (multi-thread)
)
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Déclaration du modèle de base ───────────────────────────────────────────┐
# Base = classe parent pour tous les modèles SQLAlchemy
Base = declarative_base()


class UserRole(Base):
    """
    Modèle de table SQLAlchemy pour les utilisateurs et leurs rôles
    
    Colonnes :
    - email (STRING, PK) : Adresse email unique (clé primaire)
    - role (STRING) : Rôle de l'utilisateur (par défaut: "etudiant")
    
    Exemple :
        mail@example.com  →  professeur
        test@example.com  →  etudiant
        admin@example.com →  admin
    """
    __tablename__ = "roles"
    
    email = Column(String, primary_key=True)
        # Clé primaire : chaque email est unique et non-null
    role = Column(String, default="etudiant")
        # Rôle par défaut : "etudiant" si non spécifié


# Crée les tables dans la base de données (si elles n'existent pas)
Base.metadata.create_all(engine)
# └───────────────────────────────────────────────────────────────────────────┘

# ┌─ Session factory pour les requêtes à la BDD ──────────────────────────────┐
# SessionLocal est une "fabrique" qui crée des connections à la BDD
# Utilisation : db = SessionLocal() pour ouvrir une connexion
SessionLocal = sessionmaker(bind=engine)
# └───────────────────────────────────────────────────────────────────────────┘


def get_role(email: str) -> str:
    """
    Récupère le rôle d'un utilisateur à partir de son email
    
    Logique :
    1. Ouvre une connexion à la BDD
    2. Cherche l'utilisateur par email (case-insensitive)
    3. Retourne son rôle, ou "etudiant" par défaut
    
    Args :
        email : Adresse email de l'utilisateur
    
    Return :
        String : "admin", "professeur", "etudiant", ou "etudiant" (défaut)
    
    Exemple :
        role = get_role("julien@epfedu.fr")  # → "professeur"
        role = get_role("unknown@example.fr")  # → "etudiant" (par défaut)
    """
    # Ouvre une connexion à la base de données
    db = SessionLocal()
    
    try:
        # Requête : cherche l'utilisateur par email (case-insensitive)
        user = db.query(UserRole).filter(
            UserRole.email == email.lower()  # Normalise l'email en minuscules
        ).first()  # .first() retourne le premier résultat ou None
        
        # Retourne le rôle trouvé, ou "etudiant" par défaut
        return user.role if user else "etudiant"
    
    finally:
        # Ferme proprement la connexion (important pour libérer les ressources)
        db.close()
