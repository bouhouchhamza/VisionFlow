"""Lecture d'une vidéo avec le temps vidéo de chaque image.

Deux modes, choisis explicitement dans la configuration après contrôle E3 :
- `pts` : PTS du conteneur ramenés à zéro sur la première image ; refuse des PTS non strictement croissants.
- `rang_cadence_nominale` : rang d'affichage × durée nominale d'image. Temps reconstruit, réservé aux conteneurs à
  cadence fixe par construction (AVI) dont les PTS ne sont pas des instants de présentation ; refuse tout paquet vide
  (image sautée), qui décalerait le rang. Ne restitue pas un temps de capture que le fichier ne contient pas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterator

import av

MODES_TEMPS = ("pts", "rang_cadence_nominale")


@dataclass
class Image:
    index: int
    pts: int | None
    t_s: float
    reconstruit: bool
    cle: bool
    trame: av.VideoFrame

    @property
    def t_ms(self) -> int:
        return int(round(self.t_s * 1000))


@dataclass
class BilanTemps:
    """Ce que la lecture a constaté sur les horodatages."""

    mode: str = "pts"
    images: int = 0
    paquets: int = 0
    paquets_vides: int = 0
    pts_absents: int = 0
    pts_bruts_non_croissants: int = 0
    images_temps_reconstruit: int = 0
    intervalle_min_ms: float | None = None
    intervalle_max_ms: float | None = None
    premier_pts: int | None = None
    base_de_temps: str | None = None
    cadence_nominale: str | None = None
    exemples_pts_non_croissants: list[dict] = field(default_factory=list)

    def en_dict(self) -> dict:
        d = dict(self.__dict__)
        d["exemples_pts_non_croissants"] = self.exemples_pts_non_croissants[:10]
        return d


def metadonnees(chemin: str) -> dict:
    with av.open(chemin) as c:
        s = c.streams.video[0]
        return {
            "format": c.format.name,
            "codec": s.codec_context.name,
            "largeur": s.codec_context.width,
            "hauteur": s.codec_context.height,
            "images_b": bool(s.codec_context.has_b_frames),
            "cadence_moyenne": str(s.average_rate) if s.average_rate else None,
            "base_de_temps": str(s.time_base),
            "images_declarees": s.frames or None,
            "duree_declaree_s": float(s.duration * s.time_base) if s.duration else None,
            "debut_flux_pts": s.start_time,
        }


class TempsVideoInvalide(ValueError):
    pass


def lire(chemin: str, bilan: BilanTemps | None = None, mode: str = "pts") -> Iterator[Image]:
    """Décode toutes les images dans l'ordre d'affichage avec leur temps vidéo selon `mode`."""
    if mode not in MODES_TEMPS:
        raise ValueError(f"mode de temps inconnu : {mode}")
    bilan = bilan if bilan is not None else BilanTemps()
    bilan.mode = mode
    with av.open(chemin) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        tb = s.time_base
        bilan.base_de_temps = str(tb)
        bilan.cadence_nominale = str(s.average_rate) if s.average_rate else None
        if mode == "rang_cadence_nominale" and not s.average_rate:
            raise TempsVideoInvalide("cadence nominale absente : mode rang_cadence_nominale impossible")
        duree_image = Fraction(1) / Fraction(s.average_rate) if s.average_rate else None
        premier = None
        pts_prec = None
        t_prec = None
        index = 0
        for paquet in c.demux(s):
            fin = paquet.dts is None and paquet.size == 0
            if not fin:
                bilan.paquets += 1
                if paquet.size == 0:
                    bilan.paquets_vides += 1
                    if mode == "rang_cadence_nominale":
                        raise TempsVideoInvalide(f"paquet vide (image sautée) au paquet {bilan.paquets - 1} : "
                                                 "le rang d'affichage ne donne plus le temps")
            for trame in paquet.decode():
                bilan.images += 1
                if trame.pts is None:
                    bilan.pts_absents += 1
                else:
                    if premier is None:
                        premier = trame.pts
                        bilan.premier_pts = premier
                    if pts_prec is not None and trame.pts <= pts_prec:
                        bilan.pts_bruts_non_croissants += 1
                        if len(bilan.exemples_pts_non_croissants) < 10:
                            bilan.exemples_pts_non_croissants.append({"index": index, "pts": trame.pts, "pts_precedent": pts_prec})
                    pts_prec = trame.pts
                if mode == "pts":
                    if trame.pts is None:
                        raise TempsVideoInvalide(f"image {index} sans PTS en mode pts")
                    t_s = float(Fraction(trame.pts - premier) * tb)
                    if t_prec is not None and t_s <= t_prec:
                        raise TempsVideoInvalide(f"PTS non croissant à l'image {index} : le mode pts n'est pas "
                                                 "applicable à cette vidéo (voir E3)")
                    reconstruit = False
                else:
                    t_s = float(index * duree_image)
                    reconstruit = True
                    bilan.images_temps_reconstruit += 1
                if t_prec is not None:
                    d = (t_s - t_prec) * 1000
                    bilan.intervalle_min_ms = d if bilan.intervalle_min_ms is None else min(bilan.intervalle_min_ms, d)
                    bilan.intervalle_max_ms = d if bilan.intervalle_max_ms is None else max(bilan.intervalle_max_ms, d)
                t_prec = t_s
                yield Image(index=index, pts=trame.pts, t_s=t_s, reconstruit=reconstruit, cle=bool(trame.key_frame),
                            trame=trame)
                index += 1


class Echantillonneur:
    """Retient la première image à partir de chaque instant k / cadence (temps vidéo, pas temps de calcul)."""

    def __init__(self, cadence: float):
        self.pas = 1.0 / cadence
        self.prochain = 0

    def garder(self, t_s: float) -> bool:
        if t_s + 1e-9 >= self.prochain * self.pas:
            self.prochain = math.floor(t_s / self.pas + 1e-9) + 1
            return True
        return False


def format_temps(t_ms: int | float) -> str:
    t = int(round(t_ms))
    h, reste = divmod(t, 3_600_000)
    m, reste = divmod(reste, 60_000)
    s, ms = divmod(reste, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
