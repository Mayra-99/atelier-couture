"""Schémas Pydantic des clients (+ règle RG1 sur le téléphone)."""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Genre = Literal["homme", "femme", "enfant"]


def normaliser_telephone(telephone: str) -> str:
    """
    RG1 : on enlève espaces, points, tirets et parenthèses.
    "77 123 45 67" et "771234567" deviennent tous deux "771234567".
    Forme valide : 6 à 20 chiffres, avec un "+" au début facultatif.
    """
    nettoye = re.sub(r"[\s.\-()]", "", telephone)
    if not re.fullmatch(r"\+?\d{6,20}", nettoye):
        raise ValueError(
            "Numéro de téléphone invalide : 6 à 20 chiffres, avec un « + » initial facultatif."
        )
    return nettoye


class ClientCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str
    email: EmailStr | None = None
    adresse: str | None = None
    genre: Genre | None = None
    notes: str | None = None

    # field_validator : une vérification personnalisée, exécutée par Pydantic (-> 422 si erreur)
    @field_validator("telephone")
    @classmethod
    def verifier_telephone(cls, v: str) -> str:
        return normaliser_telephone(v)

    @field_validator("nom", "prenom")
    @classmethod
    def pas_vide(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Ce champ ne peut pas être vide.")
        return v.strip()


class ClientModification(BaseModel):
    nom: str | None = Field(default=None, max_length=100)
    prenom: str | None = Field(default=None, max_length=100)
    telephone: str | None = None
    email: EmailStr | None = None
    adresse: str | None = None
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("nom", "prenom", "telephone")
    @classmethod
    def ne_pas_vider(cls, v: str | None, info) -> str:
        # nom, prénom et téléphone ne peuvent pas être vidés (route 10)
        if v is None or not v.strip():
            raise ValueError(f"Le champ « {info.field_name} » ne peut pas être vidé.")
        if info.field_name == "telephone":
            return normaliser_telephone(v)
        return v.strip()


class ClientLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: Genre | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DerniereCommande(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str | None
    statut: str
    date_commande: date
    montant_total: int


class ClientResume(BaseModel):
    """Route 13 : le résumé d'un client (commandes annulées exclues)."""
    client_id: int
    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: DerniereCommande | None
    a_des_mesures: bool
