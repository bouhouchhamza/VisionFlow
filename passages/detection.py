"""Détection de personnes avec YOLOX (export ONNX officiel 0.1.1rc0) sur ONNX Runtime CPU.

Pré- et post-traitement repris de YOLOX `yolox/data/data_augment.py::preproc` et `yolox/utils/demo_utils.py`
(Apache-2.0, Megvii). Depuis 0.1.1, l'entrée est en BGR 0-255 sans normalisation moyenne/écart-type.
"""

from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

CLASSE_PERSONNE = 0


class DetecteurYolox:
    def __init__(self, chemin: str, taille_entree: tuple[int, int] = (640, 640), seuil: float = 0.1,
                 seuil_nms: float = 0.45, threads: int | None = None):
        options = ort.SessionOptions()
        # Sans cela, les threads d'inférence en attente active privent le décodage et la conversion de CPU.
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        if threads:
            options.intra_op_num_threads = threads
        self.session = ort.InferenceSession(chemin, options, providers=["CPUExecutionProvider"])
        self.entree = self.session.get_inputs()[0].name
        self.taille = tuple(taille_entree)
        self.seuil = seuil
        self.seuil_nms = seuil_nms
        grilles, pas = [], []
        for stride in (8, 16, 32):
            h, w = self.taille[0] // stride, self.taille[1] // stride
            xv, yv = np.meshgrid(np.arange(w), np.arange(h))
            grilles.append(np.stack((xv, yv), 2).reshape(-1, 2))
            pas.append(np.full((h * w, 1), stride))
        self.grilles = np.concatenate(grilles).astype(np.float32)
        self.pas = np.concatenate(pas).astype(np.float32)

    def pretraiter(self, bgr: np.ndarray) -> tuple[np.ndarray, float]:
        h, w = bgr.shape[:2]
        r = min(self.taille[0] / h, self.taille[1] / w)
        redim = cv2.resize(bgr, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR)
        tampon = np.full((self.taille[0], self.taille[1], 3), 114, dtype=np.uint8)
        tampon[: redim.shape[0], : redim.shape[1]] = redim
        return np.ascontiguousarray(tampon.transpose(2, 0, 1)[None], dtype=np.float32), r

    def decoder(self, sortie: np.ndarray, ratio: float) -> tuple[np.ndarray, np.ndarray]:
        pred = sortie.copy()
        pred[:, :2] = (pred[:, :2] + self.grilles) * self.pas
        pred[:, 2:4] = np.exp(pred[:, 2:4]) * self.pas
        scores = pred[:, 4] * pred[:, 5 + CLASSE_PERSONNE]
        garde = scores > self.seuil
        pred, scores = pred[garde], scores[garde]
        if not len(scores):
            return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32)
        boites = np.empty((len(pred), 4), np.float32)
        boites[:, 0] = pred[:, 0] - pred[:, 2] / 2
        boites[:, 1] = pred[:, 1] - pred[:, 3] / 2
        boites[:, 2] = pred[:, 0] + pred[:, 2] / 2
        boites[:, 3] = pred[:, 1] + pred[:, 3] / 2
        boites /= ratio
        retenus = nms(boites, scores, self.seuil_nms)
        return boites[retenus], scores[retenus]

    def detecter(self, bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        entree, ratio = self.pretraiter(bgr)
        sortie = self.session.run(None, {self.entree: entree})[0][0]
        boites, scores = self.decoder(sortie, ratio)
        h, w = bgr.shape[:2]
        boites[:, [0, 2]] = np.clip(boites[:, [0, 2]], 0, w - 1)
        boites[:, [1, 3]] = np.clip(boites[:, [1, 3]], 0, h - 1)
        return boites, scores


def nms(boites: np.ndarray, scores: np.ndarray, seuil: float) -> np.ndarray:
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
