"""
main.py : le point d'entrée de l'API.

On crée l'application FastAPI, on branche tous les routeurs sous /api/v1,
et on transforme nos erreurs en réponses {"detail": "message en français"}.
Swagger (la documentation interactive) est sur /docs.
"""
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.erreurs import ErreurMetier
from app.routers import auth, catalogue, clients, commandes, livraisons, mesures, paiements, statistiques, utilisateurs

app = FastAPI(
    title="API Atelier de couture",
    description="Back-end de gestion de l'atelier de Mamadou : clients, mesures, commandes, "
                "paiements, livraisons et statistiques.",
    version="1.0.0",
)

# Toutes les routes métier sont préfixées par /api/v1
for module in (auth, utilisateurs, clients, catalogue, mesures, commandes, paiements, livraisons, statistiques):
    app.include_router(module.router, prefix="/api/v1")


@app.exception_handler(ErreurMetier)
def erreur_metier(_: Request, erreur: ErreurMetier):
    """Introuvable -> 404, Conflit -> 409, DonneesInvalides -> 422, Interdit -> 403."""
    return JSONResponse(status_code=erreur.code_http, content={"detail": erreur.message})


@app.exception_handler(RequestValidationError)
def erreur_validation(_: Request, erreur: RequestValidationError):
    """Erreurs Pydantic -> 422 avec un message français lisible (section 8)."""
    messages = []
    for e in erreur.errors():
        champ = ".".join(str(x) for x in e["loc"] if x not in ("body", "query", "path"))
        message = str(e.get("msg", "")).removeprefix("Value error, ")
        messages.append(f"{champ} : {message}" if champ else message)
    return JSONResponse(
        status_code=422,
        content={"detail": "Données invalides. " + " ; ".join(messages)},
    )


@app.get("/health", tags=["Santé"], summary="Vérifie que l'API et la base répondent")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "erreur", "detail": "La base ne répond pas."})
    return {"status": "ok"}
