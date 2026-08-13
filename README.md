# API de gestion de facturation

API REST permettant de gérer les entreprises, les clients, les factures et les échanges de factures électroniques.

L'API permet notamment de générer des factures au format UBL 2.1, de gérer les identifiants de facturation électronique et de communiquer avec une plateforme de dématérialisation partenaire.

---

## Fonctionnalités

- Authentification des utilisateurs
- Gestion des entreprises
- Gestion des clients
- Gestion des factures
- Gestion des lignes de facture
- Calcul automatique des montants HT, TVA et TTC
- Gestion des conditions de paiement
- Gestion des moyens de paiement
- Génération de factures électroniques au format UBL 2.1
- Compatibilité EN 16931 / Peppol BIS Billing
- Recherche d'un destinataire dans un annuaire de facturation électronique
- Gestion des EndpointID
- Envoi de factures électroniques via une PDP
- Réception de factures électroniques
- Gestion des événements liés aux factures
- Acceptation ou refus des factures reçues
- Suivi du statut des factures
- Intégration OAuth2 avec une plateforme externe

---

# Architecture

```text
                         ┌─────────────────────┐
                         │      Frontend       │
                         │     React / Next    │
                         └──────────┬──────────┘
                                    │
                                    │ HTTP / REST
                                    ▼
                         ┌─────────────────────┐
                         │       FastAPI       │
                         │         API         │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │  Database   │       │ UBL / XML   │       │    PDP      │
       │             │       │ Generation  │       │             │
       │ SQLite /    │       │             │       │ OAuth2      │
       │ PostgreSQL  │       │ EN 16931    │       │ API         │
       └─────────────┘       └─────────────┘       └─────────────┘
```
# Technologies
## Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic
- Uvicorn
## Base de données
- SQLite pour le développement
- PostgreSQL pour la production
## Facturation électronique
- UBL 2.1
- EN 16931
- Peppol BIS Billing 3.0
- XML
- OAuth2
## Infrastructure
- Git
- GitHub
# Installation
## Prérequis
- Python 3.11+
- pip
- Git
- SQLite ou PostgreSQL

## Cloner le projet
```bash
git clone <repository-url>
cd <project-directory>
```
## Créer un environnement virtuel
### Linux / macOS
```bash
python3 -m venv venv
source venv/bin/activate
```
### Windows
```bash
python -m venv venv
venv\Scripts\activate
```
### Installer les dépendances
```bash
pip install -r requirements.txt
```
# Configuration

Créer un fichier .env à la racine du projet.

Exemple :

```python
DATABASE_URL=sqlite+aiosqlite:///./app.db

SECRET_KEY=change-me

PDP_BASE_URL=https://api.example.com

OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback
```

Les valeurs réelles doivent être adaptées à l'environnement utilisé.

# Lancer l'API

En environnement de développement :
```bash
uvicorn app.main:app --reload
```
L'API est alors disponible à l'adresse :

http://127.0.0.1:8000
# Documentation API

La documentation est automatiquement générée par FastAPI.

## Swagger UI
http://127.0.0.1:8000/docs
## ReDoc
http://127.0.0.1:8000/redoc

La documentation Swagger permet de tester directement les endpoints de l'API.
