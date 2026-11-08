"""
Schémas Pydantic des mesures.

RG2 : toutes les mesures sont facultatives, mais une prise doit en contenir au moins une.
Chaque mesure est strictement positive (> 0) et ne dépasse pas 300 cm.
"""
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import CHAMPS_MESURES

# "Cm" = une mesure facultative, > 0 et <= 300 (RG2). On l'écrit une fois, on la réutilise 18 fois.
Cm = Annotated[float | None, Field(default=None, gt=0, le=300)]


class _LesDixHuitMesures(BaseModel):
    taille_cm: Cm = None
    tour_cou: Cm = None
    carrure_dos: Cm = None
    longueur_epaule: Cm = None
    tour_poitrine: Cm = None
    tour_taille: Cm = None
    tour_bassin: Cm = None
    longueur_manche: Cm = None
    tour_bras: Cm = None
    tour_poignet: Cm = None
    longueur_dos: Cm = None
    longueur_haut: Cm = None
    longueur_pantalon: Cm = None
    tour_cuisse: Cm = None
    tour_genou: Cm = None
    bas_pantalon: Cm = None
    entrejambe: Cm = None
    longueur_robe: Cm = None


class MesureCreation(_LesDixHuitMesures):
    date_prise: date | None = None  # aujourd'hui par défaut
    notes: str | None = None

    # model_validator : vérifie l'objet entier (ici : au moins une mesure remplie)
    @model_validator(mode="after")
    def au_moins_une_mesure(self):
        if all(getattr(self, champ) is None for champ in CHAMPS_MESURES):
            raise ValueError("Une prise de mesures doit contenir au moins une mesure (RG2).")
        return self


class MesureModification(_LesDixHuitMesures):
    # On peut corriger une mesure, ou l'effacer en envoyant null.
    # La règle "il doit rester au moins une mesure" est vérifiée dans le service.
    date_prise: date | None = None
    notes: str | None = None


class MesureLecture(_LesDixHuitMesures):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int | None
    notes: str | None
