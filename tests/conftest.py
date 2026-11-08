"""
conftest.py : la préparation commune à tous les tests (pytest le lit automatiquement).

- Une base de test toute neuve pour CHAQUE test : SQLite en mémoire par défaut
  (autorisé par l'énoncé pour les tests), ou PostgreSQL si TEST_DATABASE_URL est défini.
- On remplace la dépendance get_db de l'API par notre base de test.
- On crée 3 comptes (admin, accueil, tailleur) et le catalogue.
- Des "fixtures" donnent aux tests un client HTTP déjà connecté avec le bon rôle.
"""
import os

# Valeurs par défaut pour que les tests tournent même sans fichier .env
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "cle-de-test-uniquement-0123456789abcdef")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import TypeVetement, Utilisateur
from app.seed import CATALOGUE
from app.securite import hacher_mot_de_passe

URL_TEST = os.environ.get("TEST_DATABASE_URL", "sqlite://")
if URL_TEST.startswith("sqlite"):
    moteur = create_engine(URL_TEST, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    moteur = create_engine(URL_TEST)
SessionTest = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)

MOT_DE_PASSE = "motdepasse123"
COMPTES = {
    "admin": "admin@test.sn",
    "accueil": "accueil@test.sn",
    "tailleur": "tailleur@test.sn",
}
_HASH = hacher_mot_de_passe(MOT_DE_PASSE)  # calculé une seule fois (Argon2 est lent exprès)


def get_db_test():
    db = SessionTest()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def base_neuve():
    """Avant chaque test : tables vides + comptes + catalogue. Après : on efface tout."""
    Base.metadata.drop_all(moteur)
    Base.metadata.create_all(moteur)
    with SessionTest() as db:
        for role, email in COMPTES.items():
            db.add(Utilisateur(email=email, nom_complet=f"Compte {role}", role=role,
                               actif=True, mot_de_passe_hash=_HASH))
        for nom, description, prix, delai in CATALOGUE:
            db.add(TypeVetement(nom=nom, description=description, prix_base=prix, delai_jours=delai, actif=True))
        db.commit()
    app.dependency_overrides[get_db] = get_db_test
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(moteur)


def _client_connecte(role: str) -> TestClient:
    client = TestClient(app)
    reponse = client.post("/api/v1/auth/login", data={"username": COMPTES[role], "password": MOT_DE_PASSE})
    assert reponse.status_code == 200, reponse.text
    client.headers["Authorization"] = f"Bearer {reponse.json()['access_token']}"
    return client


@pytest.fixture
def anonyme():
    return TestClient(app)


@pytest.fixture
def admin():
    return _client_connecte("admin")


@pytest.fixture
def accueil():
    return _client_connecte("accueil")


@pytest.fixture
def tailleur():
    return _client_connecte("tailleur")


# ---- Petits raccourcis réutilisés dans plusieurs tests ---------------------
def id_prestation(client: TestClient, nom: str) -> int:
    return next(p["id"] for p in client.get("/api/v1/catalogue").json() if p["nom"] == nom)


@pytest.fixture
def fatou(accueil):
    """La cliente Fatou Diop (scénario de l'annexe A)."""
    r = accueil.post("/api/v1/clients", json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def commande(accueil, fatou):
    """Une commande : 2 boubous + 1 pantalon négocié à 10 000, remise 5 000 -> total 75 000."""
    r = accueil.post("/api/v1/commandes", json={
        "client_id": fatou["id"],
        "lignes": [
            {"type_vetement_id": id_prestation(accueil, "Boubou"), "quantite": 2},
            {"type_vetement_id": id_prestation(accueil, "Pantalon"), "quantite": 1, "prix_unitaire": 10000},
        ],
        "remise": 5000,
    })
    assert r.status_code == 201, r.text
    return r.json()


def avancer(client: TestClient, commande_id: int, *statuts: str):
    for statut in statuts:
        r = client.post(f"/api/v1/commandes/{commande_id}/statut", json={"statut": statut})
        assert r.status_code == 200, r.text
    return r.json()
