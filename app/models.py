"""
models.py : les tables de la base de données (SQLAlchemy 2, style moderne).

Chaque classe = une table. Chaque attribut Mapped[...] = une colonne.
Les noms de champs sont EXACTEMENT ceux de l'énoncé (section 5) : la correction s'appuie dessus.

Rappels :
- Mapped[int]            -> colonne obligatoire (NOT NULL)
- Mapped[int | None]     -> colonne facultative (peut être vide)
- ForeignKey("table.id") -> lien vers une autre table
- relationship(...)      -> permet d'écrire commande.lignes, client.mesures...
- Les montants sont des entiers en FCFA, les mesures des nombres en centimètres.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def maintenant() -> datetime:
    """Date et heure actuelles (en UTC)."""
    return datetime.now(timezone.utc)


# Les 18 mesures facultatives (en cm), dans l'ordre de l'énoncé.
# On garde la liste ici pour la réutiliser dans les schémas et les services.
CHAMPS_MESURES = [
    "taille_cm", "tour_cou", "carrure_dos", "longueur_epaule", "tour_poitrine",
    "tour_taille", "tour_bassin", "longueur_manche", "tour_bras", "tour_poignet",
    "longueur_dos", "longueur_haut", "longueur_pantalon", "tour_cuisse", "tour_genou",
    "bas_pantalon", "entrejambe", "longueur_robe",
]


class Utilisateur(Base):
    """Le personnel de l'atelier (admin, accueil, tailleur)."""
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nom_complet: Mapped[str] = mapped_column(String(150))
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))  # jamais le mot de passe en clair (RG21)
    role: Mapped[str] = mapped_column(String(20))  # admin | tailleur | accueil
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str] = mapped_column(String(25), unique=True, index=True)  # RG1 : unique
    email: Mapped[str | None] = mapped_column(String(255))
    adresse: Mapped[str | None] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(10))  # homme | femme | enfant
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=maintenant, onupdate=maintenant
    )

    # 1 client -> N mesures. cascade : supprimer le client supprime aussi ses mesures.
    mesures: Mapped[list["Mesure"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    # 1 client -> N commandes (pas de cascade : on interdit la suppression, RG4)
    commandes: Mapped[list["Commande"]] = relationship(back_populates="client")


class Mesure(Base):
    """Une prise de mesures. On les garde toutes (historique, RG3)."""
    __tablename__ = "mesures"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    date_prise: Mapped[date] = mapped_column(Date)
    prise_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    # Les 18 mesures facultatives, en centimètres
    taille_cm: Mapped[float | None] = mapped_column(Float)
    tour_cou: Mapped[float | None] = mapped_column(Float)
    carrure_dos: Mapped[float | None] = mapped_column(Float)
    longueur_epaule: Mapped[float | None] = mapped_column(Float)
    tour_poitrine: Mapped[float | None] = mapped_column(Float)
    tour_taille: Mapped[float | None] = mapped_column(Float)
    tour_bassin: Mapped[float | None] = mapped_column(Float)
    longueur_manche: Mapped[float | None] = mapped_column(Float)
    tour_bras: Mapped[float | None] = mapped_column(Float)
    tour_poignet: Mapped[float | None] = mapped_column(Float)
    longueur_dos: Mapped[float | None] = mapped_column(Float)
    longueur_haut: Mapped[float | None] = mapped_column(Float)
    longueur_pantalon: Mapped[float | None] = mapped_column(Float)
    tour_cuisse: Mapped[float | None] = mapped_column(Float)
    tour_genou: Mapped[float | None] = mapped_column(Float)
    bas_pantalon: Mapped[float | None] = mapped_column(Float)
    entrejambe: Mapped[float | None] = mapped_column(Float)
    longueur_robe: Mapped[float | None] = mapped_column(Float)

    client: Mapped["Client"] = relationship(back_populates="mesures")


class TypeVetement(Base):
    """Le catalogue des prestations (boubou, robe, retouche...)."""
    __tablename__ = "types_vetement"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    prix_base: Mapped[int] = mapped_column(Integer)  # FCFA
    delai_jours: Mapped[int] = mapped_column(Integer)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Commande(Base):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # CMD-AAAA-NNNNN (RG5). Rempli juste après la création (on a besoin de l'id).
    numero: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id"))
    statut: Mapped[str] = mapped_column(String(20), default="en_attente", index=True)
    date_commande: Mapped[date] = mapped_column(Date)
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    remise: Mapped[int] = mapped_column(Integer, default=0)
    montant_total: Mapped[int] = mapped_column(Integer, default=0)  # calculé par le serveur (RG7)
    montant_paye: Mapped[int] = mapped_column(Integer, default=0)   # calculé par le serveur (RG7)
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=maintenant, onupdate=maintenant
    )

    client: Mapped["Client"] = relationship(back_populates="commandes")
    mesure: Mapped["Mesure | None"] = relationship()
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="LigneCommande.id"
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="Paiement.id"
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="HistoriqueStatut.id"
    )
    livraison: Mapped["Livraison | None"] = relationship(
        back_populates="commande", cascade="all, delete-orphan", uselist=False
    )

    @property
    def solde(self) -> int:
        """Ce que le client doit encore : total - payé (RG7)."""
        return self.montant_total - self.montant_paye

    @property
    def en_retard(self) -> bool:
        """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
        return (
            self.date_livraison_prevue < date.today()
            and self.statut not in ("livree", "annulee")
        )

    @property
    def client_nom(self) -> str:
        return f"{self.client.prenom} {self.client.nom}"


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantite: Mapped[int] = mapped_column(Integer)
    prix_unitaire: Mapped[int] = mapped_column(Integer)  # FCFA, négociable (RG6)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    type_vetement: Mapped["TypeVetement"] = relationship()

    @property
    def sous_total(self) -> int:
        return self.quantite * self.prix_unitaire

    @property
    def nom_prestation(self) -> str:
        return self.type_vetement.nom


class HistoriqueStatut(Base):
    """Chaque changement de statut d'une commande (RG15)."""
    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    ancien_statut: Mapped[str | None] = mapped_column(String(20))  # vide à la création
    nouveau_statut: Mapped[str] = mapped_column(String(20))
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    commande: Mapped["Commande"] = relationship(back_populates="historique")


class Paiement(Base):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    montant: Mapped[int] = mapped_column(Integer)  # FCFA
    mode: Mapped[str] = mapped_column(String(20))  # especes | wave | orange_money | virement | cheque
    reference: Mapped[str | None] = mapped_column(String(100))
    date_paiement: Mapped[date] = mapped_column(Date)
    enregistre_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=maintenant)

    commande: Mapped["Commande"] = relationship(back_populates="paiements")


class Livraison(Base):
    """Une seule livraison par commande (commande_id unique)."""
    __tablename__ = "livraisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), unique=True
    )
    mode: Mapped[str] = mapped_column(String(20))  # retrait_atelier | domicile
    adresse: Mapped[str | None] = mapped_column(String(255))
    livreur: Mapped[str | None] = mapped_column(String(100))
    date_prevue: Mapped[date] = mapped_column(Date)
    date_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(20), default="planifiee")  # planifiee | livree
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="livraison")
