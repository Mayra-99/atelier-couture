"""Schémas Pydantic du catalogue des prestations (TypeVetement)."""
from pydantic import BaseModel, ConfigDict, Field


class PrestationCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    description: str | None = None
    prix_base: int = Field(ge=0, description="Prix en FCFA")
    delai_jours: int = Field(ge=0, description="Délai de confection en jours")
    actif: bool = True


class PrestationModification(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    prix_base: int | None = Field(default=None, ge=0)
    delai_jours: int | None = Field(default=None, ge=0)
    actif: bool | None = None


class PrestationLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
