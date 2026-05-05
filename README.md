# OcéEns II

Plateforme d'évaluation des enseignements conçue pour l'école d'ingénieurs EPF.

## Aperçu
L'application **OcéEns II** est structurée autour d’un frontend et d’un backend intégrés.
Elle permet aux utilisateurs, notamment à l’administration et à la scolarité, de créer et gérer des sondages pour différentes filières de l’EPF.
Visuellement, l'application est habillée de la charte graphique de l'EPF.

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
  Créer un dossier database/ puis y coller le fichier db_oceens.db
5. **Lancez l'application** :
   ```bash
   fastapi dev
   ``` 
6. Une fois le serveur lancé (vous verrez `* Running on http://127.0.0.1:8000`), ouvrez votre navigateur web et rendez-vous à l'adresse : **http://localhost:8000** ou faites directement CTRL + Clic sur le lien.


## Structure des Dossiers

```
test_web_app/
│
├── app.py                   # Point d'entrée Flask (démarrage du serveur et rendu des pages)
├── models.py                # Modélisation de la base de données (tables, relations, structure des données avec SQLModel)
├── requirements.txt         # Fichier contenant les dépendances Python (uniquement Flask)
├── README.md                # Documentation du projet (ce fichier)
│
├── database/                # Dossier contenant la base de données (à ajouter manuellement)
│   └── db_oceens.db         # Fichier de la base de données (à ajouter manuellement)
│
├── static/                  # Dossier des fichiers statiques
│   ├── css/
│   │   └── parametrage.css  # Styles CSS de la page de paramétrage  
│   │   └── questionnaire.css # Styles CSS de la page de questionnaire              
│   ├── img/                 # Images et logos de l'application
│   │   ├── epf_logo.png     # Logo officiel de l'EPF
│   │   └── hautpage.png     # Image en haut de la page d’accueil
│   |   └── logo.png         # Logo officiel de l'EPF
│   └── js/
│       └── parametrage.js   # Script JS gérant l'interface de paramétrage (avec données simulées)
│       └── questionnaire.js # Script JS gérant l'interface de questionnaire (avec données simulées)
│
└── templates/               # Dossier des vues HTML servies par Flask
    ├── index.html           # Structure HTML de la page d'accueil
    └── parametrage.html     # Structure HTML de la page de création de sondage
    └── questionnaire.html   # Structure HTML de la page de questionnaire
    
```

## Évolutions futures
Dans sa version finale, ce projet est destiné à accueillir un backend complet en Python.
- Le fichier `app.py` sera enrichi avec des routes API (`/api/campus`, `/api/sondages`, etc.).
- Les données simulées en tête du fichier `static/js/parametrage.js` seront supprimées et remplacées par des appels AJAX (`fetch`) vers les nouvelles routes du backend.
- Les modèles de base de données (ex: SQLite ou PostgreSQL) seront réintégrés.

## Maquette des pages web

Les pages HTML devront respecter les maquettes établies au préalable et validées par les clients.
Maquette de la page web RP/RM : https://drive.google.com/file/d/1sGFz4WbXSTzSpdkj8Jjkrh9sa7GRI336/view?usp=drive_link
