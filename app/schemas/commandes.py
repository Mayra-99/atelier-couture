"""Schémas Pydantic des commandes, lignes, statuts et historique."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.livraisons import LivraisonLecture
from app.schemas.paiements import PaiementLecture

Statut = Literal[
    "en_attente", "en_coupe", "en_couture", "essayage",
    "retouches", "terminee", "livree", "annulee",
]


class LigneCreation(BaseModel):
    type_vetement_id: int
    description: str | None = None
    quantite: int = Field(default=1, ge=1)
    # Facultatif : par défaut, le prix de base du catalogue (RG6)
    prix_unitaire: int | None = Field(default=None, ge=0, description="Prix négocié en FCFA")


class CommandeCreation(BaseModel):
    client_id: int
    mesure_id: int | None = None
    lignes: list[LigneCreation] = Field(min_length=1, description="Au moins une ligne")
    remise: int = Field(default=0, ge=0)
    date_livraison_prevue: date | None = None
    notes: str | None = None


class CommandeModification(BaseModel):
    mesure_id: int | None = None
    date_livraison_prevue: date | None = None
    remise: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ChangementStatut(BaseModel):
    statut: Statut
    commentaire: str | None = None


class LigneLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_vetement_id: int
    nom_prestation: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


class HistoriqueLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ancien_statut: str | None
    nouveau_statut: str
    commentaire: str | None
    utilisateur_id: int | None
    date_changement: datetime


class CommandeResume(BaseModel):
    """Un élément de la liste GET /commandes (route 25)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str | None
    client_id: int
    client_nom: str
    statut: Statut
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool


class CommandeDetail(CommandeResume):
    """Le détail complet (route 26)."""
    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    notes: str | None
    cree_par_id: int | None
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneLecture]
    paiements: list[PaiementLecture]
    livraison: LivraisonLecture | None
