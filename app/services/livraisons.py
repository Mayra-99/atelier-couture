"""Service "livraisons" : RG18 (planification), RG19 et RG20 (confirmation)."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, DonneesInvalides, Introuvable
from app.models import Commande, Livraison, Utilisateur
from app.schemas.livraisons import LivraisonConfirmation, LivraisonPlanification
from app.services.commandes import ajouter_historique, obtenir_commande, verifier_modifiable


def planifier(db: Session, commande_id: int, donnees: LivraisonPlanification) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # 409 si livrée ou annulée
    # RG18 : une livraison à domicile exige une adresse
    if donnees.mode == "domicile" and not (donnees.adresse or "").strip():
        raise DonneesInvalides("Une livraison à domicile exige une adresse.")
    if donnees.date_prevue < commande.date_commande:
        raise DonneesInvalides("La date de livraison ne peut pas précéder la date de commande.")

    livraison = commande.livraison
    if livraison is None:  # première planification
        livraison = Livraison(statut="planifiee")
        commande.livraison = livraison
    # Replanifier modifie la livraison existante, sans en créer une seconde (RG18)
    livraison.mode = donnees.mode
    livraison.date_prevue = donnees.date_prevue
    livraison.adresse = donnees.adresse
    livraison.livreur = donnees.livreur
    livraison.notes = donnees.notes
    # RG18 : planifier met à jour la date de livraison prévue de la commande
    commande.date_livraison_prevue = donnees.date_prevue
    db.flush()
    return livraison


def obtenir_livraison(db: Session, commande_id: int) -> Livraison:
    commande = obtenir_commande(db, commande_id)
    if commande.livraison is None:
        raise Introuvable("Aucune livraison n'est planifiée pour cette commande.")
    return commande.livraison


def confirmer(
    db: Session, commande_id: int, donnees: LivraisonConfirmation, auteur: Utilisateur
) -> Commande:
    commande = obtenir_commande(db, commande_id)
    # RG19 : la commande doit être "terminee"
    if commande.statut != "terminee":
        raise Conflit(
            f"Livraison impossible : la commande doit être « terminee » (statut actuel : {commande.statut})."
        )
    commentaire = "Livraison confirmée"
    # RG19 : et soldée, sauf autorisation explicite
    if commande.solde > 0:
        if not donnees.autoriser_solde_impaye:
            raise Conflit(
                f"Livraison refusée : il reste {commande.solde} FCFA à payer. "
                "Encaissez le solde, ou envoyez autoriser_solde_impaye=true."
            )
        commentaire = f"Livrée avec un solde impayé de {commande.solde} FCFA (autorisé)."

    date_effective = donnees.date_effective or date.today()
    # RG20 : sans planification, on crée une livraison "retrait_atelier"
    if commande.livraison is None:
        commande.livraison = Livraison(mode="retrait_atelier", date_prevue=date_effective)
    commande.livraison.statut = "livree"
    commande.livraison.date_effective = date_effective
    commande.date_livraison_reelle = date_effective
    commande.statut = "livree"
    ajouter_historique(commande, "terminee", "livree", auteur, commentaire)  # RG15
    db.flush()
    return commande


def lister_livraisons(
    db: Session, limit: int, offset: int, statut: str | None = None,
    date_min: date | None = None, date_max: date | None = None,
) -> tuple[list[Livraison], int]:
    requete = select(Livraison)
    if statut:
        requete = requete.where(Livraison.statut == statut)
    if date_min:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max:
        requete = requete.where(Livraison.date_prevue <= date_max)
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    livraisons = db.scalars(requete.order_by(Livraison.date_prevue, Livraison.id).limit(limit).offset(offset))
    return list(livraisons), total
