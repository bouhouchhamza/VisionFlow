"""Interface commune des détecteurs et construction du détecteur d'un run."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from passages.detection import DetecteurYolox


@runtime_checkable
class Detector(Protocol):
    def detecter(self, bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Image BGR uint8 (H, W, 3) en pleine résolution de la vidéo.

        Rend (boîtes, scores) : boîtes xyxy float32 (N, 4) en pixels de cette image, bornées à [0, W-1] × [0, H-1] ;
        scores float32 (N,) dans [0, 1], déjà filtrés par le seuil ; une seule classe (personne). L'ordre des
        détections doit être déterministe : le suivi les reçoit dans cet ordre.
        """
        ...


def creer_detecteur(analyse: dict, chemin_modele: str, threads: int | None = None) -> Detector:
    return DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]), float(analyse["seuil_detection"]),
                          float(analyse["seuil_nms"]), threads)
