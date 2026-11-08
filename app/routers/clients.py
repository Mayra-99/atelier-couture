"""Routeur "clients"."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import Pagination, exiger_roles, utilisateur_courant
from app.models import Utilisateur
from app.schemas.clients import ClientCreation, ClientLecture, ClientModification, ClientResume, Genre
from app.schemas.commandes import CommandeResume
from app.schemas.commun import Page
from app.services import clients as service

router = APIRouter(prefix="/clients", tags=["Clients"])
# "Tous" dans l'énoncé = tout utilisateur connecté
connecte = utilisateur_courant


@router.post("", response_model=ClientLecture, status_code=status.HTTP_201_CREATED)
def creer(donnees: ClientCreation, db: Session = Depends(get_db), _: Utilisateur = Depends(connecte)):
    client = service.creer_client(db, donnees)
    db.commit()
    return client


@router.get("", response_model=Page[ClientLecture])
def lister(
    q: str | None = Query(None, min_length=2, description="Recherche dans nom, prénom, téléphone"),
    genre: Genre | None = None,
    pagination: Pagination = Depends(),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(connecte),
):
    clients, total = service.lister_clients(db, q, genre, pagination.limit, pagination.offset)
    return {"items": clients, "total": total, "limit": pagination.limit, "offset": pagination.offset}


@router.get("/{client_id}", response_model=ClientLecture)
def detail(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(connecte)):
    return service.obtenir_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientLecture)
def modifier(
    client_id: int, donnees: ClientModification,
    db: Session = Depends(get_db), _: Utilisateur = Depends(connecte),
):
    client = service.modifier_client(db, client_id, donnees)
    db.commit()
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(exiger_roles("admin"))):
    service.supprimer_client(db, client_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/commandes", response_model=Page[CommandeResume])
def commandes(
    client_id: int, pagination: Pagination = Depends(),
    db: Session = Depends(get_db), _: Utilisateur = Depends(connecte),
):
    items, total = service.commandes_du_client(db, client_id, pagination.limit, pagination.offset)
    return {"items": items, "total": total, "limit": pagination.limit, "offset": pagination.offset}


@router.get("/{client_id}/resume", response_model=ClientResume)
def resume(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(connecte)):
    return service.resume_client(db, client_id)
