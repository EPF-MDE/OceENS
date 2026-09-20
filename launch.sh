#!/bin/bash

cd /home/mde-admin/OceENS

# uv crée .venv et y installe le projet et ses dépendances, aux versions du
# lock. Idempotent : sans changement, la commande ne fait rien.
uv sync --frozen

# Les deux processus sont lancés par leurs points d'entrée installés
# (`oceens`, `oceens-summaries`), et reconnus dans la table des processus par
# le chemin de ces mêmes points d'entrée.
if pgrep -f "bin/oceens$" > /dev/null; then
	echo "Website already launched"
else
	echo "Launching Website with screen"
	screen -d -m bash -c "PYTHONUNBUFFERED=1 uv run oceens 2> >(tee -a app.error) | tee -a app.log"
fi

if pgrep -f "bin/oceens-summaries$" > /dev/null; then
	echo "Summaries generator already launched"
else
	echo "Launching Summaries generator with screen"
	screen -d -m bash -c "PYTHONUNBUFFERED=1 uv run oceens-summaries 2> >(tee -a summaries.error) | tee -a summaries.log"
fi
