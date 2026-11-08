"""Routeur "paiements"."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import exiger_roles, utilisateur_courant
from app.models import Utilisateur
from app.schemas.paiements import PaiementCreation, PaiementLecture
from app.services import paiements as service

router = APIRouter(tags=["Paiements"])


@router.post("/commandes/{commande_id}/paiements", response_model=PaiementLecture, status_code=status.HTTP_201_CREATED)
def encaisser(
    commande_id: int, donnees: PaiementCreation,
    db: Session = Depends(get_db), moi: Utilisateur = Depends(exiger_roles("accueil")),
):
    paiement = service.encaisser(db, commande_id, donnees, moi)
    db.commit()
    return paiement


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementLecture])
def lister(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.lister_paiements(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT)
def annuler(paiement_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(exiger_roles("admin"))):
    service.annuler_paiement(db, paiement_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
