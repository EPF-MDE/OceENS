# OcéEns II

Plateforme d'évaluation des enseignements conçue pour l'école d'ingénieurs EPF.

## Aperçu
L'application **OcéEns II** est actuellement structurée comme un **frontend autonome**. Elle permet aux utilisateurs (notamment à l'administration/scolarité) de préparer la création de sondages pour différentes filières de l'EPF.

Visuellement, l'application est habillée de la charte graphique de l'EPF.

## Architecture
Le projet utilise pour l'instant un serveur léger local **FastAPI / Uvicorn** chargé de la distribution des fichiers HTML, CSS, JS et PY. L'application est en préparation pour l'intégration future d'une vraie base de données et d'une API backend.

### Pages de l'application :
1. **Page d'accueil** (`/`) : Hub principal avec l'image de fond et la charte graphique OcéEns II (titre bicolore, boutons arrondis). Permet d'accéder au module de paramétrage. Cette page sera modifiée ultérieurement pour mieux faire correspondre les couleurs de l'EPF ainsi que les attentes client.
2. **Page de paramétrage** (`/parametrage`) : Interface de création de sondage. L'utilisateur peut y sélectionner l'année, le campus, la filière, puis configurer les Unités d'Enseignement (UE), ajouter des modules et y affecter des professeurs.

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
4. **Lancez l'application** :
   ```bash
   python app.py
   ``` 
5. Une fois le serveur lancé (vous verrez `* Running on http://127.0.0.1:5000`), ouvrez votre navigateur web et rendez-vous à l'adresse : **http://localhost:5000** ou faites directement CTRL + Clic sur le lien.


## Structure des Dossiers

```
test_web_app/
│
├── app.py                   # Point d'entrée Flask (démarrage du serveur et rendu des pages)
├── requirements.txt         # Fichier contenant les dépendances Python (uniquement Flask)
├── README.md                # Documentation du projet (ce fichier)
│
├── database/                # Dossier contenant la base de données (à ajouter manuellement)
│   └── db_oceens.db         # Fichier de la base de données (à ajouter manuellement)
│
├── static/                  # Dossier des fichiers statiques
│   ├── css/
│   │   └── parametrage.css  # Styles CSS de la page de paramétrage
│   ├── img/                 # Images et logos de l'application
│   │   ├── epf_logo.png     # Logo officiel de l'EPF
│   │   └── fond_accueil.png # Image de fond de la page d'accueil
│   └── js/
│       └── parametrage.js   # Script JS gérant l'interface de paramétrage (avec données simulées)
│
└── templates/               # Dossier des vues HTML servies par Flask
    ├── index.html           # Structure HTML de la page d'accueil
    └── parametrage.html     # Structure HTML de la page de création de sondage
```

## Évolutions futures
Dans sa version finale, ce projet est destiné à accueillir un backend complet en Python.
- Le fichier `app.py` sera enrichi avec des routes API (`/api/campus`, `/api/sondages`, etc.).
- Les données simulées en tête du fichier `static/js/parametrage.js` seront supprimées et remplacées par des appels AJAX (`fetch`) vers les nouvelles routes du backend.
- Les modèles de base de données (ex: SQLite ou PostgreSQL) seront réintégrés.
