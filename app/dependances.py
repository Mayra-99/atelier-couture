"""
dependances.py : ce que les routes "demandent" à FastAPI avant de s'exécuter.

- utilisateur_courant : lit le jeton, retrouve l'utilisateur. Sinon 401.
- exiger_roles("accueil") : vérifie le rôle. Sinon 403.
  L'administrateur (le patron) est TOUJOURS autorisé (section 4 de l'énoncé).
- Pagination : les paramètres limit / offset communs à toutes les listes.
"""
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Utilisateur
from app.securite import lire_jeton

# tokenUrl : l'adresse de connexion, utilisée par le bouton "Authorize" de Swagger
schema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ERREUR_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentification requise : jeton absent, invalide ou expiré.",
    headers={"WWW-Authenticate": "Bearer"},
)


def utilisateur_courant(
    jeton: str | None = Depends(schema_oauth2),
    db: Session = Depends(get_db),
) -> Utilisateur:
    if not jeton:
        raise ERREUR_401
    utilisateur_id = lire_jeton(jeton)
    if utilisateur_id is None:
        raise ERREUR_401
    utilisateur = db.get(Utilisateur, utilisateur_id)
    # RG22 : un compte désactivé est refusé immédiatement, même avec un jeton encore valide
    if utilisateur is None or not utilisateur.actif:
        raise ERREUR_401
    return utilisateur


def exiger_roles(*roles: str):
    """Fabrique une dépendance qui n'accepte que certains rôles (+ admin)."""

    def verifier(utilisateur: Utilisateur = Depends(utilisateur_courant)) -> Utilisateur:
        if utilisateur.role != "admin" and utilisateur.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action réservée au(x) rôle(s) : {', '.join(('admin',) + roles)}.",
            )
        return utilisateur

    return verifier


class Pagination:
    """limit = 20 par défaut (maximum 100), offset = 0 (section 8)."""

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments (max 100)"),
        offset: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    ):
        self.limit = limit
        self.offset = offset
