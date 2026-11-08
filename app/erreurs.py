"""
erreurs.py : les erreurs "métier".

Pourquoi ? Les services (la logique de Mamadou) ne doivent pas dépendre de HTTP.
Ils lèvent donc des erreurs simples (Introuvable, Conflit...) et main.py les
transforme en réponse HTTP {"detail": "..."} avec le bon code.
"""


class ErreurMetier(Exception):
    code_http = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Introuvable(ErreurMetier):
    """La ressource n'existe pas -> 404."""
    code_http = 404


class Interdit(ErreurMetier):
    """Connecté, mais pas le bon rôle -> 403."""
    code_http = 403


class Conflit(ErreurMetier):
    """Conflit avec l'état actuel (doublon, transition interdite...) -> 409."""
    code_http = 409


class DonneesInvalides(ErreurMetier):
    """Donnée refusée par une règle de gestion -> 422."""
    code_http = 422
