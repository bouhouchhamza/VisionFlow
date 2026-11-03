"""Tests N0 (données synthétiques) de la géométrie, des franchissements et de la règle de maintien."""

from passages.crossing import (
    ANNULE_RETOUR, DROITE, GAUCHE, NON_CONFIRME_FIN, PASSAGE, DetecteurFranchissements, Ligne, appliquer_maintien,
    deriver_passages_machine, doublons_probables,
)
from passages.video import Echantillonneur

SENS = {"gauche_vers_droite": "entree", "droite_vers_gauche": "sortie"}


def ligne_horizontale(**kw):
    return Ligne(id="l", p1=(0.0, 100.0), p2=(200.0, 100.0), sens=SENS, **kw)


def test_cote_gauche_en_haut_pour_une_ligne_tracee_vers_la_droite():
    l = ligne_horizontale()
    assert l.cote(50, 40) == GAUCHE
    assert l.cote(50, 160) == DROITE


def test_marge_morte():
    l = ligne_horizontale(marge_px=5)
    assert l.cote(50, 103) == 0
    assert l.cote(50, 106) == DROITE


def test_franchissement_et_instant_premiere_image_du_nouveau_cote():
    d = DetecteurFranchissements([ligne_horizontale()])
    d.observer(1, 0, 0, 100, 80, 0.9)
    d.observer(1, 100, 3, 100, 95, 0.9)
    emis = d.observer(1, 200, 6, 100, 110, 0.9)
    assert len(emis) == 1
    f = emis[0]
    assert (f.direction, f.t_ms, f.num_image, f.t_ms_avant) == ("entree", 200, 6, 100)


def test_pas_de_franchissement_hors_segment():
    d = DetecteurFranchissements([ligne_horizontale(extension=0.05)])
    d.observer(1, 0, 0, 260, 80, 0.9)
    assert d.observer(1, 100, 3, 260, 120, 0.9) == []


def test_marge_morte_ne_cree_pas_de_franchissement():
    d = DetecteurFranchissements([ligne_horizontale(marge_px=5)])
    d.observer(1, 0, 0, 100, 90, 0.9)
    d.observer(1, 100, 3, 100, 101, 0.9)
    assert d.observer(1, 200, 6, 100, 98, 0.9) == []


def test_pistes_independantes():
    d = DetecteurFranchissements([ligne_horizontale()])
    d.observer(1, 0, 0, 50, 80, 0.9)
    assert d.observer(2, 100, 3, 50, 120, 0.9) == []


def chaine(*instants):
    return [{"t_ms": t} for t in instants]


def test_maintien_annule_un_aller_retour_rapide():
    assert appliquer_maintien(chaine(0, 400), 1000, None, False) == [ANNULE_RETOUR, ANNULE_RETOUR]


def test_maintien_nul_garde_tout():
    assert appliquer_maintien(chaine(0, 400), 0, None, False) == [PASSAGE, PASSAGE]


def test_maintien_hesitation_puis_passage():
    assert appliquer_maintien(chaine(0, 300, 600), 1000, None, False) == [ANNULE_RETOUR, ANNULE_RETOUR, PASSAGE]


def test_maintien_retour_lent_compte_deux_passages():
    assert appliquer_maintien(chaine(0, 5000), 1000, None, False) == [PASSAGE, PASSAGE]


def test_fin_de_video_non_confirme():
    assert appliquer_maintien(chaine(9500), 1000, 9900, True) == [NON_CONFIRME_FIN]
    assert appliquer_maintien(chaine(9500), 1000, 9900, False) == [PASSAGE]


def test_derivation_machine_et_doublons():
    fr = [
        {"id": "f1", "ligne": "l", "piste": 1, "direction": "entree", "t_ms": 1000},
        {"id": "f2", "ligne": "l", "piste": 2, "direction": "entree", "t_ms": 1300},
        {"id": "f3", "ligne": "l", "piste": 3, "direction": "entree", "t_ms": 5000},
        {"id": "f4", "ligne": "l", "piste": 3, "direction": "sortie", "t_ms": 5400},
    ]
    p = deriver_passages_machine(fr, {1: 4000, 2: 4000, 3: 8000}, 20000, 100, 1000)
    statuts = {x["franchissement"]: x["statut"] for x in p}
    assert statuts == {"f1": PASSAGE, "f2": PASSAGE, "f3": ANNULE_RETOUR, "f4": ANNULE_RETOUR}
    assert doublons_probables(p, 1500) == [("f1", "f2")]


def test_echantillonnage_sur_temps_video_irregulier():
    e = Echantillonneur(10)
    instants = [0.0, 0.033, 0.066, 0.1, 0.133, 0.25, 0.40, 0.433, 0.5]
    gardes = [t for t in instants if e.garder(t)]
    assert gardes == [0.0, 0.1, 0.25, 0.40, 0.5]
