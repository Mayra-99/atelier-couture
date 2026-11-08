"""Service "catalogue" : les prestations (boubou, robe...)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, Introuvable
from app.models import TypeVetement
from app.schemas.catalogue import PrestationCreation, PrestationModification


def _verifier_nom_libre(db: Session, nom: str, sauf_id: int | None = None):
    requete = select(TypeVetement).where(TypeVetement.nom == nom)
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    if db.scalar(requete):
        raise Conflit(f"Une prestation nommée « {nom} » existe déjà.")


def creer_prestation(db: Session, donnees: PrestationCreation) -> TypeVetement:
    _verifier_nom_libre(db, donnees.nom)
    prestation = TypeVetement(**donnees.model_dump())
    db.add(prestation)
    db.flush()
    return prestation


def lister_prestations(db: Session, actifs_seulement: bool = True) -> list[TypeVetement]:
    requete = select(TypeVetement).order_by(TypeVetement.nom)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return list(db.scalars(requete))


def obtenir_prestation(db: Session, prestation_id: int) -> TypeVetement:
    prestation = db.get(TypeVetement, prestation_id)
    if prestation is None:
        raise Introuvable(f"Prestation {prestation_id} introuvable.")
    return prestation


def modifier_prestation(
    db: Session, prestation_id: int, donnees: PrestationModification
) -> TypeVetement:
    """actif=False retire la prestation du catalogue, sans toucher aux anciennes commandes
    (les lignes gardent leur propre prix_unitaire)."""
    prestation = obtenir_prestation(db, prestation_id)
    changements = donnees.model_dump(exclude_unset=True)
    if changements.get("nom"):
        _verifier_nom_libre(db, changements["nom"], sauf_id=prestation.id)
    for champ, valeur in changements.items():
        if valeur is not None or champ == "description":
            setattr(prestation, champ, valeur)
    db.flush()
    return prestation
