"""Schéma SQLModel, un fichier par table.

Sans ce fichier, `models/` serait un paquet-espace de noms implicite : une
instruction comme `from models import User` résoudrait alors vers le
*module* `models/User.py` plutôt que vers la classe `User` qu'il contient,
et tout appel `User(mail=...)` échouerait avec « 'module' object is not
callable ». Les imports groupés utilisés dans tout le dépôt
(`from models import Answer, Module, ...`) dépendent donc de ce ré-export
explicite : toute nouvelle classe ajoutée dans `models/` doit être déclarée
ici, sans quoi elle reste invisible depuis l'extérieur du paquet.

Aucun fichier de `models/` n'importe un autre fichier de `models/` : les
clés étrangères SQLAlchemy sont déclarées par nom de table (chaîne), pas par
référence de classe, donc il n'y a pas de risque d'import circulaire ici.
"""

from oceens.models.Answer import Answer
from oceens.models.LLMModelPrice import LLMModelPrice
from oceens.models.LLMProvider import LLMProvider
from oceens.models.Module import Module
from oceens.models.Option import Option
from oceens.models.Program import Program
from oceens.models.Prompt import Prompt
from oceens.models.Question import Question
from oceens.models.Respondent import Respondent
from oceens.models.Role import Role
from oceens.models.Section import Section
from oceens.models.Setting import Setting
from oceens.models.Stat import Stat
from oceens.models.StatValue import StatValue
from oceens.models.Submission import Submission
from oceens.models.Summary import Summary
from oceens.models.Survey import Survey
from oceens.models.Template import Template
from oceens.models.User import User

__all__ = [
    "Answer",
    "LLMModelPrice",
    "LLMProvider",
    "Module",
    "Option",
    "Program",
    "Prompt",
    "Question",
    "Respondent",
    "Role",
    "Section",
    "Setting",
    "Stat",
    "StatValue",
    "Submission",
    "Summary",
    "Survey",
    "Template",
    "User",
]
