"""Service "mesures" : RG2 (au moins une mesure), RG3 (historique), RG4 (suppression)."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, DonneesInvalides, Introuvable
from app.models import CHAMPS_MESURES, Commande, Mesure, Utilisateur
from app.schemas.mesures import MesureCreation, MesureModification
from app.services.clients import obtenir_client


def creer_mesure(
    db: Session, client_id: int, donnees: MesureCreation, tailleur: Utilisateur
) -> Mesure:
    obtenir_client(db, client_id)  # 404 si le client n'existe pas
    valeurs = donnees.model_dump()
    valeurs["date_prise"] = valeurs["date_prise"] or date.today()  # aujourd'hui par défaut
    mesure = Mesure(client_id=client_id, prise_par_id=tailleur.id, **valeurs)
    db.add(mesure)
    db.flush()
    return mesure


def historique_mesures(db: Session, client_id: int) -> list[Mesure]:
    """RG3 : toutes les prises, la plus récente d'abord."""
    obtenir_client(db, client_id)
    return list(
        db.scalars(
            select(Mesure)
            .where(Mesure.client_id == client_id)
            .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        )
    )


def dernieres_mesures(db: Session, client_id: int) -> Mesure | None:
    """RG3 : les "dernières mesures" = la prise de date la plus récente."""
    return db.scalar(
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        .limit(1)
    )


def obtenir_mesure(db: Session, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable(f"Prise de mesures {mesure_id} introuvable.")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, donnees: MesureModification) -> Mesure:
    mesure = obtenir_mesure(db, mesure_id)
    changements = donnees.model_dump(exclude_unset=True)
    # On simule la correction pour vérifier qu'il restera au moins une mesure (RG2)
    apres = {champ: changements.get(champ, getattr(mesure, champ)) for champ in CHAMPS_MESURES}
    if all(v is None for v in apres.values()):
        raise DonneesInvalides(
            "Correction refusée : la prise de mesures doit garder au moins une mesure (RG2)."
        )
    for champ, valeur in changements.items():
        if champ == "date_prise" and valeur is None:
            continue  # la date de prise ne peut pas être vidée
        setattr(mesure, champ, valeur)
    db.flush()
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    mesure = obtenir_mesure(db, mesure_id)
    # RG4 : des mesures utilisées par une commande ne peuvent pas être supprimées
    nb = db.scalar(select(func.count()).where(Commande.mesure_id == mesure.id))
    if nb:
        raise Conflit(f"Impossible de supprimer ces mesures : {nb} commande(s) les utilisent.")
    db.delete(mesure)
    db.flush()
