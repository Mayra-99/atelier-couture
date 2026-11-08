"""
seed.py : remplit la base au démarrage.  Lancer :  python -m app.seed

- crée le premier administrateur (e-mail et mot de passe lus dans .env)
- crée le catalogue de départ (annexe B)
- si DEMO_MOT_DE_PASSE est rempli : crée aussi un compte accueil et un compte tailleur
Le script peut être relancé sans danger : il ne crée que ce qui manque.
"""
from sqlalchemy import select

from app.config import reglages
from app.database import SessionLocal
from app.models import TypeVetement, Utilisateur
from app.securite import hacher_mot_de_passe

CATALOGUE = [
    ("Boubou", "Boubou homme en bazin ou brodé", 35000, 10),
    ("Costume 2 pièces", "Veste et pantalon", 85000, 14),
    ("Robe", "Robe sur mesure", 30000, 7),
    ("Ensemble wax", "Tenue deux pièces en wax", 25000, 7),
    ("Chemise", "Chemise sur mesure", 15000, 5),
    ("Pantalon", "Pantalon sur mesure", 12000, 4),
    ("Retouche", "Ourlet, rétrécissement, remplacement de fermeture", 3000, 2),
]


def creer_compte(db, email: str, nom: str, mot_de_passe: str, role: str) -> None:
    if db.scalar(select(Utilisateur).where(Utilisateur.email == email.lower())):
        print(f"  = compte {email} déjà présent")
        return
    if len(mot_de_passe) < 8:
        raise SystemExit(f"Mot de passe trop court pour {email} (8 caractères minimum).")
    db.add(Utilisateur(email=email.lower(), nom_complet=nom, role=role, actif=True,
                       mot_de_passe_hash=hacher_mot_de_passe(mot_de_passe)))
    print(f"  + compte {role} créé : {email}")


def main() -> None:
    if not reglages.ADMIN_MOT_DE_PASSE:
        raise SystemExit("ADMIN_MOT_DE_PASSE est vide : remplissez-le dans le fichier .env")
    with SessionLocal() as db:
        print("Comptes :")
        creer_compte(db, reglages.ADMIN_EMAIL, reglages.ADMIN_NOM, reglages.ADMIN_MOT_DE_PASSE, "admin")
        if reglages.DEMO_MOT_DE_PASSE:
            creer_compte(db, "accueil@atelier.sn", "Awa (accueil)", reglages.DEMO_MOT_DE_PASSE, "accueil")
            creer_compte(db, "tailleur@atelier.sn", "Ousmane (tailleur)", reglages.DEMO_MOT_DE_PASSE, "tailleur")
        print("Catalogue :")
        for nom, description, prix, delai in CATALOGUE:
            if db.scalar(select(TypeVetement).where(TypeVetement.nom == nom)):
                print(f"  = {nom} déjà présent")
                continue
            db.add(TypeVetement(nom=nom, description=description, prix_base=prix, delai_jours=delai, actif=True))
            print(f"  + {nom} ({prix} FCFA, {delai} jours)")
        db.commit()
    print("Initialisation terminée.")


if __name__ == "__main__":
    main()
