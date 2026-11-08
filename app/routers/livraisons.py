"""Routeur "livraisons"."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import Pagination, exiger_roles, utilisateur_courant
from app.models import Utilisateur
from app.schemas.commandes import CommandeDetail
from app.schemas.commun import Page
from app.schemas.livraisons import (
    LivraisonConfirmation, LivraisonLecture, LivraisonPlanification, LivraisonTournee,
)
from app.services import livraisons as service

router = APIRouter(tags=["Livraisons"])
accueil = exiger_roles("accueil")


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonLecture)
def planifier(
    commande_id: int, donnees: LivraisonPlanification,
    db: Session = Depends(get_db), _: Utilisateur = Depends(accueil),
):
    livraison = service.planifier(db, commande_id, donnees)
    db.commit()
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonLecture)
def detail(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.obtenir_livraison(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=CommandeDetail)
def confirmer(
    commande_id: int,
    donnees: LivraisonConfirmation | None = Body(default=None),  # corps facultatif
    db: Session = Depends(get_db), moi: Utilisateur = Depends(accueil),
):
    commande = service.confirmer(db, commande_id, donnees or LivraisonConfirmation(), moi)
    db.commit()
    return commande


@router.get("/livraisons", response_model=Page[LivraisonTournee])
def tournee(
    statut: Literal["planifiee", "livree"] | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(utilisateur_courant),
):
    livraisons, total = service.lister_livraisons(db, pagination.limit, pagination.offset, statut, date_min, date_max)
    items = [
        LivraisonTournee(
            **LivraisonLecture.model_validate(l).model_dump(),
            numero_commande=l.commande.numero,
            client_nom=l.commande.client_nom,
            client_telephone=l.commande.client.telephone,
            solde_commande=l.commande.solde,
        )
        for l in livraisons
    ]
    return {"items": items, "total": total, "limit": pagination.limit, "offset": pagination.offset}
