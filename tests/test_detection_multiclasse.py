"""Tests N0 du décodage de YOLOX (étape 2 de `docs/CONCEPTION_MULTICLASSE.md`).

Les sorties de modèle sont **synthétiques** (tableaux (8400, 85) fabriqués, session ONNX Runtime simulée), sauf mention
contraire. L'oracle est une copie figée du décodage `person` de `passages/detection.py` au commit `878f08f` : il sert de
référence d'équivalence au bit près et ne doit pas être modifié.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from passages import detection
from passages.detection import DetecteurYolox

TAILLE = (640, 640)
SEUIL, SEUIL_NMS = 0.1, 0.45
RATIO_S1 = min(640 / 1072, 640 / 1920)
GRAINES = range(20)


# Oracle figé : `decoder` et `nms` de passages/detection.py au commit 878f08f. Ne pas modifier.

def _grilles_reference(taille):
    grilles, pas = [], []
    for stride in (8, 16, 32):
        h, w = taille[0] // stride, taille[1] // stride
        xv, yv = np.meshgrid(np.arange(w), np.arange(h))
        grilles.append(np.stack((xv, yv), 2).reshape(-1, 2))
        pas.append(np.full((h * w, 1), stride))
    return np.concatenate(grilles).astype(np.float32), np.concatenate(pas).astype(np.float32)


GRILLES, PAS = _grilles_reference(TAILLE)


def nms_reference(boites, scores, seuil):
    x1, y1, x2, y2 = boites.T
    aires = (x2 - x1 + 1) * (y2 - y1 + 1)
    ordre = scores.argsort()[::-1]
    garde = []
    while ordre.size:
        i = ordre[0]
        garde.append(i)
        xx1 = np.maximum(x1[i], x1[ordre[1:]])
        yy1 = np.maximum(y1[i], y1[ordre[1:]])
        xx2 = np.minimum(x2[i], x2[ordre[1:]])
        yy2 = np.minimum(y2[i], y2[ordre[1:]])
        inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
        iou = inter / (aires[i] + aires[ordre[1:]] - inter)
        ordre = ordre[np.where(iou <= seuil)[0] + 1]
    return np.array(garde, dtype=np.int64)


def decoder_reference(sortie, ratio, seuil=SEUIL, seuil_nms=SEUIL_NMS):
    pred = sortie.copy()
    pred[:, :2] = (pred[:, :2] + GRILLES) * PAS
    pred[:, 2:4] = np.exp(pred[:, 2:4]) * PAS
    scores = pred[:, 4] * pred[:, 5 + 0]
    garde = scores > seuil
    pred, scores = pred[garde], scores[garde]
    if not len(scores):
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32)
    boites = np.empty((len(pred), 4), np.float32)
    boites[:, 0] = pred[:, 0] - pred[:, 2] / 2
    boites[:, 1] = pred[:, 1] - pred[:, 3] / 2
    boites[:, 2] = pred[:, 0] + pred[:, 2] / 2
    boites[:, 3] = pred[:, 1] + pred[:, 3] / 2
    boites /= ratio
    retenus = nms_reference(boites, scores, seuil_nms)
    return boites[retenus], scores[retenus]


# Outils de test

class FausseSession:
    """Session ONNX Runtime simulée : formes d'entrée et de sortie déclarées, sortie fixée (synthétique)."""

    def __init__(self, colonnes=85, sortie=None):
        self.colonnes, self.sortie = colonnes, sortie

    def get_inputs(self):
        return [SimpleNamespace(name="images", shape=[1, 3, *TAILLE])]

    def get_outputs(self):
        return [SimpleNamespace(name="output", shape=[1, 8400, self.colonnes])]

    def run(self, noms, flux):
        return [self.sortie[None]]


@pytest.fixture
def session(monkeypatch):
    fausse = FausseSession()
    monkeypatch.setattr(detection.ort, "InferenceSession", lambda *a, **k: fausse)
    return fausse


def yolox(**options):
    return DetecteurYolox("modele_simule.onnx", TAILLE, SEUIL, SEUIL_NMS, None, **options)


def sortie_aleatoire(graine):
    """Sortie synthétique : boîtes plausibles, scores répartis autour du seuil ; ex aequo nombreux si graine impaire."""
    rng = np.random.default_rng(graine)
    s = np.empty((8400, 85), np.float32)
    s[:, :2] = rng.uniform(-0.5, 1.5, (8400, 2))
    s[:, 2:4] = rng.uniform(0.0, 3.0, (8400, 2))
    s[:, 4] = rng.uniform(0.0, 1.0, 8400)
    s[:, 5:] = rng.uniform(0.0, 0.3, (8400, 80))
    if graine % 2:
        s[:, 4:] = np.round(s[:, 4:] * 16) / 16
    return s


def identiques(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


@pytest.mark.parametrize("graine", GRAINES)
def test_oracle_egal_decodeur(session, graine):
    """T1 : l'oracle reproduit `decoder` au bit près, ordre compris (écrit et vérifié sur le code non modifié)."""
    sortie = sortie_aleatoire(graine)
    attendu = decoder_reference(sortie, RATIO_S1)
    obtenu = yolox().decoder(sortie, RATIO_S1)[:2]
    assert len(attendu[0]) > 0
    for a, o in zip(attendu, obtenu):
        assert identiques(a, o)
