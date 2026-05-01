from typing import Annotated, Dict, Optional, List

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
import uvicorn

from models import Module, Question, Sondage, Template, Option, User
from pydantic import BaseModel

sqlite_file_name = "database/db_oceens.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False, "timeout": 15}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


class SondageCreate(BaseModel):
    id_template: int
    campus: str
    formation: str
    semestre: str
    annee_scolaire: str
    id_user: Optional[int] = 1


class ProfesseurBase(BaseModel):
    id: int
    prenom: str
    nom: str


class ModuleCreate(BaseModel):
    id: int
    nom: str
    modalite: str
    professeurs: List[ProfesseurBase]


class UECreate(BaseModel):
    id: int
    nom: str
    optionnel: bool
    modules: List[ModuleCreate]


class SondageFullCreate(BaseModel):
    id_template: int
    campus: str
    formation: str
    semestre: str
    annee_scolaire: str
    ues: List[UECreate]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initialisation de la base de données...")
    create_db_and_tables()
    yield
    print("Fermeture de la connexion...")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def parse_name(full_name: Optional[str], fallback_id: int) -> Dict[str, Optional[str]]:
    if not full_name:
        return {"id": fallback_id, "prenom": None, "nom": None}
    parts = full_name.strip().split()
    if len(parts) == 1:
        return {"id": fallback_id, "prenom": parts[0], "nom": ""}
    return {"id": fallback_id, "prenom": parts[0], "nom": " ".join(parts[1:])}


def build_parametrage_data(session: Session) -> Dict[str, object]:
    templates = session.exec(select(Template)).all()
    sondages = session.exec(select(Sondage)).all()
    modules = session.exec(select(Module)).all()
    users = session.exec(select(User)).all()

    campus_names = []
    filiere_names = []
    semestres = []
    annees_scolaires = []
    formation_to_campus: Dict[str, str] = {}
    for sondage in sondages:
        if sondage.campus and sondage.campus not in campus_names:
            campus_names.append(sondage.campus)
        if sondage.formation and sondage.formation not in filiere_names:
            filiere_names.append(sondage.formation)
            formation_to_campus[sondage.formation] = sondage.campus or ""
        if sondage.semestre and sondage.semestre not in semestres:
            semestres.append(sondage.semestre)
        if sondage.annee_scolaire and sondage.annee_scolaire not in annees_scolaires:
            annees_scolaires.append(sondage.annee_scolaire)

    # Ensure default campuses are always available
    default_campuses = ["Paris-Cachan", "Montpellier", "Troyes", "St-Nazaire"]
    for dc in default_campuses:
        if dc not in campus_names:
            campus_names.append(dc)

    campus_list = [
        {"id": index + 1, "nom": campus} for index, campus in enumerate(campus_names)
    ]
    campus_index = {campus["nom"]: campus["id"] for campus in campus_list}
    filieres = []
    for index, formation in enumerate(filiere_names):
        filieres.append(
            {
                "id": index + 1,
                "nom": formation,
                "campus_id": campus_index.get(
                    formation_to_campus.get(formation, ""), None
                ),
            }
        )

    professors = []
    professor_index = 1
    seen_professors = set()
    for module in modules:
        if not module.enseignant:
            continue
        professor = parse_name(module.enseignant, professor_index)
        if not professor["prenom"] and not professor["nom"]:
            continue
        key = (professor["prenom"].lower(), professor["nom"].lower())
        if key not in seen_professors:
            professor["id"] = professor_index
            seen_professors.add(key)
            professors.append(professor)
            professor_index += 1

    for user in users:
        if user.role and "Enseignant" in user.role and user.mail:
            parsed = parse_name(
                user.mail.split("@")[0].replace(".", " "), professor_index
            )
            parsed["nom"] = parsed["nom"] or ""
            parsed["prenom"] = parsed["prenom"] or ""
            key = (parsed["prenom"].lower(), parsed["nom"].lower())
            if key and key not in seen_professors:
                parsed["id"] = professor_index
                seen_professors.add(key)
                professors.append(parsed)
                professor_index += 1

    ues_by_filiere = {}
    if modules and filieres:
        default_filiere_id = filieres[0]["id"]
        for module in modules:
            filiere_id = default_filiere_id
            ue_name = module.ue or "Sans UE"
            ues_by_filiere.setdefault(filiere_id, [])
            ue_entry = next(
                (ue for ue in ues_by_filiere[filiere_id] if ue["nom"] == ue_name), None
            )
            professor = parse_name(module.enseignant, professor_index)
            if professor["prenom"] or professor["nom"]:
                key = (professor["prenom"].lower(), professor["nom"].lower())
                if key not in seen_professors:
                    professor["id"] = professor_index
                    seen_professors.add(key)
                    professors.append(professor)
                    professor_index += 1
            if ue_entry is None:
                ue_entry = {
                    "id": len(ues_by_filiere[filiere_id]) + 1,
                    "nom": ue_name,
                    "optionnel": module.ue_optionnelle or False,
                    "_open": True,
                    "modules": [],
                }
                ues_by_filiere[filiere_id].append(ue_entry)
            # Parser les professeurs en splittant sur ","
            prof_list = []
            if module.enseignant:
                prof_strings = [
                    p.strip() for p in module.enseignant.split(",") if p.strip()
                ]
                for prof_str in prof_strings:
                    professor = parse_name(prof_str, professor_index)
                    if professor["prenom"] or professor["nom"]:
                        key = (professor["prenom"].lower(), professor["nom"].lower())
                        if key not in seen_professors:
                            professor["id"] = professor_index
                            seen_professors.add(key)
                            professors.append(professor)
                            professor_index += 1
                        prof_list.append(
                            {
                                "id": professor.get("id", 0),
                                "prenom": professor["prenom"],
                                "nom": professor["nom"],
                            }
                        )
            ue_entry["modules"].append(
                {
                    "id": int(module.id_module or 0),
                    "nom": module.nom or "Module",
                    "modalite": "OBLIGATOIRE",
                    "professeurs": prof_list,
                }
            )

    template_dicts = [template.dict() for template in templates]

    return {
        "templates": template_dicts,
        "campusList": campus_list,
        "filieres": filieres,
        "semestres": semestres,
        "anneesScolaires": annees_scolaires,
        "profsList": professors,
        "uesByFiliere": ues_by_filiere,
        "selectedTemplateId": template_dicts[0]["id_template"]
        if template_dicts
        else None,
        "selectedCampusId": campus_list[0]["id"] if campus_list else None,
        "selectedFiliereId": filieres[0]["id"] if filieres else None,
        "semestreAnnee": semestres[0] if semestres else "",
        "selectedAnneeScolaire": annees_scolaires[0] if annees_scolaires else "",
        "questions": [
            question.dict() for question in session.exec(select(Question)).all()
        ],
        "options": [option.dict() for option in session.exec(select(Option)).all()],
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
            "page_title": "OCEENS II - Plateforme d'évaluation",
            "page_subtitle": "Plateformes d'évaluation des enseignements",
            "create_label": "Créer questionnaire",
            "dashboard_label": "Visionner dashboard",
            "create_url": "/parametrage",
            "background_image": "/static/img/fond_accueil.png",
            "button_primary_class": "hero-btn hero-btn-purple",
            "button_secondary_class": "hero-btn hero-btn-red",
        },
    )


@app.get("/parametrage", response_class=HTMLResponse)
def parametrage(request: Request, session: SessionDep):
    data = build_parametrage_data(session)
    return templates.TemplateResponse(
        name="parametrage.html",
        context={
            "request": request,
            "templates": data["templates"],
            "campus_list": data["campusList"],
            "filieres": data["filieres"],
            "semestres": data["semestres"],
            "annees_scolaires": data["anneesScolaires"],
            "profs": data["profsList"],
            "ues_by_filiere": data["uesByFiliere"],
            "selected_template_id": data["selectedTemplateId"],
            "selected_campus_id": data["selectedCampusId"],
            "selected_filiere_id": data["selectedFiliereId"],
            "semestre_annee": data["semestreAnnee"],
            "selected_annee_scolaire": data["selectedAnneeScolaire"],
        },
    )


@app.get("/api/parametrage")
def parametrage_api(session: SessionDep):
    return JSONResponse(content=build_parametrage_data(session))


@app.post("/api/sondage")
def create_sondage(sondage: SondageFullCreate, session: SessionDep):
    # Utiliser une transaction pour éviter les locks
    with session.begin():
        with session.no_autoflush:
            # Trouver le prochain id_sondage pour ce template
            existing_sondages = session.exec(
                select(Sondage).where(Sondage.id_template == sondage.id_template)
            ).all()
            next_id_sondage = max([s.id_sondage for s in existing_sondages] + [0]) + 1
    
            new_sondage = Sondage(
                id_template=sondage.id_template,
                id_sondage=next_id_sondage,
                campus=sondage.campus,
                formation=sondage.formation,
                semestre=sondage.semestre,
                annee_scolaire=sondage.annee_scolaire,
                statut=1,  # Actif par défaut
                id_user=1,  # Utilisateur par défaut
            )
    
            session.add(new_sondage)
    
            # Traiter les UEs et modules
            for ue in sondage.ues:
                for module_data in ue.modules:
                    # Vérifier si le module existe déjà
                    module = session.exec(
                        select(Module).where(Module.id_module == module_data.id)
                    ).first()
                    if module:
                        # Mettre à jour le module existant
                        module.id_sondage = next_id_sondage
                        module.ue = ue.nom
                        module.ue_optionnelle = ue.optionnel
                        # Mettre à jour les professeurs
                        prof_names = [
                            f"{p.prenom} {p.nom}" for p in module_data.professeurs
                        ]
                        module.enseignant = ", ".join(prof_names) if prof_names else None
                    else:
                        # Créer un nouveau module
                        new_module = Module(
                            id_module=module_data.id,
                            nom=module_data.nom,
                            enseignant=", ".join(
                                [f"{p.prenom} {p.nom}" for p in module_data.professeurs]
                            ),
                            ue=ue.nom,
                            ue_optionnelle=ue.optionnel,
                            id_template=sondage.id_template,
                            id_sondage=next_id_sondage,
                        )
                        session.add(new_module)

    return {"message": "Sondage créé avec succès", "id_sondage": next_id_sondage}


if __name__ == "__main__":
    uvicorn.run("app:app", port=8000, reload=True)
