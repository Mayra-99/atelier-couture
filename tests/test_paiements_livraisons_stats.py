"""Tests paiements (RG16-RG17), livraisons (RG18-RG20), statistiques, et scénario de l'annexe A."""
from datetime import date, timedelta

from tests.conftest import avancer


def test_rg16_paiements(accueil, commande):
    url = f"/api/v1/commandes/{commande['id']}/paiements"
    assert accueil.post(url, json={"montant": 0, "mode": "wave"}).status_code == 422
    assert accueil.post(url, json={"montant": 75001, "mode": "wave"}).status_code == 409
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert accueil.post(url, json={"montant": 1000, "mode": "wave", "date_paiement": demain}).status_code == 422
    assert accueil.post(url, json={"montant": 20000, "mode": "wave", "reference": "W123"}).status_code == 201
    assert accueil.get(f"/api/v1/commandes/{commande['id']}").json()["solde"] == 55000


def test_rg16_paiement_sur_commande_annulee_409(accueil, commande):
    accueil.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "annulee"})
    r = accueil.post(f"/api/v1/commandes/{commande['id']}/paiements", json={"montant": 1000, "mode": "especes"})
    assert r.status_code == 409


def test_rg17_admin_annule_un_paiement(admin, accueil, commande):
    p = accueil.post(f"/api/v1/commandes/{commande['id']}/paiements", json={"montant": 20000, "mode": "especes"}).json()
    assert accueil.delete(f"/api/v1/paiements/{p['id']}").status_code == 403
    assert admin.delete(f"/api/v1/paiements/{p['id']}").status_code == 204
    assert admin.get(f"/api/v1/commandes/{commande['id']}").json()["solde"] == 75000
    assert admin.delete(f"/api/v1/paiements/{p['id']}").status_code == 404


def test_rg18_domicile_exige_adresse_et_replanification(accueil, commande):
    url = f"/api/v1/commandes/{commande['id']}/livraison"
    dans5 = (date.today() + timedelta(days=5)).isoformat()
    assert accueil.put(url, json={"mode": "domicile", "date_prevue": dans5}).status_code == 422
    r1 = accueil.put(url, json={"mode": "domicile", "date_prevue": dans5, "adresse": "Médina, Dakar"})
    r2 = accueil.put(url, json={"mode": "retrait_atelier", "date_prevue": dans5})
    assert r1.status_code == r2.status_code == 200 and r1.json()["id"] == r2.json()["id"]  # pas de seconde livraison
    assert accueil.get(f"/api/v1/commandes/{commande['id']}").json()["date_livraison_prevue"] == dans5


def test_rg19_rg20_confirmation(accueil, tailleur, commande):
    cid = commande["id"]
    confirmer = f"/api/v1/commandes/{cid}/livraison/confirmer"
    assert accueil.post(confirmer).status_code == 409  # pas terminée
    avancer(tailleur, cid, "en_coupe", "en_couture", "terminee")
    r = accueil.post(confirmer)
    assert r.status_code == 409 and "75000" in r.json()["detail"]  # pas soldée
    accueil.post(f"/api/v1/commandes/{cid}/paiements", json={"montant": 75000, "mode": "orange_money"})
    r = accueil.post(confirmer)
    assert r.status_code == 200
    corps = r.json()
    assert corps["statut"] == "livree" and corps["solde"] == 0
    assert corps["date_livraison_reelle"] == date.today().isoformat()
    assert corps["livraison"]["mode"] == "retrait_atelier" and corps["livraison"]["statut"] == "livree"  # RG20


def test_rg19_livraison_avec_solde_impaye_autorisee(accueil, tailleur, commande):
    cid = commande["id"]
    avancer(tailleur, cid, "en_coupe", "en_couture", "terminee")
    r = accueil.post(f"/api/v1/commandes/{cid}/livraison/confirmer", json={"autoriser_solde_impaye": True})
    assert r.status_code == 200 and r.json()["solde"] == 75000
    h = accueil.get(f"/api/v1/commandes/{cid}/historique").json()
    assert "impayé" in h[-1]["commentaire"]


def test_statistiques_admin(admin, accueil, commande):
    accueil.post(f"/api/v1/commandes/{commande['id']}/paiements", json={"montant": 20000, "mode": "wave"})
    tdb = admin.get("/api/v1/statistiques/tableau-de-bord").json()
    assert tdb["chiffre_affaires_mois"] == 75000 and tdb["encaisse_mois"] == 20000
    assert tdb["reste_a_encaisser"] == 55000 and tdb["commandes_par_statut"]["essayage"] == 0
    assert admin.get("/api/v1/statistiques/chiffre-affaires", params={"granularite": "mois"}).json()[0]["chiffre_affaires"] == 75000
    assert admin.get("/api/v1/statistiques/chiffre-affaires", params={"date_debut": "2026-12-01", "date_fin": "2026-01-01"}).status_code == 422
    types = admin.get("/api/v1/statistiques/types-vetement").json()
    assert types[0]["nom"] == "Boubou" and types[0]["quantite_vendue"] == 2
    assert admin.get("/api/v1/statistiques/top-clients").json()[0]["solde_du"] == 55000
    assert admin.get("/api/v1/statistiques/impayes").json()["total"] == 1


def test_scenario_annexe_a(admin, accueil, tailleur):
    """Le parcours de démonstration complet de l'annexe A."""
    # 1. Accueil crée Fatou ; un second client avec le même numéro est refusé
    fatou = accueil.post("/api/v1/clients", json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67"}).json()
    assert accueil.post("/api/v1/clients", json={"nom": "X", "prenom": "Y", "telephone": "771234567"}).status_code == 409
    # 2. Tailleur prend les mesures ; l'accueil reçoit 403
    m = tailleur.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 72, "longueur_pantalon": 100})
    assert m.status_code == 201
    assert accueil.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 72}).status_code == 403
    # 3. Commande : 2 boubous + 1 pantalon négocié, avec remise
    cat = {p["nom"]: p["id"] for p in accueil.get("/api/v1/catalogue").json()}
    c = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "remise": 5000, "lignes": [
        {"type_vetement_id": cat["Boubou"], "quantite": 2},
        {"type_vetement_id": cat["Pantalon"], "prix_unitaire": 10000}]}).json()
    assert c["montant_total"] == 75000 and c["mesure_id"] == m.json()["id"]
    ca_avant = admin.get("/api/v1/statistiques/tableau-de-bord").json()["chiffre_affaires_mois"]
    # 4. Passer à terminee directement : refusé
    assert accueil.post(f"/api/v1/commandes/{c['id']}/statut", json={"statut": "terminee"}).status_code == 409
    # 5. Le tailleur avance jusqu'à terminee avec aller-retour essayage/retouches
    avancer(tailleur, c["id"], "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee")
    # 6. Acompte Wave ; paiement supérieur au solde refusé
    assert accueil.post(f"/api/v1/commandes/{c['id']}/paiements", json={"montant": 30000, "mode": "wave"}).status_code == 201
    assert accueil.post(f"/api/v1/commandes/{c['id']}/paiements", json={"montant": 50000, "mode": "wave"}).status_code == 409
    # 7. Livraison refusée : solde non payé
    assert accueil.post(f"/api/v1/commandes/{c['id']}/livraison/confirmer").status_code == 409
    # 8. Solde puis livraison
    accueil.post(f"/api/v1/commandes/{c['id']}/paiements", json={"montant": 45000, "mode": "especes"})
    fin = accueil.post(f"/api/v1/commandes/{c['id']}/livraison/confirmer").json()
    assert fin["statut"] == "livree" and fin["solde"] == 0
    # 9. Admin : tableau de bord ; accueil : 403
    assert ca_avant == 75000
    assert accueil.get("/api/v1/statistiques/tableau-de-bord").status_code == 403
    # 10. Impayés et retards
    assert admin.get("/api/v1/statistiques/impayes").json()["total"] == 0
    assert admin.get("/api/v1/commandes", params={"en_retard": True}).json()["total"] == 0
