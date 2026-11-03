"""Test N0 de la logique de saisie de l'outil d'annotation (sans fenêtre)."""

import json

from passages.annotate import Annotation


def test_saisies_retour_demi_tour_non_observable_et_couverture(tmp_path):
    chemin = tmp_path / "a.json"
    note = Annotation(chemin, {"format": "annotation_passages"}, None)
    for i in range(0, 101):
        note.voir(i - 1 if i else None, i)
    note.voir(100, 150)
    for i in range(151, 201):
        note.voir(i - 1, i)
    note.franchir("portes", "sortie", 30, 1000)
    note.franchir("portes", "entree", 45, 1500)
    assert "retour de f0001" in note.lier_retour()
    note.demi_tour("portes", 60, 2000)
    note.basculer_non_observable(70, 2333)
    note.basculer_non_observable(80, 2667)
    note.franchir("portes", "sortie", 90, 3000)
    assert note.annuler() == "annule : f0005"
    note.sauver(lambda i: round(i * 1000 / 30))
    doc = json.loads(chemin.read_text(encoding="utf-8"))
    assert [f["id"] for f in doc["franchissements"]] == ["f0001", "f0002"]
    assert doc["franchissements"][1]["retour_de"] == "f0001"
    assert doc["demi_tours"][0]["id"] == "d0003"
    assert doc["non_observables"][0]["debut_image"] == 70 and doc["non_observables"][0]["fin_image"] == 80
    assert [(p["debut_image"], p["fin_image"]) for p in doc["plages_couvertes"]] == [(0, 100), (150, 200)]
