"""Tracés communs : ligne, côtés, flèche d'entrée, textes (police Hershey : ASCII uniquement)."""

from __future__ import annotations

import math

import cv2
import numpy as np

from passages.crossing import Ligne

JAUNE, CYAN, VERT, ROUGE, BLANC, GRIS, ORANGE = (0, 255, 255), (255, 255, 0), (0, 200, 0), (0, 0, 255), (255, 255, 255), (150, 150, 150), (0, 140, 255)
POLICE = cv2.FONT_HERSHEY_SIMPLEX


def texte(img: np.ndarray, contenu: str, org: tuple[int, int], echelle: float = 0.6, couleur=BLANC, epaisseur: int = 1) -> None:
    cv2.putText(img, contenu, org, POLICE, echelle, (0, 0, 0), epaisseur + 3, cv2.LINE_AA)
    cv2.putText(img, contenu, org, POLICE, echelle, couleur, epaisseur, cv2.LINE_AA)


def _pt(p: tuple[float, float], s: float) -> tuple[int, int]:
    return int(round(p[0] * s)), int(round(p[1] * s))


def ligne(img: np.ndarray, l: Ligne, s: float = 1.0, couleur=JAUNE, epaisseur: int = 2, details: bool = True) -> None:
    a, b = _pt(l.p1, s), _pt(l.p2, s)
    if l.extension > 0:
        dx, dy = b[0] - a[0], b[1] - a[1]
        ea = (int(a[0] - dx * l.extension), int(a[1] - dy * l.extension))
        eb = (int(b[0] + dx * l.extension), int(b[1] + dy * l.extension))
        cv2.line(img, ea, a, couleur, 1, cv2.LINE_AA)
        cv2.line(img, b, eb, couleur, 1, cv2.LINE_AA)
    cv2.line(img, a, b, couleur, epaisseur, cv2.LINE_AA)
    if not details:
        return
    f = max(1.0, img.shape[1] / 1100)
    ep = max(1, int(round(f)))
    texte(img, "p1", (a[0] - int(30 * f), a[1] + 5), 0.5 * f, couleur, ep)
    texte(img, "p2", (b[0] + 8, b[1] + 5), 0.5 * f, couleur, ep)
    dx, dy = l.p2[0] - l.p1[0], l.p2[1] - l.p1[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    m = ((l.p1[0] + l.p2[0]) / 2, (l.p1[1] + l.p2[1]) / 2)
    long = 70 * f / s
    gauche = (m[0] - nx * long, m[1] - ny * long)
    droite = (m[0] + nx * long, m[1] + ny * long)
    nom_g = l.sens["droite_vers_gauche"]
    nom_d = l.sens["gauche_vers_droite"]
    texte(img, f"cote G (apres {nom_g})", _pt((gauche[0] - 90 * f / s, gauche[1] - 8 * f / s), s), 0.5 * f, couleur, ep)
    texte(img, f"cote D (apres {nom_d})", _pt((droite[0] - 90 * f / s, droite[1] + 22 * f / s), s), 0.5 * f, couleur, ep)
    debut, fin, nom = (gauche, droite, nom_d) if nom_d == "entree" else (droite, gauche, nom_g)
    cv2.arrowedLine(img, _pt(debut, s), _pt(fin, s), VERT, 2 * ep, cv2.LINE_AA, tipLength=0.25)
    texte(img, f"{nom} = {'G vers D' if debut is gauche else 'D vers G'}", _pt((fin[0] + 14 * f / s, fin[1]), s), 0.55 * f, VERT, ep)
