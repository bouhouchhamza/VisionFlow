"""Géométrie de ligne, franchissements bruts et règle de passage (maintien).

Convention des côtés : en parcourant la ligne de p1 vers p2 sur l'image affichée (y vers le bas), « gauche » est
le côté situé à gauche de ce trajet. Pour une ligne tracée de gauche à droite de l'écran, « gauche » est en haut.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

GAUCHE, DROITE = -1, 1
SENS_GEOMETRIQUES = {(GAUCHE, DROITE): "gauche_vers_droite", (DROITE, GAUCHE): "droite_vers_gauche"}


@dataclass(frozen=True)
class Ligne:
    id: str
    p1: tuple[float, float]
    p2: tuple[float, float]
    sens: dict
    marge_px: float = 0.0
    extension: float = 0.0

    @classmethod
    def depuis_config(cls, d: dict, largeur: int, hauteur: int) -> "Ligne":
        return cls(
            id=d["id"],
            p1=(d["p1"][0] * largeur, d["p1"][1] * hauteur),
            p2=(d["p2"][0] * largeur, d["p2"][1] * hauteur),
            sens=dict(d["sens"]),
            marge_px=float(d.get("marge_px", 0.0)),
            extension=float(d.get("extension_segment", 0.0)),
        )

    @property
    def longueur(self) -> float:
        return math.hypot(self.p2[0] - self.p1[0], self.p2[1] - self.p1[1])

    def distance_signee(self, x: float, y: float) -> float:
        dx, dy = self.p2[0] - self.p1[0], self.p2[1] - self.p1[1]
        return (dx * (y - self.p1[1]) - dy * (x - self.p1[0])) / self.longueur

    def cote(self, x: float, y: float) -> int:
        """-1 gauche, +1 droite, 0 dans la marge morte autour de la ligne."""
        d = self.distance_signee(x, y)
        if abs(d) <= self.marge_px:
            return 0
        return GAUCHE if d < 0 else DROITE

    def position_croisement(self, a: tuple[float, float], b: tuple[float, float]) -> float | None:
        """Position u (0 = p1, 1 = p2) où le trajet a→b coupe la droite porteuse ; None si parallèle."""
        da, db = self.distance_signee(*a), self.distance_signee(*b)
        if da == db:
            return None
        k = da / (da - db)
        x, y = a[0] + k * (b[0] - a[0]), a[1] + k * (b[1] - a[1])
        dx, dy = self.p2[0] - self.p1[0], self.p2[1] - self.p1[1]
        return ((x - self.p1[0]) * dx + (y - self.p1[1]) * dy) / (self.longueur**2)

    def direction(self, depart: int, arrivee: int) -> tuple[str, str]:
        geo = SENS_GEOMETRIQUES[(depart, arrivee)]
        return geo, self.sens[geo]


@dataclass
class Franchissement:
    id: str
    ligne: str
    piste: int
    sens_geometrique: str
    direction: str
    t_ms: int
    num_image: int
    t_ms_avant: int
    num_image_avant: int
    u: float
    point: tuple[float, float]
    confiance: float

    def en_dict(self) -> dict:
        d = asdict(self)
        d["point"] = [round(self.point[0], 1), round(self.point[1], 1)]
        d["u"] = round(self.u, 4)
        d["confiance"] = round(self.confiance, 4)
        return d


class DetecteurFranchissements:
    """Émet un franchissement brut quand le point d'ancrage d'une piste change de côté à travers le segment.

    L'instant retenu est la première image analysée du nouveau côté ; `t_ms_avant` est la dernière image analysée
    de l'ancien côté. Le vrai instant se situe entre les deux.
    """

    def __init__(self, lignes: Iterable[Ligne]):
        self.lignes = list(lignes)
        self.etat: dict[tuple[str, int], tuple[int, int, int, tuple[float, float]]] = {}
        self.franchissements: list[Franchissement] = []

    def observer(self, piste: int, t_ms: int, num_image: int, x: float, y: float, confiance: float) -> list[Franchissement]:
        emis = []
        for ligne in self.lignes:
            cote = ligne.cote(x, y)
            if cote == 0:
                continue
            cle = (ligne.id, piste)
            prec = self.etat.get(cle)
            self.etat[cle] = (cote, t_ms, num_image, (x, y))
            if prec is None or prec[0] == cote:
                continue
            u = ligne.position_croisement(prec[3], (x, y))
            if u is None or not (-ligne.extension <= u <= 1 + ligne.extension):
                continue
            geo, direction = ligne.direction(prec[0], cote)
            f = Franchissement(
                id=f"f{len(self.franchissements) + 1:04d}",
                ligne=ligne.id,
                piste=piste,
                sens_geometrique=geo,
                direction=direction,
                t_ms=t_ms,
                num_image=num_image,
                t_ms_avant=prec[1],
                num_image_avant=prec[2],
                u=u,
                point=(x, y),
                confiance=confiance,
            )
            self.franchissements.append(f)
            emis.append(f)
        return emis


PASSAGE, ANNULE_RETOUR, NON_CONFIRME_FIN = "passage", "annule_par_retour", "non_confirme_fin_video"


def appliquer_maintien(chaine: list[dict], maintien_ms: int, fin_ms: int | None, fin_par_video: bool) -> list[str]:
    """Statut de chaque franchissement d'une même chaîne (même personne, même ligne), triée par temps.

    Deux franchissements consécutifs séparés de moins de `maintien_ms` s'annulent (aller-retour). Le dernier
    franchissement n'est pas confirmé si l'observation s'arrête à cause de la fin de la vidéo moins de
    `maintien_ms` après lui. `maintien_ms` est un paramètre d'hypothèse, pas une vérité terrain.
    """
    statuts = [PASSAGE] * len(chaine)
    i = 0
    while i < len(chaine):
        if i + 1 < len(chaine) and chaine[i + 1]["t_ms"] - chaine[i]["t_ms"] < maintien_ms:
            statuts[i] = statuts[i + 1] = ANNULE_RETOUR
            i += 2
            continue
        if i == len(chaine) - 1 and fin_par_video and fin_ms is not None and fin_ms - chaine[i]["t_ms"] < maintien_ms:
            statuts[i] = NON_CONFIRME_FIN
        i += 1
    return statuts


def chaines_machine(franchissements: list[dict]) -> dict[tuple[str, int], list[dict]]:
    chaines: dict[tuple[str, int], list[dict]] = {}
    for f in sorted(franchissements, key=lambda f: (f["t_ms"], f["id"])):
        chaines.setdefault((f["ligne"], f["piste"]), []).append(f)
    return chaines


def deriver_passages_machine(
    franchissements: list[dict], fin_pistes_ms: dict[int, int], fin_video_ms: int, pas_ms: float, maintien_ms: int
) -> list[dict]:
    """Applique la règle de maintien aux franchissements bruts d'un run. Ne modifie pas les entrées."""
    resultat = []
    for (_, piste), chaine in chaines_machine(franchissements).items():
        fin = fin_pistes_ms.get(piste)
        fin_par_video = fin is not None and fin >= fin_video_ms - 2 * pas_ms
        for f, statut in zip(chaine, appliquer_maintien(chaine, maintien_ms, fin, fin_par_video)):
            resultat.append({"franchissement": f["id"], "ligne": f["ligne"], "piste": piste, "direction": f["direction"],
                             "t_ms": f["t_ms"], "statut": statut})
    return sorted(resultat, key=lambda r: (r["t_ms"], r["franchissement"]))


def doublons_probables(passages: list[dict], fenetre_ms: int) -> list[tuple[str, str]]:
    """Paires de passages de pistes différentes, même ligne et même sens, proches dans le temps.

    Ce n'est qu'un signal : deux personnes qui marchent ensemble produisent le même motif.
    """
    retenus = sorted((p for p in passages if p["statut"] == PASSAGE), key=lambda p: p["t_ms"])
    paires = []
    for i, a in enumerate(retenus):
        for b in retenus[i + 1:]:
            if b["t_ms"] - a["t_ms"] > fenetre_ms:
                break
            if a["ligne"] == b["ligne"] and a["direction"] == b["direction"] and a["piste"] != b["piste"]:
                paires.append((a["franchissement"], b["franchissement"]))
    return paires
