"""Génération d'une synthèse : un appel au modèle, borné par le délai d'un job.

Le daemon passe le fournisseur, le modèle, le prompt et sa session HTTP ; il
récupère un `SummaryOutcome` qu'il écrit tel quel dans la ligne `summaries`.
Il ne connaît ni le délai, ni les exceptions de l'appel, ni le statut que
reçoit chaque échec.
"""

from oceens.summary_generation._generation import (
    JOB_DEADLINE_SECONDS,
    SummaryOutcome,
    generate_summary,
)

__all__ = ["JOB_DEADLINE_SECONDS", "SummaryOutcome", "generate_summary"]
