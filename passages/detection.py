"""Détection d'objets COCO avec YOLOX (export ONNX officiel 0.1.1rc0) sur ONNX Runtime CPU.

Pré- et post-traitement repris de YOLOX `yolox/data/data_augment.py::preproc` et `yolox/utils/demo_utils.py`
(Apache-2.0, Megvii). Depuis 0.1.1, l'entrée est en BGR 0-255 sans normalisation moyenne/écart-type.
Décodage multi-étiquette, comme `multiclass_nms` de la démo : un score par classe demandée (objectness × probabilité de
la classe), sans argmax, et une NMS par classe. Par défaut, seule la classe 0 (personne) est décodée.
"""

from __future__ import annotations

import cv2
import numpy as np
import onnxruntime as ort

# Les 80 classes contiguës de YOLOX, dans l'ordre des colonnes 5 à 84 de la sortie du modèle
# (`yolox/data/datasets/coco_classes.py` au tag 0.1.1rc0, Apache-2.0, Megvii).
COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
)
CLASSE_PERSONNE = 0
COLONNES_SORTIE = 5 + len(COCO_CLASSES)


def indices_classes(noms) -> tuple[int, ...]:
    """Noms de classes COCO -> indices du modèle, par ordre croissant. Liste vide, nom inconnu ou doublon refusés."""
    if isinstance(noms, str) or not noms:
        raise ValueError("classes : liste non vide de noms attendue")
    noms = tuple(noms)
    inconnus = [n for n in noms if not isinstance(n, str) or n not in COCO_CLASSES]
    if inconnus:
        raise ValueError(f"classes inconnues du vocabulaire COCO de YOLOX : {inconnus}")
    if len(set(noms)) != len(noms):
        raise ValueError(f"classes en double : {list(noms)}")
    return tuple(sorted(COCO_CLASSES.index(n) for n in noms))


class DetecteurYolox:
    def __init__(self, chemin: str, taille_entree: tuple[int, int] = (640, 640), seuil: float = 0.1,
                 seuil_nms: float = 0.45, threads: int | None = None,
                 classes: tuple[int, ...] = (CLASSE_PERSONNE,)):
        classes = tuple(classes)
        if not classes or len(set(classes)) != len(classes) \
                or not all(type(k) is int and 0 <= k < len(COCO_CLASSES) for k in classes):
            raise ValueError(f"classes : indices entiers distincts dans [0, {len(COCO_CLASSES) - 1}] attendus")
        self.classes = tuple(sorted(classes))
        options = ort.SessionOptions()
        # Sans cela, les threads d'inférence en attente active privent le décodage et la conversion de CPU.
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        if threads:
            options.intra_op_num_threads = threads
        self.session = ort.InferenceSession(chemin, options, providers=["CPUExecutionProvider"])
        # Forme déclarée par le modèle, lue sans inférence. Une dimension symbolique ou inconnue est refusée : rien ne
        # garantirait alors que les colonnes 5 à 84 sont les 80 classes de COCO_CLASSES.
        colonnes = self.session.get_outputs()[0].shape[-1]
        if type(colonnes) is not int or colonnes != COLONNES_SORTIE:
            raise ValueError(f"sortie du modèle : {COLONNES_SORTIE} colonnes attendues (4 boîte, objectness, "
                             f"{len(COCO_CLASSES)} classes), {colonnes!r} déclarées")
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

    def decoder(self, sortie: np.ndarray, ratio: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Boîtes float32 (N, 4), scores float32 (N,), indices de classe int64 (N,).

        Ordre : par indice de classe croissant, puis ordre de la NMS. `self.seuil` reste un float Python, pour que la
        comparaison se fasse en float32 ; les boîtes sont divisées par le ratio avant la NMS, dont l'IoU (+1 pixel)
        dépend de l'échelle.
        """
        pred = sortie.copy()
        pred[:, :2] = (pred[:, :2] + self.grilles) * self.pas
        pred[:, 2:4] = np.exp(pred[:, 2:4]) * self.pas
        parties = []
        for k in self.classes:
            scores = pred[:, 4] * pred[:, 5 + k]
            garde = scores > self.seuil
            candidats, scores = pred[garde], scores[garde]
            if not len(scores):
                continue
            boites = np.empty((len(candidats), 4), np.float32)
            boites[:, 0] = candidats[:, 0] - candidats[:, 2] / 2
            boites[:, 1] = candidats[:, 1] - candidats[:, 3] / 2
            boites[:, 2] = candidats[:, 0] + candidats[:, 2] / 2
            boites[:, 3] = candidats[:, 1] + candidats[:, 3] / 2
            boites /= ratio
            retenus = nms(boites, scores, self.seuil_nms)
            parties.append((boites[retenus], scores[retenus], np.full(len(retenus), k, dtype=np.int64)))
        if not parties:
            return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32), np.zeros((0,), np.int64)
        boites, scores, ids = (np.concatenate(t) for t in zip(*parties))
        return boites, scores, ids

    def detecter(self, bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        entree, ratio = self.pretraiter(bgr)
        sortie = self.session.run(None, {self.entree: entree})[0][0]
        boites, scores, ids = self.decoder(sortie, ratio)
        h, w = bgr.shape[:2]
        boites[:, [0, 2]] = np.clip(boites[:, [0, 2]], 0, w - 1)
        boites[:, [1, 3]] = np.clip(boites[:, [1, 3]], 0, h - 1)
        return boites, scores, ids


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
