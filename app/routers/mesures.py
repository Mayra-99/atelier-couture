"""Routeur "mesures" : le tailleur prend et corrige les mesures."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import exiger_roles, utilisateur_courant
from app.erreurs import Introuvable
from app.models import Utilisateur
from app.schemas.mesures import MesureCreation, MesureLecture, MesureModification
from app.services import mesures as service
from app.services.clients import obtenir_client

router = APIRouter(tags=["Mesures"])
tailleur = exiger_roles("tailleur")


@router.post("/clients/{client_id}/mesures", response_model=MesureLecture, status_code=status.HTTP_201_CREATED)
def creer(
    client_id: int, donnees: MesureCreation,
    db: Session = Depends(get_db), moi: Utilisateur = Depends(tailleur),
):
    mesure = service.creer_mesure(db, client_id, donnees, moi)
    db.commit()
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureLecture])
def historique(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.historique_mesures(db, client_id)


@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureLecture)
def derniere(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    obtenir_client(db, client_id)
    mesure = service.dernieres_mesures(db, client_id)
    if mesure is None:
        raise Introuvable("Ce client n'a encore aucune prise de mesures.")
    return mesure


@router.get("/mesures/{mesure_id}", response_model=MesureLecture)
def detail(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.obtenir_mesure(db, mesure_id)


@router.patch("/mesures/{mesure_id}", response_model=MesureLecture)
def corriger(
    mesure_id: int, donnees: MesureModification,
    db: Session = Depends(get_db), _: Utilisateur = Depends(tailleur),
):
    mesure = service.modifier_mesure(db, mesure_id, donnees)
    db.commit()
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tailleur)):
    service.supprimer_mesure(db, mesure_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
