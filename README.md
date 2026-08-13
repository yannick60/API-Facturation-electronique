# API de gestion de facturation

API REST permettant de gérer les entreprises, les clients, les factures et les échanges de factures électroniques.

L'API permet notamment de générer des factures au format UBL 2.1, de gérer les identifiants de facturation électronique et de communiquer avec une plateforme de dématérialisation partenaire.

---

## 🚀 Fonctionnalités

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

# 🏗️ Architecture

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
       │  Database   │       │ UBL / XML    │       │    PDP      │
       │             │       │ Generation   │       │             │
       │ SQLite /    │       │              │       │ OAuth2      │
       │ PostgreSQL  │       │ EN 16931     │       │ API         │
       └─────────────┘       └─────────────┘       └─────────────┘
```
