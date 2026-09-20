"""OceENS : l'application et ses outils, sous un seul paquet importable.

Tout le code applicatif vit sous ce paquet — `oceens.core`, `oceens.models`,
`oceens.routers`, `oceens.services` — et les fichiers qui l'accompagnent
(templates Jinja, fichiers statiques, CSV de seed) sont livrés avec lui. Un
import ne dépend donc plus du répertoire courant : l'application démarre depuis
n'importe où une fois le paquet installé.
"""
