"""Routeur "catalogue" des prestations."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import exiger_roles, utilisateur_courant
from app.models import Utilisateur
from app.schemas.catalogue import PrestationCreation, PrestationLecture, PrestationModification
from app.services import catalogue as service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])
admin = exiger_roles("admin")


@router.post("", response_model=PrestationLecture, status_code=status.HTTP_201_CREATED)
def creer(donnees: PrestationCreation, db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    prestation = service.creer_prestation(db, donnees)
    db.commit()
    return prestation


@router.get("", response_model=list[PrestationLecture])
def lister(actifs_seulement: bool = True, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.lister_prestations(db, actifs_seulement)


@router.get("/{prestation_id}", response_model=PrestationLecture)
def detail(prestation_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.obtenir_prestation(db, prestation_id)


@router.patch("/{prestation_id}", response_model=PrestationLecture)
def modifier(
    prestation_id: int, donnees: PrestationModification,
    db: Session = Depends(get_db), _: Utilisateur = Depends(admin),
):
    prestation = service.modifier_prestation(db, prestation_id, donnees)
    db.commit()
    return prestation
