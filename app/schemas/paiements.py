"""Schémas Pydantic des paiements."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModePaiement = Literal["especes", "wave", "orange_money", "virement", "cheque"]


class PaiementCreation(BaseModel):
    montant: int = Field(gt=0, description="Strictement positif, en FCFA (RG16)")
    mode: ModePaiement
    reference: str | None = None
    date_paiement: date | None = None  # aujourd'hui par défaut, jamais dans le futur


class PaiementLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int | None
    created_at: datetime
