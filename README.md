# OcéEns II

Plateforme d'évaluation des enseignements conçue pour l'école d'ingénieurs EPF.

## Aperçu
L'application **OcéEns II** est structurée autour d’un frontend et d’un backend intégrés.
Elle permet aux utilisateurs, notamment à l’administration et à la scolarité, de créer et gérer des sondages pour différentes filières de l’EPF.
Visuellement, l'application est habillée de la charte graphique de l'EPF.

## Environnements déployés

L'application est déployée sur deux environnements distincts, hébergés sur des VM dédiées avec la base de données SQLite directement intégrée sur chaque VM :

- **Préproduction** : [https://oceens-preprod.mde.epf.fr](https://oceens-preprod.mde.epf.fr/) — environnement de test utilisé pour valider les nouvelles fonctionnalités avant leur mise en production.
- **Production** : [https://oceens.mde.epf.fr](https://oceens.mde.epf.fr/) — environnement utilisé par les clients (administration et scolarité de l'EPF).

## Architecture
Le projet repose sur un serveur local basé sur FastAPI et Uvicorn, qui gère à la fois le rendu des pages HTML et les endpoints API.
Une base de données SQLite est utilisée via SQLModel pour stocker et manipuler les données.
L’architecture est conçue pour évoluer vers une base de données plus robuste et un déploiement en production.
### Pages de l'application :
1. **Page d'accueil** (`/`) : Hub principal avec l'image de fond et la charte graphique OcéEns II (titre bicolore, boutons arrondis). Permet d'accéder au module de paramétrage. Cette page sera modifiée ultérieurement pour mieux faire correspondre les couleurs de l'EPF ainsi que les attentes client.
2. **Page de paramétrage** (`/parametrage`) : Interface de création de sondage. L'utilisateur peut y sélectionner l'année, le campus, la filière, puis configurer les Unités d'Enseignement (UE), ajouter des modules et y affecter des professeurs.
3. **Page questionnaire** (`/questionnaire/{id_template}/{id_sondage}`) : Interface utilisateur permettant de répondre au sondage. Elle affiche dynamiquement les sections et les questions en fonction du template sélectionné.
Les questions peuvent être de différents types (choix unique, choix multiple, question ouverte) et s’adaptent au contexte (campus, formation, module, enseignant).
La page gère également des cas dynamiques, notamment pour les modules et enseignants (choix obligatoire, inclusif ou exclusif).
Un système de progression visuelle guide l’utilisateur, et les réponses sont envoyées au backend pour être enregistrées en base de données.

## Installation et Démarrage Local

⚠️ **Note importante** : depuis le déploiement de l'application sur les environnements de préproduction et de production, il n'est plus possible de tester l'application localement de la même manière qu'auparavant, pour deux raisons :
- La base de données `db_oceens.db` est désormais hébergée directement sur les VM de préproduction et de production, et n'est plus distribuée pour un usage local.
- L'authentification Azure Entra ID (`auth.py`) repose sur une URL de callback OAuth fixe, configurée pour les domaines `oceens-preprod.mde.epf.fr` et `oceens.mde.epf.fr`. La connexion ne fonctionne donc pas depuis un environnement local (`localhost`).

Pour toute modification ou test, il est recommandé de travailler directement sur la VM de préproduction (voir section [Environnements déployés](#environnements-déployés)).

Les étapes ci-dessous restent valables pour une installation locale à des fins de développement hors authentification (ex : travail sur le frontend, les templates, ou la logique ne dépendant pas de la connexion utilisateur) :

Ce projet nécessite Python (3.x) installé sur votre machine. Les dépendances sont minimalistes.

1. **Cloner ou télécharger le projet localement** dans le dossier de votre choix.
2. Ouvrez une invite de commande ou le terminal (ex: `cmd`, `powershell`, ou Anaconda Prompt).
- Créer un environnement virtuel : 
   ```bash
   py -m venv env
   ```

   ou 

   ```bash
   python3 -m venv env
   ```
- Activer l'environnement virtuel:
   ```bash
   env/scripts/activate
   ```
3. **Installez la dépendance principale (requirements.txt)** :
   ```bash
   pip install -r requirements.txt
   ```

4. **Ajouter la base de données**
  Créer un dossier database/ puis y coller un fichier db_oceens.db (à demander à l'équipe, ou créer une base vide localement pour les tests hors authentification)
5. **Lancez l'application** :
   ```bash
   fastapi dev
   ``` 
6. Une fois le serveur lancé (vous verrez `* Running on http://127.0.0.1:8000`), ouvrez votre navigateur web et rendez-vous à l'adresse : **http://localhost:8000** ou faites directement CTRL + Clic sur le lien.


## Structure des Dossiers

```
OCEENS/
│
├── app.py                   # Point d'entrée  (démarrage du serveur et rendu des pages)
├── models.py                # Modélisation de la base de données (tables, relations, structure des données avec SQLModel)
├── requirements.txt         # Fichier contenant les dépendances Python 
├── README.md                # Documentation du projet (ce fichier)
│
├── database/                # Dossier contenant la base de données (à ajouter manuellement)
│   └── db_oceens.db         # Fichier de la base de données (à ajouter manuellement)
│
├── static/                  # Dossier des fichiers statiques
│   ├── css/
│   │   └── admin.css  # Styles CSS de la page de admin 
│   │   └── etudiant.css # Styles CSS de la page de étudiante
|   |   └── parametrage.css # Styles CSS de la page de paramétrage
|   |   └── questionnaire.css # Styles CSS de la page de questionnaire
|   |               
│   ├── img/                 # Images et logos de l'application
│   │   ├── epf_logo.png     # Logo officiel de l'EPF
│   │   └── hautpage.png     # Image en haut de la page d’accueil
│   |   └── logo.png         # Logo officiel de l'EPF
│   └── js/
|       └── admin.js         # Script JS gérant l'interface admin 
|       └── etudiant.js      # Script JS gérant l'interface étudiant 
│       └── parametrage.js   # Script JS gérant l'interface paramétrage 
│       └── questionnaire.js # Script JS gérant l'interface questionnaire 
│
└── templates/               # Dossier des vues HTML servies par Flask
    ├── dashboard/
    │   └── admin.html  # Styles CSS de la page de admin 
    │   └── etudiant.html # Styles CSS de la page de étudiante
    |   └── parametrage.css # Styles CSS de la page de paramétrage
    |   └── questionnaire.css # Styles CSS de la page de questionnaire
    |
    ├── index.html           # Structure HTML de la page d'accueil
    └── parametrage.html     # Structure HTML de la page de création de sondage
    └── questionnaire.html   # Structure HTML de la page de questionnaire
    
```

## Évolutions futures
- Mise en place d'une page de **visualisation** des résultats de sondage, permettant à l'administration et aux RP-RM de consulter les statistiques et réponses agrégées par questionnaire.

## Maquette de visualisation

Maquette de la page de visualisation: 

<img width="800" height="600" alt="image" src="https://github.com/user-attachments/assets/c40fdae9-9c4a-4518-9a2a-fa3194ebeb98" />
