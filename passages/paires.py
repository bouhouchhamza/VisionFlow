"""Examen des paires « doublon probable » d'un run : indices de trajectoire, croisement avec la référence humaine.

Les catégories produites sont des **indices** à vérifier sur les planches d'images ; elles ne modifient ni le run ni la
référence. Les seuils ci-dessous servent à l'examen, ce ne sont pas des paramètres du pipeline.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

import passages
from passages import dessin
from passages.config import sha256_fichier
from passages.crossing import Ligne
from passages.evaluate import charger_reference, passages_reference
from passages.run import RACINE, charger_run, ecrire_json
from passages.versions import etat_git
from passages.video import format_temps, lire

FRAGMENTATION_ECART_MAX_MS = 1500
FRAGMENTATION_DISTANCE_MAX = 0.6
MEME_PERSONNE_IOU_MIN = 0.5
OSCILLATION_EXCURSION_MAX = 0.15


def iou(a: list[float], b: list[float]) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def ancrage(b: list[float]) -> tuple[float, float]:
    return (b[0] + b[2]) / 2, b[3]


def trajectoires(chemin_pistes: Path) -> dict[int, list[dict]]:
    pistes: dict[int, list[dict]] = defaultdict(list)
    with open(chemin_pistes, encoding="utf-8") as f:
        for ligne in f:
            rec = json.loads(ligne)
            for o in rec["objets"]:
                if o["piste"] >= 0:
                    pistes[o["piste"]].append({"t_ms": rec["t_ms"], "num_image": rec["num_image"], "boite": o["boite"]})
    return pistes


def indices_piste(traj: list[dict], ligne: Ligne, franchissements: list[dict]) -> dict:
    """Écarts signés à la ligne, normalisés par la hauteur de boîte, et excursion au-delà de chaque franchissement."""
    d = [ligne.distance_signee(*ancrage(p["boite"])) / max(1.0, p["boite"][3] - p["boite"][1]) for p in traj]
    excursions = []
    fr = sorted(franchissements, key=lambda f: f["t_ms"])
    for k, f in enumerate(fr):
        fin = fr[k + 1]["t_ms"] if k + 1 < len(fr) else traj[-1]["t_ms"]
        cote = 1 if f["sens_geometrique"] == "gauche_vers_droite" else -1
        apres = [cote * x for p, x in zip(traj, d) if f["t_ms"] <= p["t_ms"] <= fin]
        excursions.append(round(max(apres), 3) if apres else 0.0)
    return {"franchissements": len(fr), "excursions_relatives": excursions,
            "ecart_relatif_min": round(min(d), 3), "ecart_relatif_max": round(max(d), 3)}


def indices_paire(ta: list[dict], tb: list[dict]) -> dict:
    par_t_a = {p["t_ms"]: p for p in ta}
    communs = [(par_t_a[p["t_ms"]], p) for p in tb if p["t_ms"] in par_t_a]
    res = {"recouvrement_images": len(communs)}
    if communs:
        ious = [iou(a["boite"], b["boite"]) for a, b in communs]
        dist = [np.hypot(*np.subtract(ancrage(a["boite"]), ancrage(b["boite"]))) / max(1.0, a["boite"][3] - a["boite"][1])
                for a, b in communs]
        res.update({"iou_median": round(float(np.median(ious)), 3), "distance_relative_mediane": round(float(np.median(dist)), 3)})
    premiere, seconde = (ta, tb) if ta[0]["t_ms"] <= tb[0]["t_ms"] else (tb, ta)
    ecart = seconde[0]["t_ms"] - premiere[-1]["t_ms"]
    res["ecart_fin_debut_ms"] = ecart
    if ecart > 0:
        a, b = premiere[-1]["boite"], seconde[0]["boite"]
        res["distance_relative_reprise"] = round(float(np.hypot(*np.subtract(ancrage(a), ancrage(b))) / max(1.0, a[3] - a[1])), 3)
    return res


def indice_categorie(ip: dict, ia: dict, ib: dict) -> str:
    if ip["recouvrement_images"] == 0 and ip["ecart_fin_debut_ms"] <= FRAGMENTATION_ECART_MAX_MS \
            and ip.get("distance_relative_reprise", 9) <= FRAGMENTATION_DISTANCE_MAX:
        return "fragmentation_du_suivi"
    if ip["recouvrement_images"] and ip.get("iou_median", 0) >= MEME_PERSONNE_IOU_MIN:
        return "meme_personne_deux_pistes"
    oscille = [i for i in (ia, ib) if i["franchissements"] >= 2 and min(i["excursions_relatives"]) <= OSCILLATION_EXCURSION_MAX]
    if oscille:
        return "oscillation_autour_de_la_ligne"
    if ip["recouvrement_images"]:
        return "personnes_differentes"
    return "indetermine"


def examiner(dossier_run: str, chemin_reference: str | None, tolerance_ms: int = 1000, planches: bool = True,
             afficher=print) -> Path:
    d, manifeste, ev = charger_run(dossier_run)
    cfg = manifeste["config"]["contenu"]
    W, H = manifeste["video"]["largeur"], manifeste["video"]["hauteur"]
    lignes = {l["id"]: Ligne.depuis_config(l, W, H) for l in cfg["lignes"]}
    traj = trajectoires(d / "pistes.jsonl")
    fr_par_id = {f["id"]: f for f in ev["franchissements"]}
    fr_par_piste = defaultdict(list)
    for f in ev["franchissements"]:
        fr_par_piste[f["piste"]].append(f)
    ref_passages = None
    if chemin_reference:
        ref_doc = charger_reference(chemin_reference)
        if ref_doc["video"]["sha256"].upper() != manifeste["video"]["sha256"].upper():
            raise ValueError("référence et run sur des vidéos différentes")
        ref_passages = passages_reference(ref_doc, 0)
        ref_retours = {f["id"] for f in ref_doc["franchissements"] if f.get("retour_de")}

    paires = []
    for ida, idb in ev["doublons_probables"]:
        fa, fb = fr_par_id[ida], fr_par_id[idb]
        ligne = lignes[fa["ligne"]]
        ia = indices_piste(traj[fa["piste"]], ligne, fr_par_piste[fa["piste"]])
        ib = indices_piste(traj[fb["piste"]], ligne, fr_par_piste[fb["piste"]])
        ip = indices_paire(traj[fa["piste"]], traj[fb["piste"]])
        entree = {"franchissements": [ida, idb], "pistes": [fa["piste"], fb["piste"]], "direction": fa["direction"],
                  "t_ms": [fa["t_ms"], fb["t_ms"]], "indices_paire": ip, "indices_piste_a": ia, "indices_piste_b": ib,
                  "indice_categorie": indice_categorie(ip, ia, ib)}
        if ref_passages is not None:
            debut, fin = min(fa["t_ms"], fb["t_ms"]) - tolerance_ms, max(fa["t_ms"], fb["t_ms"]) + tolerance_ms
            proches = [p for p in ref_passages if p["ligne"] == fa["ligne"] and debut <= p["t_ms"] <= fin]
            meme_sens = [p for p in proches if p["direction"] == fa["direction"]]
            entree["reference"] = {"franchissements_meme_sens": len(meme_sens),
                                   "franchissements_sens_oppose": len(proches) - len(meme_sens),
                                   "retours_marques": sum(p["id"] in ref_retours for p in proches),
                                   "ids": [p["id"] for p in proches]}
            entree["lecture_reference"] = ("au_moins_deux_personnes" if len(meme_sens) >= 2 else
                                           "une_seule_personne" if len(meme_sens) == 1 else "aucun_franchissement_humain")
        paires.append(entree)

    dossier = d / "examens"
    dossier.mkdir(exist_ok=True)
    horodatage = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    if planches and paires:
        _planches(manifeste, cfg, traj, paires, lignes, dossier / f"{horodatage}_planches")
    sortie = dossier / f"{horodatage}_paires.json"
    ecrire_json(sortie, {
        "format": "examen_paires", "version_format": 1, "run_id": ev["run_id"],
        "cree_le_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "outil": {"passages": passages.__version__, **etat_git(RACINE)},
        "reference": {"chemin": str(Path(chemin_reference).as_posix()), "sha256": sha256_fichier(chemin_reference).upper()}
        if chemin_reference else None,
        "seuils_examen": {"fragmentation_ecart_max_ms": FRAGMENTATION_ECART_MAX_MS,
                          "fragmentation_distance_max": FRAGMENTATION_DISTANCE_MAX,
                          "meme_personne_iou_min": MEME_PERSONNE_IOU_MIN,
                          "oscillation_excursion_max": OSCILLATION_EXCURSION_MAX},
        "avertissement": "indices automatiques à vérifier visuellement ; ne modifient ni le run ni la référence",
        "paires": paires,
    })
    for p in paires:
        lecture = p.get("lecture_reference", "-")
        afficher(f"{p['franchissements'][0]}/{p['franchissements'][1]} pistes {p['pistes'][0]}/{p['pistes'][1]} "
                 f"{format_temps(p['t_ms'][0])} {p['indice_categorie']} | référence : {lecture}")
    afficher(f"examen : {sortie}")
    return sortie


def _planches(manifeste: dict, cfg: dict, traj: dict, paires: list[dict], lignes: dict, dossier: Path) -> None:
    """Pour chaque paire : 4 images (avant, deux franchissements, après) avec les deux trajectoires complètes."""
    dossier.mkdir(parents=True, exist_ok=True)
    instants = {}
    for k, p in enumerate(paires):
        t0, t1 = min(p["t_ms"]), max(p["t_ms"])
        for j, t in enumerate((t0 - 1000, p["t_ms"][0], p["t_ms"][1], t1 + 1000)):
            instants.setdefault(max(0, t), []).append((k, j))
    cibles = sorted(instants)
    vues: dict[tuple[int, int], np.ndarray] = {}
    i_cible = 0
    s = 0.5
    for image in lire(str(RACINE / cfg["video"]["chemin"]), mode=cfg["video"].get("mode_temps", "pts")):
        while i_cible < len(cibles) and image.t_ms >= cibles[i_cible]:
            bgr = cv2.resize(image.trame.to_ndarray(format="bgr24"), None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            for k, j in instants[cibles[i_cible]]:
                vues[(k, j)] = (bgr.copy(), image.t_ms, image.index)
            i_cible += 1
        if i_cible >= len(cibles):
            break
    couleurs = [dessin.CYAN, dessin.ORANGE]
    for k, p in enumerate(paires):
        cases = []
        for j in range(4):
            img, t_ms, idx = vues[(k, j)]
            for l in lignes.values():
                dessin.ligne(img, l, s, details=False)
            for c, piste in enumerate(p["pistes"]):
                pts = [(int(ancrage(q["boite"])[0] * s), int(q["boite"][3] * s)) for q in traj[piste]]
                for a, b in zip(pts, pts[1:]):
                    cv2.line(img, a, b, couleurs[c], 1, cv2.LINE_AA)
                for q in traj[piste]:
                    if q["t_ms"] == t_ms:
                        x1, y1, x2, y2 = (int(v * s) for v in q["boite"])
                        cv2.rectangle(img, (x1, y1), (x2, y2), couleurs[c], 2)
                        dessin.texte(img, f"#{piste}", (x1, max(12, y1 - 4)), 0.5, couleurs[c])
            dessin.texte(img, f"{format_temps(t_ms)} image {idx}", (8, 20), 0.55)
            cases.append(img)
        planche = np.vstack([np.hstack(cases[:2]), np.hstack(cases[2:])])
        dessin.texte(planche, f"{p['franchissements'][0]}/{p['franchissements'][1]}  pistes #{p['pistes'][0]} (cyan) "
                              f"#{p['pistes'][1]} (orange)  indice : {p['indice_categorie']}", (8, planche.shape[0] - 12), 0.6)
        cv2.imwrite(str(dossier / f"{k + 1:02d}_{p['franchissements'][0]}_{p['franchissements'][1]}.png"), planche)
