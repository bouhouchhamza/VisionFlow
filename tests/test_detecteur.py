"""Tests N0 du type `Detections`, de l'interface `Detector`, de l'adaptateur YOLOX et de la fabrique.

Les sorties de détecteur simulées et deux images sont synthétiques ; un test lit la première image de S1 (réglage).
"""

import dataclasses
import re
from pathlib import Path

import numpy as np
import pytest

from passages import config as cfgmod
from passages.detecteur import AdaptateurYolox, Detections, Detector, creer_detecteur
from passages.detection import DetecteurYolox
from passages.run import RACINE

MODELE = RACINE / "models" / "yolox_s.onnx"


def tableaux(n):
    boites = np.arange(n * 4, dtype=np.float32).reshape(n, 4)
    scores = np.linspace(0.9, 0.2, n, dtype=np.float32)
    return boites, scores


class FauxDetecteur:
    def detecter(self, bgr):
        return Detections.vide()


class SansDetecter:
    def predire(self, bgr):
        return None


class FauxYolox:
    """Rend des tableaux fixés, comme `DetecteurYolox.detecter`."""

    def __init__(self, boites, scores):
        self.sortie = (boites, scores)

    def detecter(self, bgr):
        return self.sortie


def test_protocole_reconnu_par_la_forme():
    assert isinstance(FauxDetecteur(), Detector)
    assert isinstance(AdaptateurYolox(FauxYolox(*tableaux(1))), Detector)
    assert not isinstance(SansDetecter(), Detector)


def test_vide():
    d = Detections.vide()
    assert len(d) == 0
    assert d.boites.shape == (0, 4) and d.boites.dtype == np.float32
    assert d.scores.shape == (0,) and d.scores.dtype == np.float32
    assert d.ids_modele.shape == (0,) and d.ids_modele.dtype == np.int64
    assert d.classes == ()


@pytest.mark.parametrize("n", [0, 1, 5])
def test_une_classe_reprend_les_tableaux_sans_copie(n):
    boites, scores = tableaux(n)
    d = Detections.une_classe(boites, scores, "person", 0)
    assert d.boites is boites and d.scores is scores
    assert len(d) == n and d.classes == ("person",) * n
    assert d.ids_modele.dtype == np.int64 and d.ids_modele.tolist() == [0] * n


def test_adaptateur_yolox_transmet_boites_et_scores_inchanges():
    boites, scores = tableaux(3)
    d = AdaptateurYolox(FauxYolox(boites, scores)).detecter(np.zeros((8, 8, 3), np.uint8))
    assert d.boites is boites and d.scores is scores
    assert d.classes == ("person",) * 3 and d.ids_modele.tolist() == [0, 0, 0]


def test_adaptateur_yolox_cas_vide():
    vide = (np.zeros((0, 4), np.float32), np.zeros((0,), np.float32))
    d = AdaptateurYolox(FauxYolox(*vide)).detecter(np.zeros((8, 8, 3), np.uint8))
    assert len(d) == 0 and d.classes == () and d.boites.shape == (0, 4)


@pytest.mark.parametrize("modifier, message", [
    (lambda b, s, c, i: (b[:, :3], s, c, i), "boites"),
    (lambda b, s, c, i: (b.astype(np.float64), s, c, i), "boites"),
    (lambda b, s, c, i: (b.tolist(), s, c, i), "boites"),
    (lambda b, s, c, i: (b[0], s, c, i), "boites"),
    (lambda b, s, c, i: (b, s.astype(np.float64), c, i), "scores"),
    (lambda b, s, c, i: (b, s.reshape(-1, 1), c, i), "scores"),
    (lambda b, s, c, i: (b, s[:-1], c, i), "longueurs"),
    (lambda b, s, c, i: (b, s, c[:-1], i), "longueurs"),
    (lambda b, s, c, i: (b, s, list(c), i), "classes"),
    (lambda b, s, c, i: (b, s, ("person", ""), i), "classes"),
    (lambda b, s, c, i: (b, s, c, i.astype(np.int32)), "ids_modele"),
    (lambda b, s, c, i: (b, s, c, i[:-1]), "longueurs"),
])
def test_invariants_refuses(modifier, message):
    b, s = tableaux(2)
    with pytest.raises(ValueError, match=message):
        Detections(*modifier(b, s, ("person", "person"), np.zeros(2, np.int64)))


def test_immuable():
    d = Detections.une_classe(*tableaux(1), "person", 0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.classes = ("car",)


def test_run_ne_nomme_plus_yolox():
    source = (Path(__file__).resolve().parent.parent / "passages" / "run.py").read_text(encoding="utf-8")
    assert not re.search(r"yolox", source, re.IGNORECASE)
    assert not re.search(r"passages\.detection\b", source)
    assert "creer_detecteur" in source


@pytest.mark.skipif(not MODELE.exists(), reason="modèle hors git absent")
def test_fabrique_reprend_les_parametres_de_la_configuration():
    cfg, _ = cfgmod.charger(str(RACINE / "configs" / "s1_g420.yaml"))
    analyse = cfg["analyse"]
    d = creer_detecteur(analyse, str(RACINE / analyse["modele"]["chemin"]), None)
    assert isinstance(d, AdaptateurYolox) and isinstance(d, Detector)
    assert isinstance(d.yolox, DetecteurYolox)
    assert d.yolox.taille == tuple(analyse["modele"]["taille_entree"])
    assert (d.yolox.seuil, d.yolox.seuil_nms) == (float(analyse["seuil_detection"]), float(analyse["seuil_nms"]))


def comparer_a_yolox(yolox, img):
    boites, scores = yolox.detecter(img)
    d = AdaptateurYolox(yolox).detecter(img)
    assert d.boites.dtype == boites.dtype == np.float32 and d.scores.dtype == scores.dtype == np.float32
    assert np.array_equal(d.boites, boites) and np.array_equal(d.scores, scores)
    assert d.classes == ("person",) * len(boites)
    return len(d)


@pytest.mark.skipif(not MODELE.exists(), reason="modèle hors git absent")
def test_adaptateur_identique_a_yolox_sur_images_synthetiques():
    yolox = DetecteurYolox(str(MODELE), (640, 640), 0.1, 0.45, 1)
    rng = np.random.default_rng(0)
    for img in (np.full((1072, 1920, 3), 114, np.uint8), rng.integers(0, 256, (1072, 1920, 3), dtype=np.uint8)):
        comparer_a_yolox(yolox, img)


def test_adaptateur_identique_a_yolox_sur_une_image_de_s1():
    from passages.video import lire

    cfg, _ = cfgmod.charger(str(RACINE / "configs" / "s1_g420.yaml"))
    video = RACINE / cfg["video"]["chemin"]
    if not (MODELE.exists() and video.exists()):
        pytest.skip("modèle ou vidéo S1 hors git absent")
    image = next(iter(lire(str(video), mode=cfg["video"]["mode_temps"])))
    yolox = DetecteurYolox(str(MODELE), (640, 640), 0.1, 0.45, 1)
    assert comparer_a_yolox(yolox, image.trame.to_ndarray(format="bgr24")) > 0
