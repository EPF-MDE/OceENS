import sys
import os

# Ajoute la racine du projet (le dossier OceENS/) au PYTHONPATH
# afin que les imports comme `from app import app` fonctionnent
# depuis n'importe quel sous-dossier (tests/, etc.)
sys.path.insert(0, os.path.dirname(__file__))
