from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "Users"

    id_user: Optional[int] = Field(
        default=None, sa_column=Column("Id_User", Integer, primary_key=True)
    )
    mail: Optional[str] = Field(default=None, sa_column=Column("Mail", String))
    role: Optional[str] = Field(default=None, sa_column=Column("Role", String))


class Repondant(SQLModel, table=True):
    __tablename__ = "Répondants"

    id_repondant: Optional[int] = Field(
        default=None, sa_column=Column("Id_Répondant", Integer, primary_key=True)
    )
    date_soumission: Optional[str] = Field(
        default=None, sa_column=Column("Date_soumission", String)
    )


class Template(SQLModel, table=True):
    __tablename__ = "Templates"

    id_template: Optional[int] = Field(
        default=None, sa_column=Column("Id_Template", Integer, primary_key=True)
    )
    nom: Optional[str] = Field(default=None, sa_column=Column("Nom", String))
    id_user: Optional[int] = Field(
        default=None, sa_column=Column("Id_User", Integer, ForeignKey("Users.Id_User"))
    )


class Sondage(SQLModel, table=True):
    __tablename__ = "Sondages"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template",
            Integer,
            ForeignKey("Templates.Id_Template"),
            primary_key=True,
        ),
    )
    id_sondage: Optional[int] = Field(
        default=None, sa_column=Column("Id_Sondage", Integer, primary_key=True)
    )
    campus: Optional[str] = Field(default=None, sa_column=Column("Campus", String))
    formation: Optional[str] = Field(
        default=None, sa_column=Column("Formation", String)
    )
    semestre: Optional[str] = Field(default=None, sa_column=Column("Semestre", String))
    url: Optional[str] = Field(default=None, sa_column=Column("URL", String))
    statut: Optional[int] = Field(default=None, sa_column=Column("Statut", Integer))
    annee_scolaire: Optional[str] = Field(
        default=None, sa_column=Column("Annee_scolaire", String)
    )
    mot_de_passe: Optional[str] = Field(
        default=None, sa_column=Column("Mot_de_passe", String)
    )
    id_user: Optional[int] = Field(
        default=None, sa_column=Column("Id_User", Integer, ForeignKey("Users.Id_User"))
    )


class Section(SQLModel, table=True):
    __tablename__ = "Sections"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template",
            Integer,
            ForeignKey("Templates.Id_Template"),
            primary_key=True,
        ),
    )
    id_section: Optional[int] = Field(
        default=None, sa_column=Column("Id_Section", Integer, primary_key=True)
    )
    nom: Optional[str] = Field(default=None, sa_column=Column("Nom", String))
    ordre: Optional[int] = Field(default=None, sa_column=Column("Ordre", Integer))
    section_type: Optional[str] = Field(default=None, sa_column=Column("Type", String))


class Question(SQLModel, table=True):
    __tablename__ = "Questions"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template",
            Integer,
            ForeignKey("Templates.Id_Template"),
            primary_key=True,
        ),
    )
    id_section: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Section", Integer, ForeignKey("Sections.Id_Section"), primary_key=True
        ),
    )
    id_question: Optional[int] = Field(
        default=None, sa_column=Column("Id_Question", Integer, primary_key=True)
    )
    categorie: Optional[str] = Field(
        default=None, sa_column=Column("Catégorie", String)
    )
    question_type: Optional[str] = Field(default=None, sa_column=Column("Type", String))
    langue: Optional[str] = Field(default=None, sa_column=Column("Langue", String))
    intitule: Optional[str] = Field(default=None, sa_column=Column("Intitulé", Text))


class Option(SQLModel, table=True):
    __tablename__ = "Options"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template",
            Integer,
            ForeignKey("Templates.Id_Template"),
            primary_key=True,
        ),
    )
    id_section: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Section", Integer, ForeignKey("Sections.Id_Section"), primary_key=True
        ),
    )
    id_question: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Question",
            Integer,
            ForeignKey("Questions.Id_Question"),
            primary_key=True,
        ),
    )
    id_option: Optional[int] = Field(
        default=None, sa_column=Column("Id_Option", Integer, primary_key=True)
    )
    intitule: Optional[str] = Field(default=None, sa_column=Column("Intitulé", Text))


class Module(SQLModel, table=True):
    __tablename__ = "Modules"

    id_module: Optional[int] = Field(
        default=None, sa_column=Column("Id_Module", Integer, primary_key=True)
    )
    nom: Optional[str] = Field(default=None, sa_column=Column("Nom", String))
    enseignant: Optional[str] = Field(
        default=None, sa_column=Column("Enseignant", String)
    )
    ue: Optional[str] = Field(default=None, sa_column=Column("UE", String))
    ue_optionnelle: Optional[bool] = Field(
        default=False, sa_column=Column("Ue_Optionnelle", Integer)
    )
    choix_enseignant: Optional[bool] = Field(
        default=False, sa_column=Column("Choix_enseignants", Integer)
    )
    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column("Id_Template", Integer, ForeignKey("Templates.Id_Template")),
    )
    id_sondage: Optional[int] = Field(
        default=None,
        sa_column=Column("Id_Sondage", Integer, ForeignKey("Sondages.Id_Sondage")),
    )


class Reponse(SQLModel, table=True):
    __tablename__ = "Reponses"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template", Integer, ForeignKey("Sondages.Id_Template"), primary_key=True
        ),
    )
    id_sondage: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Sondage", Integer, ForeignKey("Sondages.Id_Sondage"), primary_key=True
        ),
    )
    id_repondant: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Répondant",
            Integer,
            ForeignKey("Répondants.Id_Répondant"),
            primary_key=True,
        ),
    )
    id_template_1: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template_1",
            Integer,
            ForeignKey("Questions.Id_Template"),
            primary_key=True,
        ),
    )
    id_section: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Section", Integer, ForeignKey("Questions.Id_Section"), primary_key=True
        ),
    )
    id_question: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Question",
            Integer,
            ForeignKey("Questions.Id_Question"),
            primary_key=True,
        ),
    )
    id_reponse: Optional[int] = Field(
        default=None, sa_column=Column("Id_Reponse", Integer, primary_key=True)
    )
    valeur: Optional[str] = Field(default=None, sa_column=Column("Valeur", Text))


class Repondre(SQLModel, table=True):
    __tablename__ = "Repondre"

    id_template: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Template", Integer, ForeignKey("Sondages.Id_Template"), primary_key=True
        ),
    )
    id_sondage: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_Sondage", Integer, ForeignKey("Sondages.Id_Sondage"), primary_key=True
        ),
    )
    id_user: Optional[int] = Field(
        default=None,
        sa_column=Column(
            "Id_User", Integer, ForeignKey("Users.Id_User"), primary_key=True
        ),
    )
