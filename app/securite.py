"""
securite.py : mots de passe et jetons JWT.

1) Mots de passe (RG21) : on ne stocke JAMAIS le mot de passe, seulement son "hash"
   (une empreinte impossible à inverser), calculé avec Argon2.
   Pour vérifier, on recalcule et on compare.

2) Jetons JWT (RG22) : après la connexion, l'API donne un "badge" signé (le jeton).
   Le badge contient l'id de l'utilisateur et une date d'expiration.
   À chaque requête, le client renvoie le badge dans l'en-tête :
       Authorization: Bearer <jeton>
   Comme il est signé avec SECRET_KEY, personne ne peut le fabriquer ou le modifier.
"""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import reglages

# PasswordHash.recommended() utilise Argon2 (algorithme recommandé par l'énoncé)
_hacheur = PasswordHash.recommended()


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_enregistre: str) -> bool:
    return _hacheur.verify(mot_de_passe, hash_enregistre)


def creer_jeton(utilisateur_id: int) -> tuple[str, int]:
    """Fabrique un jeton signé. Renvoie (jeton, durée de validité en secondes)."""
    duree = timedelta(minutes=reglages.DUREE_JETON_MINUTES)
    contenu = {
        "sub": str(utilisateur_id),                      # "sub" = à qui appartient le jeton
        "exp": datetime.now(timezone.utc) + duree,       # date d'expiration
    }
    jeton = jwt.encode(contenu, reglages.SECRET_KEY, algorithm=reglages.ALGORITHME_JWT)
    return jeton, int(duree.total_seconds())


def lire_jeton(jeton: str) -> int | None:
    """Renvoie l'id de l'utilisateur si le jeton est valide, sinon None."""
    try:
        contenu = jwt.decode(jeton, reglages.SECRET_KEY, algorithms=[reglages.ALGORITHME_JWT])
        return int(contenu["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        # signature fausse, jeton expiré, contenu bizarre... -> invalide
        return None
