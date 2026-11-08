"""Service "clients" : RG1 (téléphone unique), RG4 (suppression), recherche, résumé."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, Introuvable
from app.models import Client, Commande, Mesure
from app.schemas.clients import ClientCreation, ClientModification


def _verifier_telephone_libre(db: Session, telephone: str, sauf_client_id: int | None = None):
    """RG1 : le téléphone identifie le client, il doit être unique (sinon 409)."""
    requete = select(Client).where(Client.telephone == telephone)
    if sauf_client_id is not None:
        # En modification, garder son propre numéro n'est pas un doublon
        requete = requete.where(Client.id != sauf_client_id)
    if db.scalar(requete):
        raise Conflit(f"Un client existe déjà avec le téléphone {telephone}.")


def creer_client(db: Session, donnees: ClientCreation) -> Client:
    # Le téléphone a déjà été normalisé par le schéma (normaliser_telephone)
    _verifier_telephone_libre(db, donnees.telephone)
    client = Client(**donnees.model_dump())
    db.add(client)
    db.flush()
    return client


def obtenir_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise Introuvable(f"Client {client_id} introuvable.")
    return client


def lister_clients(
    db: Session, q: str | None, genre: str | None, limit: int, offset: int
) -> tuple[list[Client], int]:
    """Liste paginée, triée par nom puis prénom. Renvoie (clients, total)."""
    requete = select(Client)
    if q:
        motif = f"%{q}%"
        # On cherche aussi dans le téléphone sans espaces : "77 123" trouve "77123..."
        motif_tel = f"%{q.replace(' ', '')}%"
        requete = requete.where(
            or_(Client.nom.ilike(motif), Client.prenom.ilike(motif), Client.telephone.like(motif_tel))
        )
    if genre:
        requete = requete.where(Client.genre == genre)
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    clients = db.scalars(
        requete.order_by(Client.nom, Client.prenom, Client.id).limit(limit).offset(offset)
    )
    return list(clients), total


def modifier_client(db: Session, client_id: int, donnees: ClientModification) -> Client:
    client = obtenir_client(db, client_id)
    changements = donnees.model_dump(exclude_unset=True)
    if "telephone" in changements:
        _verifier_telephone_libre(db, changements["telephone"], sauf_client_id=client.id)
    for champ, valeur in changements.items():
        setattr(client, champ, valeur)
    db.flush()
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    client = obtenir_client(db, client_id)
    # RG4 : un client qui a des commandes ne peut pas être supprimé
    nb = db.scalar(select(func.count()).where(Commande.client_id == client.id))
    if nb:
        raise Conflit(f"Impossible de supprimer ce client : il a {nb} commande(s).")
    db.delete(client)  # ses mesures sont supprimées aussi (cascade)
    db.flush()


def commandes_du_client(
    db: Session, client_id: int, limit: int, offset: int
) -> tuple[list[Commande], int]:
    obtenir_client(db, client_id)
    requete = select(Commande).where(Commande.client_id == client_id)
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    commandes = db.scalars(
        requete.order_by(Commande.date_commande.desc(), Commande.id.desc()).limit(limit).offset(offset)
    )
    return list(commandes), total


def resume_client(db: Session, client_id: int) -> dict:
    """Route 13 : chiffres du client, commandes annulées exclues."""
    obtenir_client(db, client_id)
    commandes = list(
        db.scalars(
            select(Commande)
            .where(Commande.client_id == client_id, Commande.statut != "annulee")
            .order_by(Commande.date_commande.desc(), Commande.id.desc())
        )
    )
    a_des_mesures = db.scalar(select(func.count()).where(Mesure.client_id == client_id)) > 0
    return {
        "client_id": client_id,
        "nb_commandes": len(commandes),
        "chiffre_affaires": sum(c.montant_total for c in commandes),
        "total_paye": sum(c.montant_paye for c in commandes),
        "solde_du": sum(c.solde for c in commandes),
        "derniere_commande": commandes[0] if commandes else None,
        "a_des_mesures": a_des_mesures,
    }
