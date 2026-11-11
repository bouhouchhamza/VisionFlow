"""Interface commune des détecteurs, type d'échange `Detections` et construction du détecteur d'un run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from passages.detection import COCO_CLASSES, DetecteurYolox


@dataclass(frozen=True)
class Detections:
    """Détections d'une image, indépendantes du modèle.

    `boites` : float32 (N, 4), xyxy en pixels de l'image ; `scores` : float32 (N,) ; `classes` : N noms de classe du
    domaine ; `ids_modele` : int64 (N,), indice de classe propre au modèle, pour la traçabilité seulement.
    L'ordre des détections est celui du détecteur et doit être déterministe.
    """

    boites: np.ndarray
    scores: np.ndarray
    classes: tuple[str, ...]
    ids_modele: np.ndarray

    def __post_init__(self):
        if not isinstance(self.boites, np.ndarray) or self.boites.dtype != np.float32 or self.boites.ndim != 2 \
                or self.boites.shape[1] != 4:
            raise ValueError("boites : tableau float32 de forme (N, 4) attendu")
        if not isinstance(self.scores, np.ndarray) or self.scores.dtype != np.float32 or self.scores.ndim != 1:
            raise ValueError("scores : tableau float32 de forme (N,) attendu")
        if not isinstance(self.ids_modele, np.ndarray) or self.ids_modele.dtype != np.int64 or self.ids_modele.ndim != 1:
            raise ValueError("ids_modele : tableau int64 de forme (N,) attendu")
        if not isinstance(self.classes, tuple) or not all(isinstance(c, str) and c for c in self.classes):
            raise ValueError("classes : tuple de noms non vides attendu")
        n = len(self.boites)
        if not (len(self.scores) == len(self.classes) == len(self.ids_modele) == n):
            raise ValueError(f"longueurs incohérentes : {n} boîtes, {len(self.scores)} scores, "
                             f"{len(self.classes)} classes, {len(self.ids_modele)} ids")

    def __len__(self) -> int:
        return len(self.boites)

    @classmethod
    def une_classe(cls, boites: np.ndarray, scores: np.ndarray, classe: str, id_modele: int) -> Detections:
        """Toutes les détections d'une même classe ; les tableaux sont repris tels quels, sans copie."""
        n = len(boites)
        return cls(boites, scores, (classe,) * n, np.full(n, id_modele, dtype=np.int64))

    @classmethod
    def vide(cls) -> Detections:
        return cls(np.zeros((0, 4), np.float32), np.zeros((0,), np.float32), (), np.zeros((0,), np.int64))


@runtime_checkable
class Detector(Protocol):
    def detecter(self, bgr: np.ndarray) -> Detections:
        """Image BGR uint8 (H, W, 3) en pleine résolution de la vidéo.

        Boîtes bornées à [0, W-1] × [0, H-1], scores dans [0, 1] déjà filtrés par le seuil, ordre déterministe : le
        suivi reçoit les détections dans cet ordre.
        """
        ...


class AdaptateurYolox:
    """YOLOX vu par le domaine : chaque indice de classe du modèle est rendu sous son nom COCO.

    Les classes décodées sont celles du `DetecteurYolox` (par défaut la seule classe 0, `person`).
    """

    def __init__(self, yolox: DetecteurYolox):
        self.yolox = yolox

    def detecter(self, bgr: np.ndarray) -> Detections:
        boites, scores, ids = self.yolox.detecter(bgr)
        return Detections(boites, scores, tuple(COCO_CLASSES[i] for i in ids.tolist()), ids)


def creer_detecteur(analyse: dict, chemin_modele: str, threads: int | None = None) -> Detector:
    # Aucune classe transmise : seule `person` est décodée tant que le suivi associe sans regarder la classe.
    return AdaptateurYolox(DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]),
                                          float(analyse["seuil_detection"]), float(analyse["seuil_nms"]), threads))
