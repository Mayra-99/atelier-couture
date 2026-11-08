"""Service "paiements" : RG16 (contrôles) et RG17 (annulation par l'admin)."""
from datetime import date

from sqlalchemy.orm import Session

from app.erreurs import Conflit, DonneesInvalides, Introuvable
from app.models import Paiement, Utilisateur
from app.schemas.paiements import PaiementCreation
from app.services.commandes import obtenir_commande, recalculer_montants


def encaisser(db: Session, commande_id: int, donnees: PaiementCreation, auteur: Utilisateur) -> Paiement:
    commande = obtenir_commande(db, commande_id)
    # RG16 : refusé sur une commande annulée
    if commande.statut == "annulee":
        raise Conflit("Impossible d'encaisser un paiement sur une commande annulée.")
    date_paiement = donnees.date_paiement or date.today()
    # RG16 : pas de date future
    if date_paiement > date.today():
        raise DonneesInvalides("La date de paiement ne peut pas être dans le futur.")
    # RG16 : pas plus que le solde restant (le montant > 0 est déjà vérifié par le schéma)
    if donnees.montant > commande.solde:
        raise Conflit(
            f"Paiement refusé : {donnees.montant} FCFA dépasse le solde restant "
            f"({commande.solde} FCFA)."
        )
    paiement = Paiement(
        montant=donnees.montant,
        mode=donnees.mode,
        reference=donnees.reference,
        date_paiement=date_paiement,
        enregistre_par_id=auteur.id,
    )
    commande.paiements.append(paiement)
    recalculer_montants(commande)  # montant payé et solde mis à jour
    db.flush()
    return paiement


def lister_paiements(db: Session, commande_id: int) -> list[Paiement]:
    return list(obtenir_commande(db, commande_id).paiements)  # ordre de saisie (id)


def annuler_paiement(db: Session, paiement_id: int) -> None:
    """RG17 : l'admin annule un paiement saisi par erreur, le solde est recalculé."""
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise Introuvable(f"Paiement {paiement_id} introuvable.")
    commande = paiement.commande
    commande.paiements.remove(paiement)
    commande.montant_paye = sum(p.montant for p in commande.paiements)
    db.flush()
