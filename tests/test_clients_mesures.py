"""Tests clients et mesures : RG1 à RG4."""


def test_rg1_telephone_normalise_et_doublon_409(accueil, fatou):
    assert fatou["telephone"] == "771234567"
    r = accueil.post("/api/v1/clients", json={"nom": "Ndiaye", "prenom": "Awa", "telephone": "771234567"})
    assert r.status_code == 409


def test_rg1_telephone_invalide_422(accueil):
    r = accueil.post("/api/v1/clients", json={"nom": "Sow", "prenom": "Ali", "telephone": "12ab"})
    assert r.status_code == 422
    assert "téléphone" in r.json()["detail"]


def test_patch_client_ne_peut_pas_vider_le_nom_et_garde_son_numero(accueil, fatou):
    assert accueil.patch(f"/api/v1/clients/{fatou['id']}", json={"nom": ""}).status_code == 422
    r = accueil.patch(f"/api/v1/clients/{fatou['id']}", json={"telephone": "77.123.45.67", "notes": "VIP"})
    assert r.status_code == 200 and r.json()["notes"] == "VIP"


def test_liste_paginee_et_recherche(accueil, fatou):
    accueil.post("/api/v1/clients", json={"nom": "Ba", "prenom": "Moussa", "telephone": "780000000"})
    r = accueil.get("/api/v1/clients", params={"q": "Diop"}).json()
    assert r["total"] == 1 and r["items"][0]["prenom"] == "Fatou" and r["limit"] == 20 and r["offset"] == 0
    tous = accueil.get("/api/v1/clients").json()["items"]
    assert [c["nom"] for c in tous] == ["Ba", "Diop"]  # trié par nom
    assert accueil.get("/api/v1/clients", params={"q": "D"}).status_code == 422  # 2 caractères minimum


def test_rg2_au_moins_une_mesure_et_bornes(tailleur, fatou):
    url = f"/api/v1/clients/{fatou['id']}/mesures"
    assert tailleur.post(url, json={}).status_code == 422
    assert tailleur.post(url, json={"tour_taille": 0}).status_code == 422
    assert tailleur.post(url, json={"tour_taille": 301}).status_code == 422
    r = tailleur.post(url, json={"tour_taille": 72, "longueur_robe": 140})
    assert r.status_code == 201 and r.json()["prise_par_id"] is not None


def test_accueil_ne_peut_pas_prendre_les_mesures_403(accueil, fatou):
    assert accueil.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 72}).status_code == 403


def test_rg3_dernieres_mesures(tailleur, fatou):
    url = f"/api/v1/clients/{fatou['id']}/mesures"
    assert tailleur.get(url + "/derniere").status_code == 404
    tailleur.post(url, json={"tour_taille": 70, "date_prise": "2026-01-10"})
    tailleur.post(url, json={"tour_taille": 75, "date_prise": "2026-03-10"})
    assert tailleur.get(url + "/derniere").json()["tour_taille"] == 75
    assert len(tailleur.get(url).json()) == 2  # l'historique est conservé


def test_patch_mesure_ne_peut_pas_tout_effacer(tailleur, fatou):
    m = tailleur.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 70}).json()
    assert tailleur.patch(f"/api/v1/mesures/{m['id']}", json={"tour_taille": None}).status_code == 422
    assert tailleur.patch(f"/api/v1/mesures/{m['id']}", json={"tour_taille": 71}).json()["tour_taille"] == 71


def test_rg4_suppressions_interdites(admin, tailleur, fatou, commande):
    # Fatou a une commande : impossible de la supprimer
    assert admin.delete(f"/api/v1/clients/{fatou['id']}").status_code == 409


def test_rg4_mesure_utilisee_par_une_commande(accueil, tailleur, fatou, ):
    m = tailleur.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 70}).json()
    boubou = next(p["id"] for p in accueil.get("/api/v1/catalogue").json() if p["nom"] == "Boubou")
    accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "lignes": [{"type_vetement_id": boubou}]})
    assert tailleur.delete(f"/api/v1/mesures/{m['id']}").status_code == 409


def test_suppression_client_sans_commande(admin, fatou):
    assert admin.delete(f"/api/v1/clients/{fatou['id']}").status_code == 204
    assert admin.get(f"/api/v1/clients/{fatou['id']}").status_code == 404
