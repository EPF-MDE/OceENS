"""Jeu de données lu au démarrage par `oceens.core.seed`.

Ce dossier s'appelait `import/` à la racine du dépôt : un nom que Python ne
peut pas importer, `import` étant un mot-clé du langage. Les CSV vivent
désormais à côté du code qui les lit, et `DATA_DIR` les localise par rapport à
ce fichier plutôt que par rapport au répertoire courant.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
