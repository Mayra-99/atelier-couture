"""Service "statistiques" (administrateur). Calculs simples en Python, lisibles."""
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.erreurs import DonneesInvalides
from app.models import Commande, Livraison, Paiement
from app.services.commandes import TOUS_LES_STATUTS, condition_en_retard


def _periode_par_defaut(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    """Par défaut : du 1er du mois à aujourd'hui. 422 si début > fin."""
    aujourd_hui = date.today()
    date_debut = date_debut or aujourd_hui.replace(day=1)
    date_fin = date_fin or aujourd_hui
    if date_debut > date_fin:
        raise DonneesInvalides("date_debut doit être antérieure ou égale à date_fin.")
    return date_debut, date_fin


def _commandes_valides(db: Session, debut: date, fin: date) -> list[Commande]:
    """Commandes non annulées, datées à la date de commande."""
    return list(db.scalars(
        select(Commande).where(
            Commande.statut != "annulee",
            Commande.date_commande >= debut,
            Commande.date_commande <= fin,
        )
    ))


def tableau_de_bord(db: Session) -> dict:
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    commandes_mois = _commandes_valides(db, debut_mois, aujourd_hui)
    encaisse_mois = db.scalar(
        select(func.coalesce(func.sum(Paiement.montant), 0)).where(
            Paiement.date_paiement >= debut_mois, Paiement.date_paiement <= aujourd_hui
        )
    )
    non_annulees = list(db.scalars(select(Commande).where(Commande.statut != "annulee")))
    par_statut = {statut: 0 for statut in TOUS_LES_STATUTS}  # tous les statuts, même à 0
    for statut, nombre in db.execute(select(Commande.statut, func.count()).group_by(Commande.statut)):
        par_statut[statut] = nombre
    return {
        "chiffre_affaires_mois": sum(c.montant_total for c in commandes_mois),
        "encaisse_mois": encaisse_mois,
        "nb_commandes_mois": len(commandes_mois),
        "reste_a_encaisser": sum(c.solde for c in non_annulees),
        "commandes_par_statut": par_statut,
        "nb_commandes_en_retard": db.scalar(select(func.count()).where(condition_en_retard())),
        "commandes_pretes_a_livrer": par_statut["terminee"],
        "livraisons_du_jour": db.scalar(
            select(func.count()).where(Livraison.date_prevue == aujourd_hui, Livraison.statut == "planifiee")
        ),
    }


def chiffre_affaires(db: Session, granularite: str, date_debut: date | None, date_fin: date | None) -> list[dict]:
    debut, fin = _periode_par_defaut(date_debut, date_fin)

    def cle(d: date) -> str:
        return d.isoformat() if granularite == "jour" else d.strftime("%Y-%m")

    periodes: dict[str, dict] = defaultdict(lambda: {"chiffre_affaires": 0, "encaisse": 0})
    for c in _commandes_valides(db, debut, fin):
        periodes[cle(c.date_commande)]["chiffre_affaires"] += c.montant_total
    paiements = db.scalars(select(Paiement).where(Paiement.date_paiement >= debut, Paiement.date_paiement <= fin))
    for p in paiements:
        periodes[cle(p.date_paiement)]["encaisse"] += p.montant
    # Seules les périodes avec activité sont listées, dans l'ordre chronologique
    return [{"periode": k, **v} for k, v in sorted(periodes.items())]


def par_type_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict]:
    debut, fin = _periode_par_defaut(date_debut, date_fin)
    stats: dict[int, dict] = {}
    for commande in _commandes_valides(db, debut, fin):
        for ligne in commande.lignes:
            s = stats.setdefault(ligne.type_vetement_id, {
                "type_vetement_id": ligne.type_vetement_id, "nom": ligne.type_vetement.nom,
                "quantite_vendue": 0, "chiffre_affaires": 0,
            })
            s["quantite_vendue"] += ligne.quantite
            s["chiffre_affaires"] += ligne.sous_total  # avant remise
    return sorted(stats.values(), key=lambda s: s["chiffre_affaires"], reverse=True)


def top_clients(db: Session, date_debut: date | None, date_fin: date | None, limite: int) -> list[dict]:
    debut, fin = _periode_par_defaut(date_debut, date_fin)
    stats: dict[int, dict] = {}
    for c in _commandes_valides(db, debut, fin):
        s = stats.setdefault(c.client_id, {
            "client_id": c.client_id, "client_nom": c.client_nom, "telephone": c.client.telephone,
            "nb_commandes": 0, "chiffre_affaires": 0, "solde_du": 0,
        })
        s["nb_commandes"] += 1
        s["chiffre_affaires"] += c.montant_total
        s["solde_du"] += c.solde
    return sorted(stats.values(), key=lambda s: s["chiffre_affaires"], reverse=True)[:limite]


def impayes(db: Session, limit: int, offset: int) -> tuple[list[Commande], int]:
    """Commandes non annulées non soldées, la date prévue la plus proche d'abord."""
    requete = select(Commande).where(
        Commande.statut != "annulee", Commande.montant_total > Commande.montant_paye
    )
    total = db.scalar(select(func.count()).select_from(requete.subquery()))
    commandes = db.scalars(
        requete.order_by(Commande.date_livraison_prevue, Commande.id).limit(limit).offset(offset)
    )
    return list(commandes), total
