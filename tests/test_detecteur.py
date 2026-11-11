"""Tests N0 de l'interface `Detector` et de la fabrique du détecteur."""

import re
from pathlib import Path

import numpy as np
import pytest

from passages import config as cfgmod
from passages.detecteur import Detector, creer_detecteur
from passages.detection import DetecteurYolox
from passages.run import RACINE


class FauxDetecteur:
    def detecter(self, bgr):
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32)


class SansDetecter:
    def predire(self, bgr):
        return None


def test_protocole_reconnu_par_la_forme():
    assert isinstance(FauxDetecteur(), Detector)
    assert not isinstance(SansDetecter(), Detector)


def test_run_ne_nomme_plus_yolox():
    source = (Path(__file__).resolve().parent.parent / "passages" / "run.py").read_text(encoding="utf-8")
    assert not re.search(r"yolox", source, re.IGNORECASE)
    assert not re.search(r"passages\.detection\b", source)
    assert "creer_detecteur" in source


@pytest.mark.skipif(not (RACINE / "models" / "yolox_s.onnx").exists(), reason="modèle hors git absent")
def test_fabrique_reprend_les_parametres_de_la_configuration():
    cfg, _ = cfgmod.charger(str(RACINE / "configs" / "s1_g420.yaml"))
    analyse = cfg["analyse"]
    d = creer_detecteur(analyse, str(RACINE / analyse["modele"]["chemin"]), None)
    assert isinstance(d, DetecteurYolox) and isinstance(d, Detector)
    assert d.taille == tuple(analyse["modele"]["taille_entree"])
    assert (d.seuil, d.seuil_nms) == (float(analyse["seuil_detection"]), float(analyse["seuil_nms"]))
