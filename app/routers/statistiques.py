"""Routeur "statistiques" : réservé à l'administrateur (le patron)."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import Pagination, exiger_roles
from app.models import Utilisateur
from app.schemas.commandes import CommandeResume
from app.schemas.commun import Page
from app.schemas.statistiques import PeriodeChiffreAffaires, StatTypeVetement, TableauDeBord, TopClient
from app.services import statistiques as service

router = APIRouter(prefix="/statistiques", tags=["Statistiques"])
admin = exiger_roles("admin")


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    return service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=list[PeriodeChiffreAffaires])
def chiffre_affaires(
    granularite: Literal["jour", "mois"] = "jour",
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin),
):
    return service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[StatTypeVetement])
def types_vetement(
    date_debut: date | None = None, date_fin: date | None = None,
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin),
):
    return service.par_type_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient])
def top_clients(
    date_debut: date | None = None, date_fin: date | None = None,
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin),
):
    return service.top_clients(db, date_debut, date_fin, limite)


@router.get("/impayes", response_model=Page[CommandeResume])
def impayes(pagination: Pagination = Depends(), db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    items, total = service.impayes(db, pagination.limit, pagination.offset)
    return {"items": items, "total": total, "limit": pagination.limit, "offset": pagination.offset}
