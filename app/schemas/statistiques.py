"""Schémas Pydantic des statistiques (administrateur)."""
from pydantic import BaseModel


class TableauDeBord(BaseModel):
    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int
    reste_a_encaisser: int
    commandes_par_statut: dict[str, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class PeriodeChiffreAffaires(BaseModel):
    periode: str  # "2026-11-05" (jour) ou "2026-11" (mois)
    chiffre_affaires: int
    encaisse: int


class StatTypeVetement(BaseModel):
    type_vetement_id: int
    nom: str
    quantite_vendue: int
    chiffre_affaires: int


class TopClient(BaseModel):
    client_id: int
    client_nom: str
    telephone: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int
