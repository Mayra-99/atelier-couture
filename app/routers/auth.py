"""
Routeur "auth" : se connecter et voir son profil.

Rôle d'un routeur : recevoir la requête, vérifier les droits, appeler le service,
valider la transaction (commit), renvoyer la réponse. Aucune règle de gestion ici.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependances import utilisateur_courant
from app.models import Utilisateur
from app.schemas.utilisateurs import Jeton, UtilisateurLecture
from app.securite import creer_jeton
from app.services import utilisateurs as service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton, summary="Se connecter (username = e-mail)")
def login(formulaire: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    utilisateur = service.authentifier(db, formulaire.username, formulaire.password)
    if utilisateur is None:
        # RG23 : même message que l'e-mail soit inconnu ou le mot de passe faux
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=service.MESSAGE_CONNEXION_ECHOUEE,
            headers={"WWW-Authenticate": "Bearer"},
        )
    jeton, duree = creer_jeton(utilisateur.id)
    return Jeton(access_token=jeton, token_type="bearer", expires_in=duree)


@router.get("/me", response_model=UtilisateurLecture, summary="Mon profil")
def mon_profil(moi: Utilisateur = Depends(utilisateur_courant)):
    return moi  # response_model filtre : le hash du mot de passe n'est jamais renvoyé
