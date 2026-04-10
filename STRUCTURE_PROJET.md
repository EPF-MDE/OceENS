# 📋 OceENS - Structure et Architecture du Projet

## 🏗️ Vue d'ensemble

OceENS est une application web d'authentification et de gestion des rôles utilisant :
- **Framework** : FastAPI (Python)
- **Authentification** : Microsoft Entra ID (Azure AD) via OAuth 2.0
- **Base de données** : SQLite
- **Templating** : Jinja2 (HTML)
- **Frontend** : HTML/CSS/JavaScript
- **Serveur** : Uvicorn

---

## 📁 Structure des fichiers

```
OceENS/
├── app.py              # Point d'entrée principal - Routes et configuration
├── auth.py             # Gestion authentification (login, logout, callback)
├── database.py         # Configuration SQLite + modèle UserRole
├── remplir_db.py       # Script pour initialiser les données de test
├── requirements.txt    # Dépendances Python (pip)
├── .env                # Variables d'environnement (⚠️ à ne pas commiter)
├── README.md           # Documentation générale
├── STRUCTURE_PROJET.md # Ce fichier
│
├── templates/          # Fichiers HTML (templates Jinja2)
│   ├── index.html           # Page de login / accueil
│   ├── parametrage.html     # Page de paramétrage
│   └── dashboard/
│       ├── admin.html       # Dashboard administrateur
│       ├── etudiant.html    # Dashboard étudiant
│       └── professeur.html  # Dashboard professeur
│
├── static/             # Fichiers statiques (CSS, JS, images)
│   ├── css/
│   │   └── parametrage.css  # Styles pour la page paramétrage
│   ├── js/
│   │   └── parametrage.js   # Scripts JavaScript
│   └── img/                 # Images et icônes
│
├── env/                # Environnement virtuel Python
│   ├── Scripts/        # Exécutables (Python, pip, etc)
│   └── Lib/            # Packages Python installés
│
└── roles.db            # Base de données SQLite (créée automatiquement)
```

---

## 🔄 Flux d'authentification

### 1️⃣ Phase 1 : Initiation (Route `/login`)

```
Utilisateur clique "Se connecter"
    ↓
FastAPI génère state aléatoire
    ↓
Stockage en session Starlette
    ↓
Redirection vers Microsoft Login
```

**Fichier** : `auth.py` → `login()`

**Sécurité** : State (UUID) = Protection CSRF

---

### 2️⃣ Phase 2 : Authentification Microsoft

```
Utilisateur se connecte chez Microsoft
    ↓
Microsoft valide les identifiants
    ↓
Microsoft redirige vers /auth/callback avec :
  - code (authentification)
  - state (vérification)
```

**Fournisseur** : Microsoft Entra ID

---

### 3️⃣ Phase 3 : Échange de code (Route `/auth/callback`)

```
Vérifier que state == session state (CSRF check)
    ↓
Envoyer code à Microsoft (avec SECRET_KEY)
    ↓
Microsoft retourne token d'accès
    ↓
Utiliser token pour récupérer infos utilisateur (Microsoft Graph)
    ↓
Querier BDD pour obtenir le rôle
    ↓
Créer session avec {name, email, role}
    ↓
Rediriger vers /dashboard/{role}
```

**Fichier** : `auth.py` → `auth_callback()`

---

### 4️⃣ Phase 4 : Accès au dashboard

```
Request vers /dashboard/{role}
    ↓
get_current_user() récupère l'utilisateur de la session
    ↓
Vérifications :
  ✓ Utilisateur connecté ?
  ✓ Rôle valide ?
  ✓ L'utilisateur a-t-il le droit d'accéder à ce rôle ?
    ↓
Afficher le template correspondant
  admin → templates/dashboard/admin.html
  etudiant → templates/dashboard/etudiant.html
  professeur → templates/dashboard/professeur.html
```

**Fichier** : `app.py` → `dashboard()`

---

### 5️⃣ Phase 5 : Déconnexion (Route `/logout`)

```
Utilisateur clique "Se déconnecter"
    ↓
Effacer la session Starlette
    ↓
Effacer les cookies de session
    ↓
Rediriger vers /logout Microsoft
    ↓
Déconnecter de tous les services Microsoft
    ↓
Retour à la page d'accueil
```

**Fichier** : `auth.py` → `logout()`

---

## 💾 Base de données

### Modèle `UserRole`

**Table** : `roles`

| Colonne | Type   | Clé | Défaut      |
|---------|--------|-----|-------------|
| email   | String | PK  | (required)  |
| role    | String | -   | "etudiant"  |

**Rôles disponibles** :
- `"etudiant"` : Accès au dashboard étudiant
- `"professeur"` : Accès au dashboard professeur
- `"admin"` : Accès au dashboard administrateur

### Fonction `get_role(email: str) -> str`

```python
# Récupère le rôle d'un utilisateur
role = get_role("julien.blondiaux@epfedu.fr")  # → "professeur"

# Défaut si email non trouvé
role = get_role("unknown@example.fr")  # → "etudiant"
```

**Utilisation** : Dans `auth_callback()` pour assigner le rôle à chaque authentification

---

## 🔐 Variables d'environnement (`.env`)

Créez un fichier `.env` à la racine du projet :

```env
# Azure Entra ID Configuration
ENTRA_CLIENT_ID=your_app_id_here
ENTRA_CLIENT_SECRET=your_secret_here
ENTRA_TENANT_ID=your_tenant_id_here
REDIRECT_URI=https://localhost/auth/callback

# Session Security
SECRET_KEY=your_secure_random_key_here
```

⚠️ **IMPORTANT** : Ne jamais commiter `.env` !

---

## 🚀 Démarrage du serveur

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Lancer l'application

```bash
python app.py
```

Ou avec Uvicorn directement :

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Accès

- **URL** : http://localhost:8000
- **Dashboard Admin** : http://localhost:8000/dashboard/admin
- **Dashboard Étudiant** : http://localhost:8000/dashboard/etudiant
- **Dashboard Professeur** : http://localhost:8000/dashboard/professeur

---

## 📝 Initialisation des données

Éditer `remplir_db.py` avec les emails réels, puis exécuter :

```bash
python remplir_db.py
```

**Exemple** :

```python
prof = UserRole(email="prof@epfedu.fr", role="professeur")
admin = UserRole(email="admin@epfedu.fr", role="admin")

db.add(prof)
db.add(admin)
db.commit()
```

---

## 🔧 Points clés d'architecture

### SessionMiddleware (app.py)

- Gère les **sessions utilisateur** de manière sécurisée
- Stocke l'utilisateur dans des **cookies signés**
- `https_only=True` : Force HTTPS en production
- `same_site="lax"` : Protection CSRF

### MSAL (auth.py)

- **Bibliothèque Microsoft** pour OAuth 2.0
- Gère automatiquement les tokens
- État valide 10 minutes seulement
- Renouvellement automatique si nécessaire

### SQLAlchemy (database.py)

- **ORM** pour interaction avec SQLite
- `declarative_base()` : Classes Python → Tables SQL
- `sessionmaker` : Factory pour créer des connexions BDD
- `finally: db.close()` : Fermeture propre

### Jinja2 (templates)

- **Templating HTML** avec variables Python
- Accès aux variables : `{{ variable_name }}`
- Boucles : `{% for item in items %}`
- Conditions : `{% if user %}`

---

## 🛡️ Sécurité

| Aspect | Implémentation |
|--------|----------------|
| **CSRF** | State aléatoire (UUID) validé côté serveur |
| **Session** | Cookies signés + middleware Starlette |
| **HTTPS** | Force HTTPS en production |
| **Secrets** | Variables d'environnement (jamais en dur) |
| **Access Control** | Vérification du rôle pour chaque dashboard |
| **Accès BDD** | Injection SQL impossible (ORM SQLAlchemy) |

---

## 🐛 Troubleshooting

### "State invalide"
- Le cookie de session n'est pas persistent
- **Solution** : Utiliser un certificat SSL valide en production

### "Erreur token"
- `CLIENT_SECRET` ou `CLIENT_ID` incorrect dans `.env`
- **Solution** : Vérifier les credentials sur Azure Entra ID

### "Utilisateur connecté mais dashboard vide"
- `get_current_user()` retourne None
- **Solution** : Vérifier que la session Starlette est active

### "Email non trouvé dans BDD"
- Utilisateur obtient rôle "etudiant" par défaut
- **Solution** : Ajouter l'email dans `remplir_db.py`

---

## 📚 Ressources

- **FastAPI** : https://fastapi.tiangolo.com/
- **MSAL Python** : https://github.com/AzureAD/microsoft-authentication-library-for-python
- **Microsoft Graph** : https://learn.microsoft.com/en-us/graph/
- **Jinja2** : https://jinja.palletsprojects.com/
- **SQLAlchemy** : https://www.sqlalchemy.org/

---

## ✅ Checklist de déploiement

- [ ] `.env` créé avec vraies credentials Azure
- [ ] Certificat SSL valide (Let's Encrypt)
- [ ] `https_only=True` dans SessionMiddleware
- [ ] Base de données initialisée (`python remplir_db.py`)
- [ ] Tous les utilisateurs ajoutés à `roles.db`
- [ ] Port 8000 ouvert sur le serveur
- [ ] Variables d'environnement sécurisées
- [ ] Tests d'authentification complète

---

**Auteur** : Équipe OceENS  
**Dernière mise à jour** : 2026-04-10
