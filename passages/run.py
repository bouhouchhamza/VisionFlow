"""Exécution d'une analyse : un run immuable par appel."""

from __future__ import annotations

import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

from passages import config as cfgmod
from passages import versions
from passages.crossing import DetecteurFranchissements, Ligne, deriver_passages_machine, doublons_probables
from passages.detection import DetecteurYolox
from passages.video import BilanTemps, Echantillonneur, lire, metadonnees

RACINE = Path(__file__).resolve().parent.parent


def ecrire_json(chemin: Path, contenu: dict) -> None:
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(contenu, f, ensure_ascii=False, indent=2)
        f.write("\n")


def nouveau_run_id() -> str:
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"


def creer_traqueur(suivi: dict, cadence: float) -> ByteTrackTracker:
    return ByteTrackTracker(
        lost_track_buffer=int(suivi["lost_track_buffer"]),
        frame_rate=float(cadence),
        track_activation_threshold=float(suivi["track_activation_threshold"]),
        minimum_consecutive_frames=int(suivi["minimum_consecutive_frames"]),
        minimum_iou_threshold=float(suivi["minimum_iou_threshold"]),
        high_conf_det_threshold=float(suivi["high_conf_det_threshold"]),
    )


def analyser(chemin_config: str, dossier_runs: str = "runs", limite_s: float | None = None,
             threads: int | None = None, afficher=print) -> Path:
    cfg, cfg_sha = cfgmod.charger(chemin_config)
    sha_config = cfgmod.sha256_fichier(chemin_config).upper()
    etat_depart = versions.etat_git(RACINE)
    video = cfg["video"]
    analyse = cfg["analyse"]
    chemin_video = str(RACINE / video["chemin"])
    chemin_modele = str(RACINE / analyse["modele"]["chemin"])

    afficher("vérification des empreintes (vidéo, modèle)…")
    sha_video = cfgmod.sha256_fichier(chemin_video).upper()
    if sha_video != video["sha256"].upper():
        raise RuntimeError(f"empreinte vidéo différente de la configuration : {sha_video}")
    sha_modele = cfgmod.sha256_fichier(chemin_modele).upper()
    if sha_modele != analyse["modele"]["sha256"].upper():
        raise RuntimeError(f"empreinte du modèle différente de la configuration : {sha_modele}")

    run_id = nouveau_run_id()
    final = RACINE / dossier_runs / run_id
    tmp = final.with_name(run_id + ".tmp")
    tmp.mkdir(parents=True)
    meta = metadonnees(chemin_video)
    largeur, hauteur = meta["largeur"], meta["hauteur"]
    lignes = [Ligne.depuis_config(l, largeur, hauteur) for l in cfg["lignes"]]
    cadence = float(analyse["cadence_analyse"])
    detecteur = DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]), float(analyse["seuil_detection"]),
                               float(analyse["seuil_nms"]), threads)
    traqueur = creer_traqueur(analyse["suivi"], cadence)
    franchisseur = DetecteurFranchissements(lignes)
    echantillon = Echantillonneur(cadence)
    bilan = BilanTemps()

    debut_pistes: dict[int, int] = {}
    fin_pistes: dict[int, int] = {}
    chrono = {"decodage_s": 0.0, "conversion_s": 0.0, "detection_s": 0.0, "suivi_et_regle_s": 0.0}
    images_analysees = 0
    images_temps_reconstruit_analysees = 0
    dernier_t_ms = 0
    t_mur_debut = time.perf_counter()
    afficher(f"run {run_id} : analyse à {cadence:g} images/s de temps vidéo…")
    try:
        with open(tmp / "pistes.jsonl", "w", encoding="utf-8") as f_pistes:
            t0 = time.perf_counter()
            for image in lire(chemin_video, bilan, video.get("mode_temps", "pts")):
                t1 = time.perf_counter()
                chrono["decodage_s"] += t1 - t0
                if limite_s is not None and image.t_s > limite_s:
                    break
                dernier_t_ms = image.t_ms
                if not echantillon.garder(image.t_s):
                    t0 = time.perf_counter()
                    continue
                bgr = image.trame.to_ndarray(format="bgr24")
                t2 = time.perf_counter()
                boites, scores = detecteur.detecter(bgr)
                t3 = time.perf_counter()
                dets = sv.Detections(xyxy=boites.astype(np.float32), confidence=scores.astype(np.float32),
                                     class_id=np.zeros(len(scores), dtype=int))
                suivis = traqueur.update(dets, timestamp=image.t_s)
                objets = []
                for xyxy, conf, tid in zip(suivis.xyxy, suivis.confidence if suivis.confidence is not None else
                                           np.ones(len(suivis)), suivis.tracker_id):
                    tid = int(tid)
                    x1, y1, x2, y2 = (float(v) for v in xyxy)
                    objets.append({"piste": tid, "boite": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                                   "score": round(float(conf), 4)})
                    if tid < 0:
                        continue
                    debut_pistes.setdefault(tid, image.t_ms)
                    fin_pistes[tid] = image.t_ms
                    franchisseur.observer(tid, image.t_ms, image.index, (x1 + x2) / 2, y2, float(conf))
                t4 = time.perf_counter()
                chrono["conversion_s"] += t2 - t1
                chrono["detection_s"] += t3 - t2
                chrono["suivi_et_regle_s"] += t4 - t3
                images_analysees += 1
                images_temps_reconstruit_analysees += int(image.reconstruit)
                f_pistes.write(json.dumps({"num_image": image.index, "t_ms": image.t_ms, "pts": image.pts,
                                           "temps_reconstruit": image.reconstruit, "detections_brutes": len(scores),
                                           "objets": objets}, ensure_ascii=False) + "\n")
                if images_analysees % 300 == 0:
                    ecoule = time.perf_counter() - t_mur_debut
                    afficher(f"  t vidéo {image.t_s:7.1f} s | {images_analysees} images analysées | "
                             f"{image.t_s / ecoule:.2f} s vidéo / s calcul")
                t0 = time.perf_counter()
        duree_mur = time.perf_counter() - t_mur_debut

        maintien = int(cfg["regle_passage"]["maintien_ms"])
        franchissements = [f.en_dict() for f in franchisseur.franchissements]
        passages = deriver_passages_machine(franchissements, fin_pistes, dernier_t_ms, 1000 / cadence, maintien)
        fenetre_doublon = int(cfg["regle_passage"].get("fenetre_doublon_ms", 1500))
        evenements = {
            "format": "evenements_passages",
            "version_format": 1,
            "run_id": run_id,
            "video": {"sha256": sha_video, "nom_fichier": Path(chemin_video).name},
            "temps": {
                "mode": bilan.mode,
                "reference": ("PTS du conteneur ramenés à 0 sur la première image, en ms" if bilan.mode == "pts" else
                              "rang d'affichage × durée nominale d'image, en ms (temps reconstruit)"),
                "debut_declare": video.get("debut_declare"),
                "source_debut_declare": video.get("source_debut"),
                "images_analysees_temps_reconstruit": images_temps_reconstruit_analysees,
                "fin_analyse_ms": dernier_t_ms,
            },
            "nature": "observations_brutes_machine",
            "franchissements": franchissements,
            "regle_passage": {"maintien_ms": maintien, "statut_parametre": "hypothese",
                              "fenetre_doublon_ms": fenetre_doublon},
            "passages_derives": passages,
            "doublons_probables": [list(p) for p in doublons_probables(passages, fenetre_doublon)],
            "pistes": {str(k): {"debut_ms": debut_pistes[k], "fin_ms": fin_pistes[k]} for k in sorted(debut_pistes)},
        }
        ecrire_json(tmp / "evenements.json", evenements)

        duree_video_s = dernier_t_ms / 1000
        manifeste = {
            "format": "manifeste_run",
            "version_format": 1,
            "run_id": run_id,
            "cree_le_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "commande": [Path(sys.executable).name, "-m", "passages", *sys.argv[1:]],
            "config": {"chemin": str(Path(chemin_config).as_posix()), "sha256_canonique": cfg_sha,
                       "sha256_fichier": sha_config, "contenu": cfg},
            "video": {"sha256": sha_video, "verifiee": True, **meta, "bilan_temps": bilan.en_dict()},
            "modele": {"chemin": analyse["modele"]["chemin"], "sha256": sha_modele, "verifie": True},
            "versions": {**versions.relever(RACINE), **etat_depart},
            "execution": {
                "limite_s": limite_s,
                "threads_onnxruntime": threads or "defaut",
                "images_decodees": bilan.images,
                "images_analysees": images_analysees,
                "duree_video_analysee_s": duree_video_s,
                "duree_calcul_s": round(duree_mur, 3),
                "chronometrage_s": {k: round(v, 3) for k, v in chrono.items()},
                "vitesse_s_video_par_s_calcul": round(duree_video_s / duree_mur, 3) if duree_mur else None,
                "nature_mesure": "temps mural sur cette machine, une seule vidéo, aucun autre run simultané déclaré",
            },
            "resultats": {
                "pistes_confirmees": len(debut_pistes),
                "franchissements_bruts": len(franchissements),
                "passages_retenus": sum(p["statut"] == "passage" for p in passages),
            },
        }
        ecrire_json(tmp / "manifest.json", manifeste)
        tmp.rename(final)
    except BaseException:
        afficher(f"échec : le dossier incomplet {tmp} est conservé pour diagnostic, il n'est pas un run valide")
        raise
    afficher(f"run terminé : {final}")
    return final


def charger_run(dossier: str | Path) -> tuple[Path, dict, dict]:
    d = Path(dossier)
    if d.name.endswith(".tmp"):
        raise RuntimeError("dossier .tmp : run incomplet")
    with open(d / "manifest.json", encoding="utf-8") as f:
        manifeste = json.load(f)
    with open(d / "evenements.json", encoding="utf-8") as f:
        evenements = json.load(f)
    return d, manifeste, evenements
