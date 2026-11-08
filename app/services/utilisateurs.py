"""
Service "utilisateurs" : la logique métier des comptes et de la connexion.

Les services ne font pas de commit : c'est le routeur qui valide la transaction.
Ils lèvent des ErreurMetier (Conflit, Introuvable...) que main.py traduit en HTTP.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.erreurs import Conflit, Introuvable
from app.models import Utilisateur
from app.schemas.utilisateurs import UtilisateurCreation, UtilisateurModification
from app.securite import hacher_mot_de_passe, verifier_mot_de_passe

# RG23 : le même message, que l'e-mail soit inconnu ou le mot de passe faux
MESSAGE_CONNEXION_ECHOUEE = "Identifiants incorrects ou compte désactivé."


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur | None:
    """Renvoie l'utilisateur si e-mail + mot de passe sont bons et le compte actif, sinon None."""
    utilisateur = db.scalar(select(Utilisateur).where(Utilisateur.email == email.lower()))
    if utilisateur is None:
        return None
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hash):
        return None
    if not utilisateur.actif:
        return None
    return utilisateur


def creer_utilisateur(db: Session, donnees: UtilisateurCreation) -> Utilisateur:
    email = donnees.email.lower()
    if db.scalar(select(Utilisateur).where(Utilisateur.email == email)):
        raise Conflit(f"Un compte existe déjà avec l'e-mail {email}.")
    utilisateur = Utilisateur(
        email=email,
        nom_complet=donnees.nom_complet,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),  # RG21
        role=donnees.role,
        actif=True,
    )
    db.add(utilisateur)
    db.flush()  # flush : envoie à la base sans valider, pour obtenir l'id
    return utilisateur


def lister_utilisateurs(db: Session) -> list[Utilisateur]:
    return list(db.scalars(select(Utilisateur).order_by(Utilisateur.nom_complet)))


def obtenir_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise Introuvable(f"Utilisateur {utilisateur_id} introuvable.")
    return utilisateur


def modifier_utilisateur(
    db: Session, utilisateur_id: int, donnees: UtilisateurModification, auteur: Utilisateur
) -> Utilisateur:
    utilisateur = obtenir_utilisateur(db, utilisateur_id)
    # exclude_unset : seulement les champs réellement envoyés (PATCH)
    changements = donnees.model_dump(exclude_unset=True)

    # RG24 : un administrateur ne peut ni se désactiver ni retirer son propre rôle admin
    if utilisateur.id == auteur.id:
        if changements.get("actif") is False:
            raise Conflit("Vous ne pouvez pas désactiver votre propre compte.")
        if "role" in changements and changements["role"] != "admin":
            raise Conflit("Vous ne pouvez pas retirer votre propre rôle d'administrateur.")

    if "mot_de_passe" in changements:
        mot_de_passe = changements.pop("mot_de_passe")
        if mot_de_passe is not None:
            utilisateur.mot_de_passe_hash = hacher_mot_de_passe(mot_de_passe)
    for champ, valeur in changements.items():
        if valeur is not None:
            setattr(utilisateur, champ, valeur)
    db.flush()
    return utilisateur
