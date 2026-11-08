"""Tests de la sécurité : connexion (RG21-RG23), droits par rôle (401 / 403), RG24."""


def test_connexion_ok_renvoie_un_jeton(anonyme):
    r = anonyme.post("/api/v1/auth/login", data={"username": "admin@test.sn", "password": "motdepasse123"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["token_type"] == "bearer" and corps["access_token"] and corps["expires_in"] > 0


def test_rg23_meme_message_email_inconnu_ou_mot_de_passe_faux(anonyme):
    r1 = anonyme.post("/api/v1/auth/login", data={"username": "inconnu@test.sn", "password": "motdepasse123"})
    r2 = anonyme.post("/api/v1/auth/login", data={"username": "admin@test.sn", "password": "mauvais-mdp"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_rg21_me_ne_renvoie_jamais_le_hash(accueil):
    r = accueil.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "accueil"
    assert "mot_de_passe_hash" not in r.json() and "mot_de_passe" not in r.json()


def test_sans_jeton_401(anonyme):
    assert anonyme.get("/api/v1/clients").status_code == 401
    assert anonyme.get("/api/v1/clients", headers={"Authorization": "Bearer faux"}).status_code == 401


def test_role_insuffisant_403(accueil, tailleur):
    assert accueil.get("/api/v1/statistiques/tableau-de-bord").status_code == 403
    assert tailleur.post("/api/v1/catalogue", json={"nom": "X", "prix_base": 1, "delai_jours": 1}).status_code == 403
    assert accueil.get("/api/v1/utilisateurs").status_code == 403


def test_admin_peut_tout_faire(admin, fatou):
    r = admin.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 80})
    assert r.status_code == 201


def test_rg22_compte_desactive_refuse_meme_avec_jeton_valide(admin, accueil):
    moi = accueil.get("/api/v1/auth/me").json()
    assert admin.patch(f"/api/v1/utilisateurs/{moi['id']}", json={"actif": False}).status_code == 200
    assert accueil.get("/api/v1/auth/me").status_code == 401


def test_creation_utilisateur_doublon_et_mot_de_passe_court(admin):
    ok = {"email": "awa@test.sn", "nom_complet": "Awa", "mot_de_passe": "12345678", "role": "accueil"}
    assert admin.post("/api/v1/utilisateurs", json=ok).status_code == 201
    assert admin.post("/api/v1/utilisateurs", json=ok).status_code == 409
    court = {**ok, "email": "b@test.sn", "mot_de_passe": "1234567"}
    assert admin.post("/api/v1/utilisateurs", json=court).status_code == 422


def test_rg24_admin_ne_peut_pas_se_desactiver_ni_se_retirer_admin(admin):
    moi = admin.get("/api/v1/auth/me").json()
    assert admin.patch(f"/api/v1/utilisateurs/{moi['id']}", json={"actif": False}).status_code == 409
    assert admin.patch(f"/api/v1/utilisateurs/{moi['id']}", json={"role": "accueil"}).status_code == 409


def test_health(anonyme):
    assert anonyme.get("/health").json() == {"status": "ok"}
