"""Tests N0 du comparateur de runs, sur des runs synthétiques marqués comme tels (`synthetique: true`)."""

import copy
import hashlib
import json

import pytest

from passages.non_regression import (DIFFERENT, ECARTS_D_ARRONDI, IDENTIQUE, NON_COMPARABLE, comparer_et_ecrire,
                                     comparer_runs)


def run_synthetique() -> dict:
    franchissements = [
        {"id": "f0001", "ligne": "l", "piste": 1, "sens_geometrique": "droite_vers_gauche", "direction": "sortie",
         "t_ms": 1000, "num_image": 30, "t_ms_avant": 900, "num_image_avant": 27, "u": 0.5, "point": [10.0, 20.0],
         "confiance": 0.9},
        {"id": "f0002", "ligne": "l", "piste": 2, "sens_geometrique": "gauche_vers_droite", "direction": "entree",
         "t_ms": 65000, "num_image": 1950, "t_ms_avant": 64900, "num_image_avant": 1947, "u": 0.25,
         "point": [30.0, 40.0], "confiance": 0.8},
    ]
    passages = [
        {"franchissement": "f0001", "ligne": "l", "piste": 1, "direction": "sortie", "t_ms": 1000, "statut": "passage"},
        {"franchissement": "f0002", "ligne": "l", "piste": 2, "direction": "entree", "t_ms": 65000, "statut": "passage"},
    ]
    pistes = [
        {"num_image": 0, "t_ms": 0, "pts": 1, "temps_reconstruit": True, "detections_brutes": 2,
         "objets": [{"piste": 1, "boite": [1.0, 2.0, 3.0, 4.0], "score": 0.9}]},
        {"num_image": 30, "t_ms": 1000, "pts": 31, "temps_reconstruit": True, "detections_brutes": 1,
         "objets": [{"piste": 1, "boite": [1.5, 2.0, 3.5, 4.0], "score": 0.88}]},
        {"num_image": 1950, "t_ms": 65000, "pts": 1951, "temps_reconstruit": True, "detections_brutes": 1,
         "objets": [{"piste": 2, "boite": [5.0, 6.0, 7.0, 8.0], "score": 0.8}]},
    ]
    manifeste = {
        "synthetique": True,
        "run_id": "20260101T000000Z-aaaaaa", "cree_le_utc": "2026-01-01T00:00:00+00:00", "commande": ["python"],
        "config": {"chemin": "c.yaml", "sha256_canonique": "CFG", "sha256_fichier": "F"},
        "video": {"sha256": "VID", "bilan_temps": {"mode": "rang_cadence_nominale", "images": 2000}},
        "modele": {"sha256": "MOD"},
        "versions": {"python": "3.11.9", "paquets": {"onnxruntime": "1.31.1"}, "processeur": "cpu",
                     "coeurs_logiques": 12, "plateforme": "Windows", "git_commit": "abc", "git_dirty": False},
        "execution": {"threads_onnxruntime": "defaut", "limite_s": None, "images_decodees": 2000,
                      "images_analysees": 3, "duree_calcul_s": 10.0, "chronometrage_s": {"detection_s": 9.0},
                      "vitesse_s_video_par_s_calcul": 0.5},
    }
    evenements = {
        "format": "evenements_passages", "version_format": 1, "run_id": manifeste["run_id"],
        "nature": "observations_brutes_machine", "temps": {"mode": "rang_cadence_nominale", "fin_analyse_ms": 66000},
        "regle_passage": {"maintien_ms": 1000, "fenetre_doublon_ms": 1500},
        "franchissements": franchissements, "passages_derives": passages, "doublons_probables": [],
        "pistes": {"1": {"debut_ms": 0, "fin_ms": 1000}, "2": {"debut_ms": 65000, "fin_ms": 65000}},
    }
    return {"manifeste": manifeste, "evenements": evenements, "pistes": pistes}


def ecrire(dossier, run):
    dossier.mkdir(parents=True)
    (dossier / "manifest.json").write_text(json.dumps(run["manifeste"]), encoding="utf-8")
    (dossier / "evenements.json").write_text(json.dumps(run["evenements"]), encoding="utf-8")
    (dossier / "pistes.jsonl").write_text("".join(json.dumps(l) + "\n" for l in run["pistes"]), encoding="utf-8")
    return dossier


def comparer(tmp_path, modifier, jusqu_a_ms=None):
    ref = run_synthetique()
    cand = copy.deepcopy(ref)
    modifier(cand)
    return comparer_runs(ecrire(tmp_path / "ref", ref), ecrire(tmp_path / "cand", cand), jusqu_a_ms)


def rien(_):
    pass


def test_copie_exacte_identique(tmp_path):
    res = comparer(tmp_path, rien)
    assert res["verdict"] == IDENTIQUE
    assert res["metadonnees_differentes"] == []


def test_metadonnees_seules_differentes_restent_identique(tmp_path):
    def m(r):
        r["manifeste"].update(run_id="20260202T000000Z-bbbbbb", cree_le_utc="2026-02-02", commande=["autre"])
        r["manifeste"]["execution"].update(duree_calcul_s=99.0, vitesse_s_video_par_s_calcul=0.1)
        r["manifeste"]["versions"].update(git_commit="def", git_dirty=True, plateforme="Windows-11")
        del r["manifeste"]["config"]["sha256_fichier"]
        r["evenements"]["run_id"] = "20260202T000000Z-bbbbbb"
    res = comparer(tmp_path, m)
    assert res["verdict"] == IDENTIQUE
    assert {"run_id", "cree_le_utc", "git_commit", "git_dirty", "duree_calcul_s"} <= set(res["metadonnees_differentes"])


def test_ancien_manifeste_sans_git_dirty(tmp_path):
    def m(r):
        v = r["manifeste"]["versions"]
        del v["git_dirty"]
        v.update(git_commit=None, git_modifications_locales=True)
    res = comparer(tmp_path, m)
    assert res["verdict"] == IDENTIQUE
    assert res["candidat"]["git_dirty"] is True


def test_un_pas_d_arrondi_classe_a_part(tmp_path):
    res = comparer(tmp_path, lambda r: r["pistes"][1]["objets"][0]["boite"].__setitem__(0, 1.6))
    assert res["verdict"] == ECARTS_D_ARRONDI
    assert res["pistes"]["premier_ecart_arrondi"]["champ"] == "boite[0]"


def test_ecart_de_boite_au_dela_d_un_pas_est_une_divergence(tmp_path):
    res = comparer(tmp_path, lambda r: r["pistes"][1]["objets"][0]["boite"].__setitem__(0, 1.8))
    assert res["verdict"] == DIFFERENT
    assert res["pistes"]["premiere_divergence"]["num_image"] == 30


def test_direction_inversee(tmp_path):
    def m(r):
        r["evenements"]["franchissements"][0]["direction"] = "entree"
    res = comparer(tmp_path, m)
    assert res["verdict"] == DIFFERENT
    assert res["franchissements"]["premiere_divergence"]["champ"] == "direction"
    assert res["franchissements"]["premiere_divergence"]["franchissement"] == "f0001"
    assert "franchissements_par_ligne_et_direction" in res["statistiques_differentes"]


def test_temps_decale(tmp_path):
    def m(r):
        r["evenements"]["franchissements"][1]["t_ms"] = 65100
    res = comparer(tmp_path, m)
    assert res["verdict"] == DIFFERENT
    d = res["franchissements"]["premiere_divergence"]
    assert (d["champ"], d["attendu"], d["obtenu"]) == ("t_ms", 65000, 65100)


def test_evenement_manquant_et_supplementaire(tmp_path):
    def manque(r):
        del r["evenements"]["franchissements"][1]
    res = comparer(tmp_path, manque)
    assert res["verdict"] == DIFFERENT
    assert [f["t_ms"] for f in res["franchissements"]["manquants"]] == [65000]
    assert res["franchissements"]["supplementaires"] == []

    def ajout(r):
        f = dict(r["evenements"]["franchissements"][1], id="f0003", piste=3, t_ms=70000, num_image=2100)
        r["evenements"]["franchissements"].append(f)
    res = comparer(tmp_path / "b", ajout)
    assert res["verdict"] == DIFFERENT
    assert [f["piste"] for f in res["franchissements"]["supplementaires"]] == [3]


def test_identifiant_de_piste_change(tmp_path):
    def m(r):
        r["pistes"][2]["objets"][0]["piste"] = 7
    res = comparer(tmp_path, m)
    assert res["verdict"] == DIFFERENT
    assert res["pistes"]["premiere_divergence"]["champ"] == "pistes_de_l_image"


def test_statut_de_passage_et_statistiques(tmp_path):
    def m(r):
        r["evenements"]["passages_derives"][1]["statut"] = "annule_par_retour"
    res = comparer(tmp_path, m)
    assert res["verdict"] == DIFFERENT
    assert "passages_derives" in res["blocs_evenements_differents"]
    assert {"passages_par_statut_et_direction", "passages_retenus_par_minute"} <= set(res["statistiques_differentes"])


def test_version_de_paquet_differente_non_comparable(tmp_path):
    res = comparer(tmp_path, lambda r: r["manifeste"]["versions"]["paquets"].update(onnxruntime="1.32.0"))
    assert res["verdict"] == NON_COMPARABLE
    assert "versions.paquets" in res["prealables_differents"]


def test_non_comparable_l_emporte_sur_identique(tmp_path):
    res = comparer(tmp_path, lambda r: r["manifeste"]["execution"].update(threads_onnxruntime=1))
    assert res["verdict"] == NON_COMPARABLE
    assert res["pistes"]["ecarts_stricts"] == res["franchissements"]["ecarts_stricts"] == 0


def run_limite(r):
    """Candidat arrêté à 20 s : une image et un franchissement de moins, passages et pistes recalculés."""
    r["manifeste"]["execution"].update(limite_s=20.0, images_decodees=600, images_analysees=2)
    r["manifeste"]["video"]["bilan_temps"]["images"] = 600
    r["pistes"].pop()
    ev = r["evenements"]
    ev["franchissements"].pop()
    ev["passages_derives"] = ev["passages_derives"][:1]
    ev["pistes"] = {"1": {"debut_ms": 0, "fin_ms": 1000}}
    ev["temps"]["fin_analyse_ms"] = 20000


def test_run_limite_non_comparable_en_mode_complet(tmp_path):
    res = comparer(tmp_path, run_limite)
    assert res["verdict"] == NON_COMPARABLE
    assert "execution.limite_s" in res["prealables_differents"]


def test_run_limite_identique_en_mode_tronque(tmp_path):
    assert comparer(tmp_path, run_limite, jusqu_a_ms=20000)["verdict"] == IDENTIQUE


def test_mode_tronque_trop_large_voit_la_difference(tmp_path):
    res = comparer(tmp_path, run_limite, jusqu_a_ms=300000)
    assert res["verdict"] == DIFFERENT
    assert res["franchissements"]["manquants"][0]["t_ms"] == 65000


def test_mode_tronque_detecte_une_divergence_avant_la_borne(tmp_path):
    def m(r):
        run_limite(r)
        r["evenements"]["franchissements"][0]["piste"] = 9
    assert comparer(tmp_path, m, jusqu_a_ms=20000)["verdict"] == DIFFERENT


def empreintes(dossier):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dossier.iterdir())}


def test_ecriture_hors_des_runs_compares(tmp_path):
    ref = ecrire(tmp_path / "ref", run_synthetique())
    cand = ecrire(tmp_path / "cand", run_synthetique())
    avant = empreintes(ref), empreintes(cand)
    res = comparer_et_ecrire(str(ref), str(cand), sortie=str(tmp_path / "rapports"), afficher=lambda *_: None)
    assert res["verdict"] == IDENTIQUE
    assert (empreintes(ref), empreintes(cand)) == avant
    assert len(list((tmp_path / "rapports").iterdir())) == 2
    with pytest.raises(ValueError):
        comparer_et_ecrire(str(ref), str(cand), sortie=str(ref / "non_regression"), afficher=lambda *_: None)
    with pytest.raises(ValueError):
        comparer_et_ecrire(str(ref), str(cand), sortie=str(cand), afficher=lambda *_: None)
    assert not (ref / "non_regression").exists()
