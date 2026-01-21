# QRVerse Pro (2qrgen)

Plateforme de génération et gestion de QR Codes avec FastAPI.

## Fonctionnalités

- **Types de QR Codes** : URL, Texte, Email, Téléphone, WiFi, vCard
- **QR Codes dynamiques** : Cible modifiable après création
- **Personnalisation** : Couleurs personnalisées, ajout de logo
- **Analytics** : Suivi des scans (IP, pays, user-agent, timestamp)
- **Dashboard admin** : Interface de gestion complète
- **Assistant de création** : Modal 4 étapes avec prévisualisation

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | FastAPI 0.95.2, Uvicorn |
| ORM | SQLAlchemy 1.4.49 |
| Base de données | SQLite (dev) / PostgreSQL (prod) |
| Auth | JWT (python-jose), bcrypt (passlib) |
| QR Codes | segno, Pillow |
| Frontend | HTML5, CSS3, JavaScript vanilla |
| Déploiement | Vercel (serverless) |

## Installation

### Prérequis

- Python 3.10+
- pip

### Mise en place

```bash
# Cloner le repo
git clone <url-du-repo>
cd 2qrgen

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Dépendances
pip install -r backend/requirements.txt

# Configuration
cp backend/.env.example backend/.env
# Éditer backend/.env avec vos valeurs
```

### Lancer le serveur

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## URLs

| Page | URL |
|------|-----|
| Accueil (création QR) | http://localhost:8000/ |
| Dashboard admin | http://localhost:8000/admin |
| Documentation API | http://localhost:8000/docs |

## Variables d'environnement

### Requises

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé de signature JWT (32+ caractères) |
| `ADMIN_PASSWORD` | Mot de passe admin |
| `DATABASE_URL` | URL de connexion (optionnel en dev, SQLite par défaut) |

### Optionnelles

| Variable | Description | Défaut |
|----------|-------------|--------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée du token JWT | 15 |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Durée du refresh token | 1440 |
| `SMTP_HOST` | Serveur email | - |
| `SMTP_PORT` | Port SMTP | 587 |
| `SMTP_USER` | Utilisateur SMTP | - |
| `SMTP_PASSWORD` | Mot de passe SMTP | - |
| `EMAIL_FROM` | Adresse expéditeur | no-reply@example.com |

## Structure du projet

```
2qrgen/
├── backend/
│   ├── app/
│   │   ├── main.py           # App FastAPI et routes
│   │   ├── models.py         # Modèles SQLAlchemy
│   │   ├── schemas.py        # Schémas Pydantic
│   │   ├── db.py             # Connexion DB
│   │   ├── auth.py           # Authentification JWT
│   │   ├── routes_auth.py    # Endpoints auth
│   │   ├── routes_admin.py   # Endpoints admin
│   │   ├── routes_qr.py      # CRUD QR codes
│   │   └── qrcode_redirect.py # Redirections QR
│   ├── templates/            # Templates Jinja2
│   ├── static/               # CSS, images
│   └── requirements.txt
├── api/
│   └── index.py              # Entry point Vercel
├── tests/                    # Tests pytest
├── vercel.json               # Config Vercel
└── .env.example
```

## API Endpoints

### QR Codes (`/api/qrcodes/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/` | Créer un QR code |
| GET | `/` | Lister les QR codes |
| PATCH | `/{id}` | Modifier un QR dynamique |
| GET | `/{id}/image` | Obtenir l'image QR |
| GET | `/{id}/analytics` | Stats de scans |

### Admin (`/admin/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/login` | Page de connexion |
| POST | `/login` | Authentification |
| POST | `/logout` | Déconnexion |
| GET | `/api/admin/stats` | Statistiques |

### Redirection

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/q/{slug}` | Redirection QR + tracking |

## Tests

```bash
pytest tests/ -v
```

## Déploiement Vercel

```bash
# Installer Vercel CLI
npm install -g vercel

# Déployer
vercel

# Configurer les variables d'environnement dans le dashboard Vercel
```

Variables requises sur Vercel :
- `DATABASE_URL` (PostgreSQL)
- `SECRET_KEY`
- `ADMIN_PASSWORD`

## Modèles de données

### QRCode

| Champ | Type | Description |
|-------|------|-------------|
| slug | string | Identifiant unique |
| title | string | Titre du QR |
| content | string | URL ou données |
| is_dynamic | boolean | Modifiable après création |
| options | JSON | Couleurs, logo |

### Click (Analytics)

| Champ | Type | Description |
|-------|------|-------------|
| qr_id | FK | Référence QR code |
| timestamp | datetime | Date/heure du scan |
| ip | string | Adresse IP |
| user_agent | string | Navigateur |
| country | string | Pays (si disponible) |

## Licence

MIT
# Dynamique-Qrcode
# Dynamique-Qrcode
# Dynamique-Qrcode
