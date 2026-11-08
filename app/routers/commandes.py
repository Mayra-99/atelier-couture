"""Routeur "commandes" : création, suivi, statuts, lignes."""
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import Pagination, exiger_roles, utilisateur_courant
from app.models import Utilisateur
from app.schemas.commandes import (
    ChangementStatut, CommandeCreation, CommandeDetail, CommandeModification,
    CommandeResume, HistoriqueLecture, LigneCreation, Statut,
)
from app.schemas.commun import Page
from app.services import commandes as service

router = APIRouter(prefix="/commandes", tags=["Commandes"])
accueil = exiger_roles("accueil")


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def creer(donnees: CommandeCreation, db: Session = Depends(get_db), moi: Utilisateur = Depends(accueil)):
    commande = service.creer_commande(db, donnees, moi)
    db.commit()
    return commande


@router.get("", response_model=Page[CommandeResume])
def lister(
    statut: Statut | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(utilisateur_courant),
):
    items, total = service.lister_commandes(
        db, pagination.limit, pagination.offset, statut, client_id, en_retard, date_min, date_max, numero
    )
    return {"items": items, "total": total, "limit": pagination.limit, "offset": pagination.offset}


@router.get("/{commande_id}", response_model=CommandeDetail)
def detail(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.obtenir_commande(db, commande_id)


@router.patch("/{commande_id}", response_model=CommandeDetail)
def modifier(
    commande_id: int, donnees: CommandeModification,
    db: Session = Depends(get_db), _: Utilisateur = Depends(accueil),
):
    commande = service.modifier_commande(db, commande_id, donnees)
    db.commit()
    return commande


@router.post("/{commande_id}/statut", response_model=CommandeDetail)
def changer_statut(
    commande_id: int, donnees: ChangementStatut,
    db: Session = Depends(get_db), moi: Utilisateur = Depends(utilisateur_courant),
):
    # "Tous" : les restrictions de rôle (RG14) sont vérifiées dans le service
    commande = service.changer_statut(db, commande_id, donnees, moi)
    db.commit()
    return commande


@router.get("/{commande_id}/historique", response_model=list[HistoriqueLecture])
def historique(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_courant)):
    return service.historique_commande(db, commande_id)


@router.post("/{commande_id}/lignes", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED)
def ajouter_ligne(
    commande_id: int, donnees: LigneCreation,
    db: Session = Depends(get_db), _: Utilisateur = Depends(accueil),
):
    commande = service.ajouter_ligne(db, commande_id, donnees)
    db.commit()
    return commande


@router.delete("/{commande_id}/lignes/{ligne_id}", response_model=CommandeDetail)
def retirer_ligne(
    commande_id: int, ligne_id: int,
    db: Session = Depends(get_db), _: Utilisateur = Depends(accueil),
):
    commande = service.retirer_ligne(db, commande_id, ligne_id)
    db.commit()
    return commande
