"""Outil d'annotation manuelle des passages (vérité terrain humaine, protocole E1 v2).

N'affiche jamais de détection ni de piste : l'annotation doit être indépendante du système évalué.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import av
import cv2
import numpy as np

import passages
from passages import dessin
from passages.config import charger, sha256_fichier
from passages.crossing import Ligne
from passages.run import RACINE
from passages.video import format_temps, lire

FENETRE = "Annotation passages (h = aide)"
TOUCHES_GAUCHE = {2424832, ord("a")}
TOUCHES_DROITE = {2555904, ord("d")}
PAGE_HAUT, PAGE_BAS = 2162688, 2228224
VITESSES = [0.25, 0.5, 1.0, 2.0]
AIDE = [
    "espace : lecture / pause      fleches ou a/d : image -1/+1     j / l : -1 s / +1 s",
    "PgUp / PgDn : -10 s / +10 s   + / - : vitesse de lecture",
    "e : franchissement ENTREE     x : franchissement SORTIE        (une touche par personne)",
    "r : le dernier franchissement saisi est le RETOUR d'un franchissement precedent (r encore : candidat plus ancien)",
    "t : demi-tour SANS franchissement   n : debut / fin d'intervalle NON OBSERVABLE",
    "i : basculer 'incertain' sur la derniere saisie   c : basculer 'horloge incrustee illisible'",
    "u : annuler la derniere saisie   s : sauvegarder   q / Echap : sauvegarder et quitter   h : aide",
]


def table_images(chemin: str, sha: str, mode: str, afficher=print) -> dict:
    """Temps de chaque image (même calcul que l'analyse) et images clés {pts: rang} pour la recherche."""
    cache = RACINE / "data" / "cache" / sha[:16] / f"images_{mode}.json"
    if cache.exists():
        with open(cache, encoding="utf-8") as f:
            contenu = json.load(f)
        if contenu.get("sha256") == sha and contenu.get("av") == av.__version__:
            return contenu
    afficher("première ouverture : relevé du temps de toutes les images (une seule fois)…")
    t_ms, cles = [], []
    for im in lire(chemin, mode=mode):
        t_ms.append(im.t_ms)
        if im.cle:
            if im.pts is None:
                raise RuntimeError(f"image clé {im.index} sans PTS : recherche impossible")
            cles.append([im.pts, im.index])
    if len({p for p, _ in cles}) != len(cles):
        raise RuntimeError("PTS d'images clés en double : recherche impossible")
    contenu = {"sha256": sha, "av": av.__version__, "mode": mode, "t_ms": t_ms, "cles": cles}
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(contenu, f)
    return contenu


class Navigateur:
    def __init__(self, chemin: str, cles: list[list[int]], largeur: int, taille_cache: int = 120):
        self.c = av.open(chemin)
        self.s = self.c.streams.video[0]
        self.s.thread_type = "AUTO"
        self.cles = sorted(cles, key=lambda c: c[1])
        self.rang_cle = {p: i for p, i in cles}
        self.largeur = largeur
        self.cache: OrderedDict[int, np.ndarray] = OrderedDict()
        self.taille_cache = taille_cache
        self.flux = None
        self.dernier = None

    def fermer(self) -> None:
        self.c.close()

    def _garder(self, i: int, trame) -> None:
        img = trame.to_ndarray(format="bgr24")
        h, w = img.shape[:2]
        if w != self.largeur:
            img = cv2.resize(img, (self.largeur, int(round(h * self.largeur / w))), interpolation=cv2.INTER_AREA)
        self.cache[i] = img
        self.cache.move_to_end(i)
        while len(self.cache) > self.taille_cache:
            self.cache.popitem(last=False)

    def _chercher(self, i: int) -> None:
        pts_cle, rang = max((c for c in self.cles if c[1] <= i), key=lambda c: c[1])
        self.c.seek(pts_cle, stream=self.s, backward=True, any_frame=False)
        self.flux = self.c.decode(self.s)
        trame = next(self.flux)
        if not trame.key_frame or self.rang_cle.get(trame.pts) != rang:
            raise RuntimeError(f"recherche : image clé attendue au rang {rang}, obtenue pts={trame.pts}")
        self.dernier = rang
        self._garder(rang, trame)

    def image(self, i: int) -> np.ndarray:
        if i in self.cache:
            self.cache.move_to_end(i)
            return self.cache[i]
        if self.dernier is None or not (self.dernier < i <= self.dernier + 90):
            self._chercher(i)
        while self.dernier < i:
            trame = next(self.flux)
            self.dernier += 1
            if trame.key_frame and self.rang_cle.get(trame.pts, self.dernier) != self.dernier:
                raise RuntimeError(f"désynchronisation : image clé pts={trame.pts} au rang {self.dernier}")
            self._garder(self.dernier, trame)
        return self.cache[i]


class Annotation:
    def __init__(self, chemin: Path, entete: dict, existante: dict | None):
        self.chemin = chemin
        self.doc = existante or {**entete, "franchissements": [], "demi_tours": [], "non_observables": [],
                                 "plages_couvertes": []}
        self.doc["derniere_sauvegarde_utc"] = None
        self.ordre: list[tuple[str, str]] = []
        self.plages: list[list[int]] = [[p["debut_image"], p["fin_image"]] for p in self.doc["plages_couvertes"]]
        self.no_ouvert: dict | None = None
        self.candidat_retour = 0
        self.compteur = max([int(e["id"][1:]) for k in ("franchissements", "demi_tours", "non_observables")
                             for e in self.doc[k]] + [0])

    def _id(self, prefixe: str) -> str:
        self.compteur += 1
        return f"{prefixe}{self.compteur:04d}"

    def franchir(self, ligne: str, direction: str, i: int, t_ms: int) -> None:
        e = {"id": self._id("f"), "ligne": ligne, "direction": direction, "t_ms": t_ms, "num_image": i,
             "retour_de": None, "incertain": False, "horloge_incrustee_illisible": False, "remarque": ""}
        self.doc["franchissements"].append(e)
        self.ordre.append(("franchissements", e["id"]))
        self.candidat_retour = 0

    def lier_retour(self) -> str:
        fr = self.doc["franchissements"]
        if not fr or not self.ordre or self.ordre[-1][0] != "franchissements":
            return "r : la derniere saisie doit etre un franchissement"
        dernier = next(e for e in fr if e["id"] == self.ordre[-1][1])
        candidats = sorted((e for e in fr if e["ligne"] == dernier["ligne"] and e["direction"] != dernier["direction"]
                            and e["t_ms"] <= dernier["t_ms"] and e["id"] != dernier["id"]),
                           key=lambda e: -e["t_ms"])
        if not candidats:
            return "r : aucun franchissement anterieur de sens oppose"
        if self.candidat_retour >= len(candidats):
            self.candidat_retour = 0
            dernier["retour_de"] = None
            return "r : lien de retour retire"
        c = candidats[self.candidat_retour]
        self.candidat_retour += 1
        dernier["retour_de"] = c["id"]
        return f"r : {dernier['id']} est le retour de {c['id']} ({format_temps(c['t_ms'])})"

    def demi_tour(self, ligne: str, i: int, t_ms: int) -> None:
        e = {"id": self._id("d"), "ligne": ligne, "t_ms": t_ms, "num_image": i, "incertain": False, "remarque": ""}
        self.doc["demi_tours"].append(e)
        self.ordre.append(("demi_tours", e["id"]))

    def basculer_non_observable(self, i: int, t_ms: int) -> str:
        if self.no_ouvert is None:
            self.no_ouvert = {"id": self._id("n"), "debut_image": i, "debut_ms": t_ms}
            return "non observable : debut note, appuyer n a la fin"
        e = self.no_ouvert
        if i < e["debut_image"]:
            e["debut_image"], e["debut_ms"], i, t_ms = i, t_ms, e["debut_image"], e["debut_ms"]
        e.update({"fin_image": i, "fin_ms": t_ms, "remarque": ""})
        self.doc["non_observables"].append(e)
        self.ordre.append(("non_observables", e["id"]))
        self.no_ouvert = None
        return f"non observable : {format_temps(e['debut_ms'])} -> {format_temps(t_ms)}"

    def derniere(self) -> dict | None:
        if not self.ordre:
            return None
        cle, ident = self.ordre[-1]
        return next(e for e in self.doc[cle] if e["id"] == ident)

    def annuler(self) -> str:
        if not self.ordre:
            return "rien a annuler (seules les saisies de cette session sont annulables)"
        cle, ident = self.ordre.pop()
        self.doc[cle] = [e for e in self.doc[cle] if e["id"] != ident]
        for e in self.doc["franchissements"]:
            if e["retour_de"] == ident:
                e["retour_de"] = None
        return f"annule : {ident}"

    def voir(self, i_prec: int | None, i: int) -> None:
        if i_prec is not None and i == i_prec + 1:
            self.plages.append([i_prec, i])
        elif not any(a <= i <= b for a, b in self.plages):
            self.plages.append([i, i])

    def plages_fusionnees(self) -> list[list[int]]:
        out: list[list[int]] = []
        for a, b in sorted(self.plages):
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out

    def sauver(self, t_de) -> None:
        self.plages = self.plages_fusionnees()
        self.doc["plages_couvertes"] = [{"debut_image": a, "fin_image": b, "debut_ms": t_de(a), "fin_ms": t_de(b)}
                                        for a, b in self.plages if b > a]
        self.doc["derniere_sauvegarde_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.no_ouvert is not None:
            self.doc["non_observable_ouvert"] = self.no_ouvert
        else:
            self.doc.pop("non_observable_ouvert", None)
        tmp = self.chemin.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        tmp.replace(self.chemin)


def annoter(chemin_config: str, annotateur: str, passe: int, id_echantillon: str, sortie: str | None,
            reprendre: bool, largeur: int = 1280, afficher=print) -> Path:
    cfg, _ = charger(chemin_config)
    chemin_video = str(RACINE / cfg["video"]["chemin"])
    sha = sha256_fichier(chemin_video).upper()
    if sha != cfg["video"]["sha256"].upper():
        raise RuntimeError("empreinte vidéo différente de la configuration")
    if cfg["video"].get("role_echantillon") == "reserve":
        raise RuntimeError("extrait de réserve : annotation interdite tant que la configuration n'est pas gelée")
    chemin = Path(sortie) if sortie else RACINE / "data" / "annotations" / sha[:16] / f"{annotateur}_passe{passe}.json"
    existante = None
    if chemin.exists():
        if not reprendre:
            raise RuntimeError(f"{chemin} existe : utiliser --reprendre pour continuer cette annotation")
        with open(chemin, encoding="utf-8") as f:
            existante = json.load(f)
        if existante["video"]["sha256"] != sha:
            raise RuntimeError("l'annotation existante porte sur une autre vidéo")
    chemin.parent.mkdir(parents=True, exist_ok=True)

    mode = cfg["video"].get("mode_temps", "pts")
    table = table_images(chemin_video, sha, mode, afficher)
    with av.open(chemin_video) as c:
        s = c.streams.video[0]
        W, H = s.codec_context.width, s.codec_context.height
        pas_ms = float(1000 / s.average_rate) if s.average_rate else 33.3
    temps = table["t_ms"]
    t_de = temps.__getitem__
    n = len(temps)
    entete = {
        "format": "annotation_passages", "version_format": 2, "version_protocole": 2,
        "nature": "verite_terrain_humaine", "detecteur_affiche": False,
        "video": {"id_echantillon": id_echantillon, "sha256": sha, "nom_fichier": Path(chemin_video).name,
                  "images": n, "duree_ms": t_de(n - 1), "mode_temps": mode},
        "annotateur": annotateur, "passe": passe, "outil": f"passages.annotate {passages.__version__}",
        "debut_annotation_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lignes": cfg["lignes"],
    }
    note = Annotation(chemin, entete, existante)
    s_aff = largeur / W
    lignes = [Ligne.depuis_config(l, W, H) for l in cfg["lignes"]]
    ligne_active = 0
    nav = Navigateur(chemin_video, table["cles"], largeur)
    cv2.namedWindow(FENETRE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(FENETRE, largeur, int(H * s_aff))
    i, i_prec = 0, None
    lecture, vitesse, aide, message = False, 2, True, "pret"
    derniere_sauvegarde = datetime.now()
    try:
        while True:
            note.voir(i_prec, i)
            img = nav.image(i).copy()
            for k, l in enumerate(lignes):
                dessin.ligne(img, l, s_aff, dessin.JAUNE if k == ligne_active else dessin.GRIS, details=k == ligne_active)
            fr = note.doc["franchissements"]
            ne = sum(e["direction"] == "entree" for e in fr)
            nso = sum(e["direction"] == "sortie" for e in fr)
            nr = sum(e["retour_de"] is not None for e in fr)
            dessin.texte(img, f"t {format_temps(t_de(i))}   image {i}/{n - 1}   {'LECTURE' if lecture else 'pause'} x{VITESSES[vitesse]}"
                              f"   ligne {lignes[ligne_active].id}", (10, 24), 0.65)
            dessin.texte(img, f"entrees {ne}  sorties {nso}  dont retours {nr}  demi-tours {len(note.doc['demi_tours'])}"
                              f"  non observables {len(note.doc['non_observables'])}{'  [NO OUVERT]' if note.no_ouvert else ''}",
                         (10, 50), 0.55)
            d = note.derniere()
            if d:
                dessin.texte(img, f"derniere saisie : {d['id']} {d.get('direction', '')} {format_temps(d.get('t_ms', d.get('debut_ms', 0)))}"
                                  f"{' retour_de ' + d['retour_de'] if d.get('retour_de') else ''}{' INCERTAIN' if d.get('incertain') else ''}",
                             (10, 76), 0.55, dessin.VERT)
            dessin.texte(img, message, (10, img.shape[0] - 14), 0.55, dessin.ORANGE)
            if aide:
                for k, txt in enumerate(AIDE):
                    dessin.texte(img, txt, (10, 110 + 22 * k), 0.5, dessin.CYAN)
            cv2.imshow(FENETRE, img)
            delai = max(1, int(pas_ms / VITESSES[vitesse])) if lecture else 0
            touche = cv2.waitKeyEx(delai)
            if cv2.getWindowProperty(FENETRE, cv2.WND_PROP_VISIBLE) < 1:
                break
            i_prec = i
            t = t_de(i)
            if touche == -1:
                if lecture:
                    if i < n - 1:
                        i += 1
                    else:
                        lecture, message = False, "fin de la video"
                continue
            k = touche & 0xFF if touche < 256 else touche
            if k in (ord("q"), 27):
                break
            elif k == ord(" "):
                lecture = not lecture
            elif k in TOUCHES_DROITE:
                lecture, i = False, min(n - 1, i + 1)
            elif k in TOUCHES_GAUCHE:
                lecture, i = False, max(0, i - 1)
            elif k == ord("l"):
                i = min(n - 1, i + int(round(1000 / pas_ms)))
            elif k == ord("j"):
                i = max(0, i - int(round(1000 / pas_ms)))
            elif k == PAGE_BAS:
                i = min(n - 1, i + int(round(10000 / pas_ms)))
            elif k == PAGE_HAUT:
                i = max(0, i - int(round(10000 / pas_ms)))
            elif k == ord("+"):
                vitesse = min(len(VITESSES) - 1, vitesse + 1)
            elif k == ord("-"):
                vitesse = max(0, vitesse - 1)
            elif k == ord("h"):
                aide = not aide
            elif k in (ord("e"), ord("x")):
                lecture = False
                note.franchir(lignes[ligne_active].id, "entree" if k == ord("e") else "sortie", i, t)
                message = f"{'entree' if k == ord('e') else 'sortie'} notee a {format_temps(t)} (image {i})"
            elif k == ord("r"):
                message = note.lier_retour()
            elif k == ord("t"):
                lecture = False
                note.demi_tour(lignes[ligne_active].id, i, t)
                message = f"demi-tour sans franchissement note a {format_temps(t)}"
            elif k == ord("n"):
                message = note.basculer_non_observable(i, t)
            elif k == ord("i"):
                if d:
                    d["incertain"] = not d.get("incertain", False)
                    message = f"{d['id']} incertain = {d['incertain']}"
            elif k == ord("c"):
                if d and "horloge_incrustee_illisible" in d:
                    d["horloge_incrustee_illisible"] = not d["horloge_incrustee_illisible"]
            elif k == ord("u"):
                message = note.annuler()
            elif k == ord("s"):
                note.sauver(t_de)
                message = f"sauvegarde : {chemin.name}"
            elif k == ord("v") and len(lignes) > 1:
                ligne_active = (ligne_active + 1) % len(lignes)
            if (datetime.now() - derniere_sauvegarde).total_seconds() > 60:
                note.sauver(t_de)
                derniere_sauvegarde = datetime.now()
    finally:
        note.sauver(t_de)
        nav.fermer()
        cv2.destroyAllWindows()
    afficher(f"annotation sauvegardée : {chemin}")
    return chemin
