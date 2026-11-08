"""Routeur "utilisateurs" : réservé à l'administrateur."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import exiger_roles
from app.models import Utilisateur
from app.schemas.utilisateurs import UtilisateurCreation, UtilisateurLecture, UtilisateurModification
from app.services import utilisateurs as service

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])
admin = exiger_roles("admin")


@router.post("", response_model=UtilisateurLecture, status_code=status.HTTP_201_CREATED)
def creer(donnees: UtilisateurCreation, db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    utilisateur = service.creer_utilisateur(db, donnees)
    db.commit()
    return utilisateur


@router.get("", response_model=list[UtilisateurLecture])
def lister(db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    return service.lister_utilisateurs(db)


@router.get("/{utilisateur_id}", response_model=UtilisateurLecture)
def detail(utilisateur_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin)):
    return service.obtenir_utilisateur(db, utilisateur_id)


@router.patch("/{utilisateur_id}", response_model=UtilisateurLecture)
def modifier(
    utilisateur_id: int, donnees: UtilisateurModification,
    db: Session = Depends(get_db), moi: Utilisateur = Depends(admin),
):
    utilisateur = service.modifier_utilisateur(db, utilisateur_id, donnees, moi)
    db.commit()
    return utilisateur
