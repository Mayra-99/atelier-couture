"""
Schémas Pydantic des utilisateurs.

Pydantic vérifie les données reçues AVANT qu'elles n'arrivent dans notre code :
mauvais type, champ manquant, valeur interdite -> 422 automatiquement.
On a un schéma distinct pour la création, la modification et la lecture (section 3).
Le schéma de lecture ne contient PAS le hash du mot de passe (RG21).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["admin", "tailleur", "accueil"]


class UtilisateurCreation(BaseModel):
    email: EmailStr
    nom_complet: str = Field(min_length=1, max_length=150)
    mot_de_passe: str = Field(min_length=8, description="8 caractères minimum (RG21)")
    role: Role


class UtilisateurModification(BaseModel):
    # Tout est facultatif : PATCH ne change que les champs envoyés
    nom_complet: str | None = Field(default=None, min_length=1, max_length=150)
    role: Role | None = None
    actif: bool | None = None
    mot_de_passe: str | None = Field(default=None, min_length=8)


class UtilisateurLecture(BaseModel):
    # from_attributes : Pydantic sait lire un objet SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime


class Jeton(BaseModel):
    """Réponse de POST /auth/login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # en secondes
