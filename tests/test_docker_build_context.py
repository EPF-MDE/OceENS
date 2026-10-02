"""Les fichiers que lit le seed font partie du contexte de build Docker.

Une image lancée sans volume (Azure App Service, `docker run` seul) ne voit que
ce que `.dockerignore` laisse passer : un fichier du seed exclu y manque à
chaque démarrage, et le sondage seedé n'a rien à synthétiser.
"""

from fnmatch import fnmatch
from pathlib import Path

import pytest

from oceens.core.seed import SEEDED_SURVEYS
from oceens.seed_data import DATA_DIR

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SEED_FILES = [DATA_DIR / "Program_list.csv"] + [
    DATA_DIR / survey["answers_file"] for survey in SEEDED_SURVEYS
]


def dockerignore_patterns():
    """Les règles de `.dockerignore`, sans commentaires ni lignes vides."""
    lines = (PROJECT_ROOT / ".dockerignore").read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def is_excluded(path, patterns):
    """Le chemin, relatif à la racine, est-il écarté du contexte de build ?

    Comme Docker : la dernière règle qui correspond l'emporte, `!` réintègre,
    et écarter un dossier écarte tout ce qu'il contient. `fnmatch` laisse `*`
    traverser les `/`, ce que Docker ne fait pas : le test écarte donc plutôt
    trop que pas assez.
    """
    parts = path.split("/")
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    excluded = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        pattern = pattern.removeprefix("!").strip("/")
        if any(fnmatch(candidate, pattern) for candidate in candidates):
            excluded = not negated
    return excluded


@pytest.mark.parametrize("seed_file", SEED_FILES, ids=lambda path: path.name)
def test_seed_file_is_in_build_context(seed_file):
    assert seed_file.exists()
    relative_path = seed_file.relative_to(PROJECT_ROOT).as_posix()
    assert not is_excluded(relative_path, dockerignore_patterns())
