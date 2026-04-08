from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./roles.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()


class UserRole(Base):
    __tablename__ = "roles"
    email = Column(String, primary_key=True)
    role = Column(String, default="etudiant")


Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def get_role(email: str) -> str:
    db = SessionLocal()
    user = db.query(UserRole).filter(UserRole.email == email.lower()).first()
    db.close()
    return (
        user.role if user else "etudiant"
    )  # une personne n'appartenant pas à la bdd sera considéré come un élève
