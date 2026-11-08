"""Schémas Pydantic des livraisons."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

ModeLivraison = Literal["retrait_atelier", "domicile"]


class LivraisonPlanification(BaseModel):
    mode: ModeLivraison
    date_prevue: date
    adresse: str | None = None  # obligatoire si mode = domicile (RG18)
    livreur: str | None = None
    notes: str | None = None


class LivraisonConfirmation(BaseModel):
    date_effective: date | None = None  # aujourd'hui par défaut
    autoriser_solde_impaye: bool = False  # RG19


class LivraisonLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: Literal["planifiee", "livree"]
    notes: str | None


class LivraisonTournee(LivraisonLecture):
    """Un élément de GET /livraisons (route 38)."""
    numero_commande: str | None
    client_nom: str
    client_telephone: str
    solde_commande: int
