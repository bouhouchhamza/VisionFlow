"""Test N0 de bout en bout de `comparer` sur des fichiers : run et référence synthétiques, marqués comme tels."""

import json

from passages.evaluate import comparer


def ecrire(chemin, contenu):
    chemin.write_text(json.dumps(contenu), encoding="utf-8")


def test_comparer_ecrit_json_et_markdown(tmp_path):
    run = tmp_path / "20260101T000000Z-abcdef"
    run.mkdir()
    ecrire(run / "manifest.json", {
        "video": {"sha256": "AA"},
        "config": {"contenu": {"video": {"role_echantillon": "reglage"}, "analyse": {"cadence_analyse": 10}}},
    })
    ecrire(run / "evenements.json", {
        "run_id": run.name,
        "temps": {"fin_analyse_ms": 60000},
        "regle_passage": {"maintien_ms": 1000, "fenetre_doublon_ms": 1500},
        "franchissements": [
            {"id": "f0001", "ligne": "l", "piste": 1, "direction": "sortie", "t_ms": 10100},
            {"id": "f0002", "ligne": "l", "piste": 2, "direction": "sortie", "t_ms": 40000},
        ],
        "pistes": {"1": {"debut_ms": 0, "fin_ms": 15000}, "2": {"debut_ms": 35000, "fin_ms": 45000}},
    })
    reference = tmp_path / "ref.json"
    ecrire(reference, {
        "format": "annotation_passages", "version_format": 2, "nature": "verite_terrain_humaine",
        "detecteur_affiche": False, "synthetique": True, "annotateur": "test", "passe": 1,
        "video": {"sha256": "AA"},
        "plages_couvertes": [{"debut_ms": 0, "fin_ms": 60000, "debut_image": 0, "fin_image": 1800}],
        "franchissements": [{"id": "f0001", "ligne": "l", "direction": "sortie", "t_ms": 10000, "retour_de": None}],
        "demi_tours": [], "non_observables": [],
    })
    md = comparer(str(run), str(reference), None, 1000, afficher=lambda *_: None)
    texte = md.read_text(encoding="utf-8")
    assert "Référence synthétique" in texte
    resultat = json.loads(md.with_suffix(".json").read_text(encoding="utf-8"))["resultat"]
    assert (resultat["apparies"], resultat["manques"], resultat["ajouts"]) == (1, 0, 1)
