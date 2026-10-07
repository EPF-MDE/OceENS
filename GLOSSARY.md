# OcéEns

Plateforme d'évaluation des enseignements de l'EPF : des sondages sont créés par filière, les étudiants y répondent, et les réponses sont exportées, visualisées et synthétisées.

## Langage

### Authentification

**Connexion de développement** (`AUTH_MODE=dev`) :
Connexion sans fournisseur d'identité : on choisit l'adresse mail d'un utilisateur et on est connecté en tant que lui, sans preuve d'identité. Elle n'existe que lorsque `AUTH_MODE=dev` et ne doit jamais servir en production.
_À éviter_ : impersonation, usurpation, fake login
