"""Tests des commandes : RG5 à RG15 (montants, dates, lignes, workflow des statuts)."""
import re
from datetime import date, timedelta

from tests.conftest import avancer, id_prestation


def test_rg5_rg7_rg8_creation(commande):
    assert re.fullmatch(r"CMD-\d{4}-\d{5}", commande["numero"])
    # 2 x 35 000 + 1 x 10 000 - 5 000
    assert commande["montant_total"] == 75000 and commande["montant_paye"] == 0 and commande["solde"] == 75000
    # RG8 : + le plus long délai (boubou : 10 jours)
    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert commande["statut"] == "en_attente"
    assert commande["lignes"][0]["prix_unitaire"] == 35000  # RG6 : prix du catalogue par défaut


def test_rg9_rattachement_automatique_aux_dernieres_mesures(accueil, tailleur, fatou):
    m = tailleur.post(f"/api/v1/clients/{fatou['id']}/mesures", json={"tour_taille": 70}).json()
    r = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "lignes": [{"type_vetement_id": id_prestation(accueil, "Robe")}]})
    assert r.json()["mesure_id"] == m["id"]


def test_rg9_mesure_d_un_autre_client_422(accueil, tailleur, fatou):
    autre = accueil.post("/api/v1/clients", json={"nom": "Ba", "prenom": "Moussa", "telephone": "780000000"}).json()
    m = tailleur.post(f"/api/v1/clients/{autre['id']}/mesures", json={"tour_taille": 90}).json()
    r = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "mesure_id": m["id"],
                                                "lignes": [{"type_vetement_id": id_prestation(accueil, "Robe")}]})
    assert r.status_code == 422


def test_rg7_remise_trop_grande_422(accueil, fatou):
    r = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "remise": 999999,
                                                "lignes": [{"type_vetement_id": id_prestation(accueil, "Robe")}]})
    assert r.status_code == 422


def test_rg8_date_prevue_dans_le_passe_422(accueil, fatou):
    hier = (date.today() - timedelta(days=1)).isoformat()
    r = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "date_livraison_prevue": hier,
                                                "lignes": [{"type_vetement_id": id_prestation(accueil, "Robe")}]})
    assert r.status_code == 422


def test_rg6_prestation_inactive_422(admin, accueil, fatou):
    robe = id_prestation(accueil, "Robe")
    admin.patch(f"/api/v1/catalogue/{robe}", json={"actif": False})
    r = accueil.post("/api/v1/commandes", json={"client_id": fatou["id"], "lignes": [{"type_vetement_id": robe}]})
    assert r.status_code == 422
    assert all(p["nom"] != "Robe" for p in accueil.get("/api/v1/catalogue").json())


def test_rg10_lignes(accueil, tailleur, commande):
    cid = commande["id"]
    r = accueil.post(f"/api/v1/commandes/{cid}/lignes", json={"type_vetement_id": id_prestation(accueil, "Retouche")})
    assert r.status_code == 201 and r.json()["montant_total"] == 78000
    l1, l2, l3 = (l["id"] for l in r.json()["lignes"])
    accueil.delete(f"/api/v1/commandes/{cid}/lignes/{l3}")
    accueil.delete(f"/api/v1/commandes/{cid}/lignes/{l2}")
    assert accueil.delete(f"/api/v1/commandes/{cid}/lignes/{l1}").status_code == 409  # dernière ligne
    assert accueil.delete(f"/api/v1/commandes/{cid}/lignes/99999").status_code == 404
    avancer(tailleur, cid, "en_coupe")
    r = accueil.post(f"/api/v1/commandes/{cid}/lignes", json={"type_vetement_id": id_prestation(accueil, "Retouche")})
    assert r.status_code == 409  # plus en_attente


def test_workflow_transition_interdite_message_avec_statuts_possibles(accueil, commande):
    r = accueil.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "terminee"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe."


def test_rg13_meme_statut_et_livree_interdits(accueil, commande):
    url = f"/api/v1/commandes/{commande['id']}/statut"
    assert accueil.post(url, json={"statut": "en_attente"}).status_code == 409
    assert accueil.post(url, json={"statut": "livree"}).status_code == 409


def test_rg15_historique_avec_aller_retour_essayage_retouches(tailleur, commande):
    avancer(tailleur, commande["id"], "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee")
    h = tailleur.get(f"/api/v1/commandes/{commande['id']}/historique").json()
    assert h[0]["ancien_statut"] is None and h[0]["nouveau_statut"] == "en_attente"
    assert [x["nouveau_statut"] for x in h[1:]] == ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]


def test_rg14_tailleur_ne_peut_pas_annuler(tailleur, commande):
    r = tailleur.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "annulee"})
    assert r.status_code == 403


def test_rg14_annulation_avec_acompte_exige_un_commentaire(accueil, commande):
    accueil.post(f"/api/v1/commandes/{commande['id']}/paiements", json={"montant": 10000, "mode": "wave"})
    url = f"/api/v1/commandes/{commande['id']}/statut"
    assert accueil.post(url, json={"statut": "annulee"}).status_code == 422
    r = accueil.post(url, json={"statut": "annulee", "commentaire": "Acompte remboursé en espèces"})
    assert r.status_code == 200 and r.json()["statut"] == "annulee"


def test_rg12_commande_annulee_plus_modifiable(accueil, commande):
    accueil.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "annulee"})
    assert accueil.patch(f"/api/v1/commandes/{commande['id']}", json={"notes": "x"}).status_code == 409
    r = accueil.post(f"/api/v1/commandes/{commande['id']}/statut", json={"statut": "en_coupe"})
    assert r.status_code == 409 and "aucun" in r.json()["detail"]


def test_patch_commande_recalcule(accueil, commande):
    r = accueil.patch(f"/api/v1/commandes/{commande['id']}", json={"remise": 0})
    assert r.status_code == 200 and r.json()["montant_total"] == 80000


def test_rg7_total_jamais_sous_le_paye(accueil, commande):
    accueil.post(f"/api/v1/commandes/{commande['id']}/paiements", json={"montant": 75000, "mode": "especes"})
    assert accueil.patch(f"/api/v1/commandes/{commande['id']}", json={"remise": 6000}).status_code == 409


def test_rg11_liste_filtre_en_retard(accueil, commande):
    r = accueil.get("/api/v1/commandes", params={"en_retard": True}).json()
    assert r["total"] == 0
    r = accueil.get("/api/v1/commandes").json()
    assert r["items"][0]["client_nom"] == "Fatou Diop" and r["items"][0]["en_retard"] is False
