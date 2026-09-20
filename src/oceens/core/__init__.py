"""Accès bas niveau et sécurité : base de données, authentification, rôles.

Ce fichier est la surface publique du paquet : ce qu'un appelant extérieur
peut lire en un seul passage pour savoir ce que `core` offre au-delà de ses
modules d'entrée (`core.database`, `core.security`, `core.settings_store`...).

`check_survey_access_and_status` y est re-exporté parce que `routers` en a
besoin : une fois qu'un nom est atteint depuis l'extérieur du paquet, il est
de l'interface, et un nom d'interface ne porte pas de souligné de tête.
"""

from oceens.core.security import check_survey_access_and_status

__all__ = ["check_survey_access_and_status"]
