"""
Service "commandes" : le cœur métier.

Règles appliquées ici : RG5 (numéro), RG6 (prix par défaut), RG7 (montants),
RG8 (date prévue), RG9 (mesures du client), RG10 (lignes), RG11 (retard),
RG12 (commande figée), RG13-RG15 (statuts et historique).
"""
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, DonneesInvalides, Interdit, Introuvable
from app.models import Client, Commande, HistoriqueStatut, LigneCommande, Mesure, TypeVetement, Utilisateur
from app.schemas.commandes import (
    ChangementStatut,
    CommandeCreation,
    CommandeModification,
    LigneCreation,
)
from app.services.mesures import dernieres_mesures

# ----------------------------------------------------------------------------
# Le workflow des statuts (section 6) : pour chaque statut, les suivants autorisés
# ----------------------------------------------------------------------------
TRANSITIONS: dict[str, list[str]] = {
    "en_attente": ["en_coupe", "annulee"],
    "en_coupe": ["en_couture", "annulee"],
    "en_couture": ["essayage", "terminee", "annulee"],
    "essayage": ["retouches", "terminee", "annulee"],
    "retouches": ["essayage", "terminee", "annulee"],
    "terminee": ["livree"],  # uniquement par la confirmation de livraison
    "livree": [],            # statut final
    "annulee": [],           # statut final
}
TOUS_LES_STATUTS = list(TRANSITIONS)
STATUTS_FINAUX = ("livree", "annulee")


# ----------------------------------------------------------------------------
# Petites fonctions utiles
# ----------------------------------------------------------------------------
def condition_en_retard(aujourd_hui: date | None = None):
    """RG11 écrite en SQL : date prévue dépassée, ni livrée ni annulée."""
    aujourd_hui = aujourd_hui or date.today()
    return and_(
        Commande.date_livraison_prevue < aujourd_hui,
        Commande.statut.not_in(STATUTS_FINAUX),
    )


def obtenir_commande(db: Session, commande_id: int) -> Commande:
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise Introuvable(f"Commande {commande_id} introuvable.")
    return commande


def verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable."""
    if commande.statut in STATUTS_FINAUX:
        raise Conflit(
            f"La commande {commande.numero} est « {commande.statut} » : elle n'est plus modifiable."
        )


def recalculer_montants(commande: Commande) -> None:
    """
    RG7 : c'est le SERVEUR qui calcule.
      total = somme(quantité × prix unitaire) − remise
      payé  = somme des paiements
      solde = total − payé  (propriété Commande.solde)
    """
    somme_prestations = sum(ligne.quantite * ligne.prix_unitaire for ligne in commande.lignes)
    if commande.remise > somme_prestations:
        raise DonneesInvalides(
            f"La remise ({commande.remise} FCFA) dépasse la somme des prestations "
            f"({somme_prestations} FCFA)."
        )
    nouveau_total = somme_prestations - commande.remise
    montant_paye = sum(p.montant for p in commande.paiements)
    # RG7 : un changement ne peut jamais ramener le total sous le montant déjà payé
    if nouveau_total < montant_paye:
        raise Conflit(
            f"Modification refusée : le nouveau total ({nouveau_total} FCFA) serait inférieur "
            f"au montant déjà payé ({montant_paye} FCFA)."
        )
    commande.montant_total = nouveau_total
    commande.montant_paye = montant_paye


def _choisir_mesure(db: Session, client_id: int, mesure_id: int | None) -> int | None:
    """RG9 : la mesure doit appartenir au client ; sinon, les dernières mesures du client."""
    if mesure_id is None:
        derniere = dernieres_mesures(db, client_id)
        return derniere.id if derniere else None
    mesure = db.get(Mesure, mesure_id)
    if mesure is None or mesure.client_id != client_id:
        raise DonneesInvalides(
            f"La prise de mesures {mesure_id} n'appartient pas au client {client_id} (RG9)."
        )
    return mesure.id


def _construire_ligne(db: Session, donnees: LigneCreation) -> LigneCommande:
    """RG6 : prix par défaut = prix du catalogue ; prestation inactive interdite (422)."""
    prestation = db.get(TypeVetement, donnees.type_vetement_id)
    if prestation is None:
        raise DonneesInvalides(f"Prestation {donnees.type_vetement_id} introuvable dans le catalogue.")
    if not prestation.actif:
        raise DonneesInvalides(
            f"La prestation « {prestation.nom} » n'est plus au catalogue : elle ne peut plus être commandée."
        )
    prix = donnees.prix_unitaire if donnees.prix_unitaire is not None else prestation.prix_base
    ligne = LigneCommande(
        type_vetement_id=prestation.id,
        description=donnees.description,
        quantite=donnees.quantite,
        prix_unitaire=prix,
    )
    ligne.type_vetement = prestation
    return ligne


def ajouter_historique(
    commande: Commande,
    ancien: str | None,
    nouveau: str,
    utilisateur: Utilisateur,
    commentaire: str | None = None,
) -> None:
    """RG15 : chaque changement de statut est enregistré."""
    commande.historique.append(
        HistoriqueStatut(
            ancien_statut=ancien,
            nouveau_statut=nouveau,
            commentaire=commentaire,
            utilisateur_id=utilisateur.id,
        )
    )


# ----------------------------------------------------------------------------
# Les opérations
# ----------------------------------------------------------------------------
def creer_commande(db: Session, donnees: CommandeCreation, auteur: Utilisateur) -> Commande:
    if db.get(Client, donnees.client_id) is None:
        raise Introuvable(f"Client {donnees.client_id} introuvable.")

    aujourd_hui = date.today()
    lignes = [_construire_ligne(db, l) for l in donnees.lignes]

    # RG8 : date prévue par défaut = date de commande + le plus long délai des prestations
    if donnees.date_livraison_prevue is None:
        delai_max = max(l.type_vetement.delai_jours for l in lignes)
        date_prevue = aujourd_hui + timedelta(days=delai_max)
    else:
        date_prevue = donnees.date_livraison_prevue
        if date_prevue < aujourd_hui:
            raise DonneesInvalides(
                "La date de livraison prévue ne peut pas précéder la date de commande (RG8)."
            )

    commande = Commande(
        client_id=donnees.client_id,
        mesure_id=_choisir_mesure(db, donnees.client_id, donnees.mesure_id),
        statut="en_attente",
        date_commande=aujourd_hui,
        date_livraison_prevue=date_prevue,
        remise=donnees.remise,
        notes=donnees.notes,
        cree_par_id=auteur.id,
        lignes=lignes,
        paiements=[],
    )
    recalculer_montants(commande)
    # RG15 : la création inscrit la première ligne d'historique (ancien statut vide)
    ajouter_historique(commande, None, "en_attente", auteur, "Création de la commande")
    db.add(commande)
    db.flush()  # on obtient l'id...
    # ... pour fabriquer le numéro RG5 : CMD-AAAA-NNNNN, ex CMD-2026-00017
    commande.numero = f"CMD-{commande.date_commande.year}-{commande.id:05d}"
    db.flush()
    return commande


def lister_commandes(
    db: Session,
    limit: int,
    offset: int,
    statut: str | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
) -> tuple[list[Commande], int]:
    requete = select(Commande)
    if statut:
        requete = requete.where(Commande.statut == statut)
    if client_id:
        requete = requete.where(Commande.client_id == client_id)
    if en_retard is True:
        requete = requete.where(condition_en_retard())
    elif en_retard is False:
        requete = requete.where(~condition_en_retard())
    if date_min:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.ilike(f"%{numero}%"))
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    commandes = db.scalars(
        requete.order_by(Commande.date_commande.desc(), Commande.id.desc()).limit(limit).offset(offset)
    )
    return list(commandes), total


def modifier_commande(db: Session, commande_id: int, donnees: CommandeModification) -> Commande:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)  # 409 si livrée ou annulée
    changements = donnees.model_dump(exclude_unset=True)

    if "mesure_id" in changements:
        if changements["mesure_id"] is None:
            commande.mesure_id = None
        else:
            commande.mesure_id = _choisir_mesure(db, commande.client_id, changements["mesure_id"])
    if changements.get("date_livraison_prevue") is not None:
        if changements["date_livraison_prevue"] < commande.date_commande:
            raise DonneesInvalides(
                "La date de livraison prévue ne peut pas précéder la date de commande (RG8)."
            )
        commande.date_livraison_prevue = changements["date_livraison_prevue"]
    if changements.get("remise") is not None:
        commande.remise = changements["remise"]
    if "notes" in changements:
        commande.notes = changements["notes"]

    recalculer_montants(commande)  # RG7 : on recalcule toujours
    db.flush()
    return commande


def changer_statut(
    db: Session, commande_id: int, donnees: ChangementStatut, utilisateur: Utilisateur
) -> Commande:
    commande = obtenir_commande(db, commande_id)
    actuel, demande = commande.statut, donnees.statut

    # RG13 : demander le statut déjà en cours est refusé
    if demande == actuel:
        raise Conflit(f"La commande est déjà au statut « {actuel} ».")
    # RG13 : "livree" ne se pose pas ici, c'est la confirmation de livraison qui le fait
    if demande == "livree":
        raise Conflit(
            "Le statut « livree » ne peut pas être posé ici : "
            "utilisez la confirmation de livraison (POST /commandes/{id}/livraison/confirmer)."
        )
    # RG14 : le tailleur ne peut pas annuler une commande
    if demande == "annulee" and utilisateur.role == "tailleur":
        raise Interdit("Le tailleur ne peut pas annuler une commande.")

    # Le workflow : la transition doit être dans le tableau, sinon 409 avec les statuts possibles
    possibles = TRANSITIONS[actuel]
    if demande not in possibles:
        texte_possibles = ", ".join(sorted(possibles)) if possibles else "aucun (statut final)"
        raise Conflit(
            f"Transition interdite : {actuel} → {demande}. Statuts possibles : {texte_possibles}."
        )

    # RG14 : annuler une commande qui a reçu un acompte exige un commentaire (sort de l'argent)
    if demande == "annulee" and commande.montant_paye > 0 and not (donnees.commentaire or "").strip():
        raise DonneesInvalides(
            f"Cette commande a reçu {commande.montant_paye} FCFA : un commentaire expliquant "
            "le sort de l'argent (remboursement, avoir...) est obligatoire pour l'annuler."
        )

    commande.statut = demande
    ajouter_historique(commande, actuel, demande, utilisateur, donnees.commentaire)  # RG15
    db.flush()
    return commande


def historique_commande(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    return list(obtenir_commande(db, commande_id).historique)  # déjà trié par id (chronologique)


def ajouter_ligne(db: Session, commande_id: int, donnees: LigneCreation) -> Commande:
    commande = obtenir_commande(db, commande_id)
    verifier_modifiable(commande)
    # RG10 : les lignes ne sont modifiables que tant que la commande est "en_attente"
    if commande.statut != "en_attente":
        raise Conflit(
            f"Les lignes ne sont modifiables qu'au statut « en_attente » (statut actuel : {commande.statut})."
        )
    commande.lignes.append(_construire_ligne(db, donnees))
    recalculer_montants(commande)
    db.flush()
    return commande


def retirer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    commande = obtenir_commande(db, commande_id)
    ligne = next((l for l in commande.lignes if l.id == ligne_id), None)
    if ligne is None:
        raise Introuvable(f"Ligne {ligne_id} introuvable dans cette commande.")
    verifier_modifiable(commande)
    if commande.statut != "en_attente":
        raise Conflit(
            f"Les lignes ne sont modifiables qu'au statut « en_attente » (statut actuel : {commande.statut})."
        )
    # RG10 : une commande garde toujours au moins une ligne
    if len(commande.lignes) == 1:
        raise Conflit("Impossible de retirer la dernière ligne : une commande garde au moins une ligne.")
    commande.lignes.remove(ligne)
    recalculer_montants(commande)
    db.flush()
    return commande
