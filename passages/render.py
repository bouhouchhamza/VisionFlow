"""Vidéo annotée d'un run (produit dérivé, rangé dans `<run>/rendus/`, le run lui-même n'est pas modifié)."""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import cv2

from passages import dessin
from passages.config import sha256_fichier
from passages.crossing import Ligne
from passages.run import RACINE, charger_run, ecrire_json
from passages.video import format_temps, lire
from passages.versions import version_ffmpeg

DUREE_FLASH_MS = 1500


def rendre(dossier_run: str, largeur: int = 960, afficher=print) -> Path:
    d, manifeste, ev = charger_run(dossier_run)
    cfg = manifeste["config"]["contenu"]
    chemin_video = str(RACINE / cfg["video"]["chemin"])
    if sha256_fichier(chemin_video).upper() != manifeste["video"]["sha256"]:
        raise RuntimeError("la vidéo ne correspond pas à celle du run")
    W, H = manifeste["video"]["largeur"], manifeste["video"]["hauteur"]
    s = largeur / W
    w_out, h_out = int(round(W * s / 2) * 2), int(round(H * s / 2) * 2)
    lignes = [Ligne.depuis_config(l, W, H) for l in cfg["lignes"]]
    cadence = float(cfg["analyse"]["cadence_analyse"])
    maintien = ev["regle_passage"]["maintien_ms"]

    pistes = {}
    with open(d / "pistes.jsonl", encoding="utf-8") as f:
        for ligne_json in f:
            rec = json.loads(ligne_json)
            pistes[rec["num_image"]] = rec
    statut = {p["franchissement"]: p["statut"] for p in ev["passages_derives"]}
    par_image = defaultdict(list)
    for fr in ev["franchissements"]:
        par_image[fr["num_image"]].append(fr)
    retenus = sorted((p for p in ev["passages_derives"] if p["statut"] == "passage"), key=lambda p: p["t_ms"])

    dossier = d / "rendus"
    dossier.mkdir(exist_ok=True)
    sortie = dossier / "video_annotee.mp4"
    tmp = dossier / "video_annotee.tmp.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{w_out}x{h_out}", "-r", f"{cadence:g}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "23", "-pix_fmt", "yuv420p", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    traces: dict[int, deque] = defaultdict(lambda: deque(maxlen=15))
    flashs: list[tuple[int, dict]] = []
    ecrites = 0
    afficher(f"rendu de {len(pistes)} images analysées vers {sortie}…")
    try:
        for image in lire(chemin_video, mode=cfg["video"].get("mode_temps", "pts")):
            rec = pistes.get(image.index)
            if rec is None:
                if image.index > max(pistes):
                    break
                continue
            img = cv2.resize(image.trame.to_ndarray(format="bgr24"), (w_out, h_out), interpolation=cv2.INTER_AREA)
            for l in lignes:
                dessin.ligne(img, l, s, details=False)
            for o in rec["objets"]:
                x1, y1, x2, y2 = (int(v * s) for v in o["boite"])
                if o["piste"] < 0:
                    cv2.rectangle(img, (x1, y1), (x2, y2), dessin.GRIS, 1)
                    continue
                traces[o["piste"]].append((int((x1 + x2) / 2), y2))
                cv2.rectangle(img, (x1, y1), (x2, y2), dessin.CYAN, 1)
                dessin.texte(img, f"#{o['piste']}", (x1, max(12, y1 - 4)), 0.45, dessin.CYAN)
                pts = list(traces[o["piste"]])
                for a, b in zip(pts, pts[1:]):
                    cv2.line(img, a, b, dessin.CYAN, 1, cv2.LINE_AA)
                cv2.circle(img, pts[-1], 3, dessin.JAUNE, -1)
            for fr in par_image.get(image.index, []):
                flashs.append((image.t_ms + DUREE_FLASH_MS, fr))
            flashs = [(fin, fr) for fin, fr in flashs if fin >= image.t_ms]
            for k, (_, fr) in enumerate(flashs):
                st = statut.get(fr["id"], "?")
                couleur = dessin.VERT if st == "passage" else dessin.ORANGE
                x, y = int(fr["point"][0] * s), int(fr["point"][1] * s)
                cv2.circle(img, (x, y), 14, couleur, 2)
                dessin.texte(img, f"{fr['direction']} {fr['id']} #{fr['piste']} [{st}]", (10, h_out - 40 - 20 * k), 0.5, couleur)
            n_e = sum(1 for p in retenus if p["t_ms"] <= image.t_ms and p["direction"] == "entree")
            n_s = sum(1 for p in retenus if p["t_ms"] <= image.t_ms and p["direction"] == "sortie")
            dessin.texte(img, f"t video {format_temps(image.t_ms)}  image {image.index}", (10, 22), 0.6)
            dessin.texte(img, f"passages retenus (maintien {maintien} ms, hypothese) : entrees {n_e}  sorties {n_s}", (10, 46), 0.5)
            dessin.texte(img, f"run {ev['run_id']} - observations machine, non validees", (10, h_out - 12), 0.45, dessin.GRIS)
            proc.stdin.write(img.tobytes())
            ecrites += 1
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg a échoué (code {code})")
    tmp.replace(sortie)
    ecrire_json(dossier / "rendu.json", {
        "format": "rendu_video",
        "run_id": ev["run_id"],
        "cree_le_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fichier": sortie.name,
        "sha256": sha256_fichier(sortie).upper(),
        "images": ecrites,
        "cadence_sortie": cadence,
        "largeur": w_out,
        "hauteur": h_out,
        "encodeur": version_ffmpeg(),
        "remarque": "Superposition des observations brutes du run ; la cadence de sortie est la cadence d'analyse.",
    })
    afficher(f"vidéo annotée : {sortie} ({ecrites} images)")
    return sortie
