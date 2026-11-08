# API de gestion d'un atelier de couture

Back-end REST de l'atelier de Mamadou (tailleur à Dakar) : clients et historique des mesures,
commandes et suivi de la production, acomptes et soldes, livraisons, statistiques du patron.

**Technologies :** Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Pydantic, JWT (Argon2), pytest, Docker.

---

## 1. Lancer le projet avec Docker (méthode recommandée)

Prérequis : Docker Desktop installé et démarré.

```bash
git clone <url-du-depot>
cd atelier-couture
cp .env.example .env        # puis ouvrez .env et changez les mots de passe et SECRET_KEY
docker compose up --build
```

Au démarrage, le conteneur de l'API :
1. crée les tables avec `alembic upgrade head` ;
2. crée l'administrateur, les comptes de démonstration et le catalogue avec `python -m app.seed` ;
3. lance l'API sur le port 8000.

Ouvrez ensuite :
- la documentation interactive Swagger : http://localhost:8000/docs
- la route de santé : http://localhost:8000/health

Pour tout arrêter : `docker compose down` (ajoutez `-v` pour effacer aussi la base).

## 2. Lancer le projet sans Docker (PostgreSQL installé sur la machine)

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash) ; sous Linux/Mac : source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # adaptez DATABASE_URL à votre PostgreSQL local
alembic upgrade head               # crée les tables
python -m app.seed                 # crée l'admin, les comptes de démo et le catalogue
uvicorn app.main:app --reload      # lance l'API sur http://localhost:8000/docs
```

## 3. Lancer les tests

```bash
pytest -q
```

Les tests utilisent une base SQLite en mémoire, recréée pour chaque test (rien à installer).
Pour les lancer sur PostgreSQL : `TEST_DATABASE_URL=postgresql+psycopg://user:mdp@localhost:5432/atelier_test pytest -q`.

45 tests : au moins un par règle de gestion importante, les droits par rôle (401 / 403),
et le scénario complet de démonstration de l'annexe A (`test_scenario_annexe_a`).

## 4. Comptes de test

Créés par `python -m app.seed` à partir du fichier `.env` :

| Rôle | E-mail | Mot de passe |
|---|---|---|
| admin (le patron) | valeur de `ADMIN_EMAIL` (par défaut `admin@atelier.sn`) | valeur de `ADMIN_MOT_DE_PASSE` |
| accueil | `accueil@atelier.sn` | valeur de `DEMO_MOT_DE_PASSE` |
| tailleur | `tailleur@atelier.sn` | valeur de `DEMO_MOT_DE_PASSE` |

Dans Swagger : cliquez sur **Authorize**, saisissez l'e-mail dans `username` et le mot de passe dans `password`.

## 5. Organisation du code

```
app/
├── main.py           # crée l'application, branche les routeurs, traduit les erreurs en {"detail": ...}
├── config.py         # lit les réglages du fichier .env
├── database.py       # connexion à PostgreSQL, session par requête
├── models.py         # les tables SQLAlchemy (noms de champs de l'énoncé)
├── securite.py       # hachage Argon2 et jetons JWT
├── dependances.py    # utilisateur connecté (401), contrôle des rôles (403), pagination
├── erreurs.py        # erreurs métier : Introuvable 404, Interdit 403, Conflit 409, DonneesInvalides 422
├── seed.py           # python -m app.seed
├── schemas/          # schémas Pydantic : création / modification / lecture, par domaine
├── services/         # TOUTE la logique métier (règles RG1 à RG24), testable séparément
└── routers/          # un fichier par domaine : droits -> service -> commit
alembic/versions/     # migration initiale complète
tests/                # tests pytest
```

Règles d'architecture respectées : les routeurs ne contiennent aucune règle de gestion ;
les modèles SQLAlchemy ne sont jamais renvoyés tels quels (toujours un schéma de lecture, jamais le hash du mot de passe) ;
aucun secret dans le code (tout est dans `.env`, exclu par `.gitignore`).

## 6. Routes réalisées (44 / 44)

Toutes les routes sont préfixées par `/api/v1`, sauf `/health`.

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 1 | POST | /auth/login | Public |
| 2 | GET | /auth/me | Connecté |
| 3 | POST | /utilisateurs | Admin |
| 4 | GET | /utilisateurs | Admin |
| 5 | GET | /utilisateurs/{id} | Admin |
| 6 | PATCH | /utilisateurs/{id} | Admin |
| 7 | POST | /clients | Tous |
| 8 | GET | /clients | Tous |
| 9 | GET | /clients/{id} | Tous |
| 10 | PATCH | /clients/{id} | Tous |
| 11 | DELETE | /clients/{id} | Admin |
| 12 | GET | /clients/{id}/commandes | Tous |
| 13 | GET | /clients/{id}/resume | Tous |
| 14 | POST | /catalogue | Admin |
| 15 | GET | /catalogue | Tous |
| 16 | GET | /catalogue/{id} | Tous |
| 17 | PATCH | /catalogue/{id} | Admin |
| 18 | POST | /clients/{id}/mesures | Tailleur |
| 19 | GET | /clients/{id}/mesures | Tous |
| 20 | GET | /clients/{id}/mesures/derniere | Tous |
| 21 | GET | /mesures/{id} | Tous |
| 22 | PATCH | /mesures/{id} | Tailleur |
| 23 | DELETE | /mesures/{id} | Tailleur |
| 24 | POST | /commandes | Accueil |
| 25 | GET | /commandes | Tous |
| 26 | GET | /commandes/{id} | Tous |
| 27 | PATCH | /commandes/{id} | Accueil |
| 28 | POST | /commandes/{id}/statut | Tous (RG13-14) |
| 29 | GET | /commandes/{id}/historique | Tous |
| 30 | POST | /commandes/{id}/lignes | Accueil |
| 31 | DELETE | /commandes/{id}/lignes/{ligne_id} | Accueil |
| 32 | POST | /commandes/{id}/paiements | Accueil |
| 33 | GET | /commandes/{id}/paiements | Tous |
| 34 | DELETE | /paiements/{id} | Admin |
| 35 | PUT | /commandes/{id}/livraison | Accueil |
| 36 | GET | /commandes/{id}/livraison | Tous |
| 37 | POST | /commandes/{id}/livraison/confirmer | Accueil |
| 38 | GET | /livraisons | Tous |
| 39 | GET | /statistiques/tableau-de-bord | Admin |
| 40 | GET | /statistiques/chiffre-affaires | Admin |
| 41 | GET | /statistiques/types-vetement | Admin |
| 42 | GET | /statistiques/top-clients | Admin |
| 43 | GET | /statistiques/impayes | Admin |
| 44 | GET | /health | Public |

L'administrateur est autorisé partout. Sans jeton valide : 401. Rôle insuffisant : 403.

## 7. Choix et précisions

- **Connexion :** par e-mail (champ `username` du formulaire OAuth2), comme indiqué dans le modèle de données et la route 1.
- **Numéro de commande :** `CMD-<année>-<id sur 5 chiffres>`, par exemple `CMD-2026-00017` (unique car basé sur l'identifiant).
- **Messages d'erreur :** toujours `{"detail": "message en français"}`, y compris pour les erreurs de validation Pydantic.
- **Statut « livree » :** posé uniquement par `POST /commandes/{id}/livraison/confirmer` (RG13, RG20).
- **Tableau de bord :** `nb_commandes_mois` compte les commandes non annulées du mois ; `livraisons_du_jour` compte les livraisons planifiées pour aujourd'hui.
- **Tests :** SQLite en mémoire (autorisé par l'énoncé pour les tests) ; l'application elle-même utilise uniquement PostgreSQL et Alembic.
