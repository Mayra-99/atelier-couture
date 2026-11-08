"""
config.py : les réglages de l'application.

Pourquoi ? L'énoncé interdit d'écrire un mot de passe ou une clé secrète dans le code.
On les met donc dans un fichier .env (jamais envoyé sur GitHub) et on les lit ici.

pydantic-settings lit automatiquement les variables d'environnement
(et le fichier .env) et vérifie leur type.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Reglages(BaseSettings):
    # Adresse de la base PostgreSQL, ex : postgresql+psycopg://user:mdp@localhost:5432/atelier
    DATABASE_URL: str

    # Clé secrète qui sert à signer les jetons JWT (longue chaîne aléatoire)
    SECRET_KEY: str
    ALGORITHME_JWT: str = "HS256"
    DUREE_JETON_MINUTES: int = 60

    # Premier administrateur, créé par "python -m app.seed"
    ADMIN_EMAIL: str = "admin@atelier.sn"
    ADMIN_NOM: str = "Mamadou (patron)"
    ADMIN_MOT_DE_PASSE: str = ""

    # Comptes de démonstration (accueil et tailleur), créés par le seed si un mot de passe est donné
    DEMO_MOT_DE_PASSE: str = ""

    # On dit à pydantic-settings de lire le fichier .env s'il existe
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Un seul objet de réglages, importé partout : from app.config import reglages
reglages = Reglages()
