"""Lecture, validation minimale et empreinte des configurations d'analyse."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

CHAMPS_OBLIGATOIRES = {
    "version_schema": int,
    "scenario": str,
    "video": dict,
    "lignes": list,
    "analyse": dict,
    "regle_passage": dict,
}


class ConfigInvalide(ValueError):
    pass


def empreinte(contenu: Any) -> str:
    canonique = json.dumps(contenu, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()


def sha256_fichier(chemin: str | Path, taille_bloc: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while bloc := f.read(taille_bloc):
            h.update(bloc)
    return h.hexdigest()


def charger(chemin: str | Path) -> tuple[dict, str]:
    with open(chemin, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    valider(cfg)
    return cfg, empreinte(cfg)


def valider(cfg: dict) -> None:
    if not isinstance(cfg, dict):
        raise ConfigInvalide("la configuration doit être un dictionnaire")
    for champ, type_attendu in CHAMPS_OBLIGATOIRES.items():
        if champ not in cfg:
            raise ConfigInvalide(f"champ obligatoire manquant : {champ}")
        if not isinstance(cfg[champ], type_attendu):
            raise ConfigInvalide(f"{champ} doit être de type {type_attendu.__name__}")
    if cfg["version_schema"] != 1:
        raise ConfigInvalide("version_schema non prise en charge (attendu : 1)")
    if cfg["scenario"] != "comptage_passages":
        raise ConfigInvalide("seul le scénario comptage_passages est pris en charge")
    for cle in ("chemin", "sha256"):
        if not cfg["video"].get(cle):
            raise ConfigInvalide(f"video.{cle} est obligatoire")
    if cfg["video"].get("mode_temps", "pts") not in ("pts", "rang_cadence_nominale"):
        raise ConfigInvalide("video.mode_temps : pts ou rang_cadence_nominale")
    if not cfg["lignes"]:
        raise ConfigInvalide("au moins une ligne est nécessaire")
    ids = set()
    for ligne in cfg["lignes"]:
        for cle in ("id", "p1", "p2", "sens"):
            if cle not in ligne:
                raise ConfigInvalide(f"ligne : champ {cle} manquant")
        if ligne["id"] in ids:
            raise ConfigInvalide(f"identifiant de ligne en double : {ligne['id']}")
        ids.add(ligne["id"])
        for p in (ligne["p1"], ligne["p2"]):
            if len(p) != 2 or not all(0.0 <= v <= 1.0 for v in p):
                raise ConfigInvalide(f"ligne {ligne['id']} : coordonnées normalisées attendues dans [0, 1]")
        if set(ligne["sens"]) != {"gauche_vers_droite", "droite_vers_gauche"}:
            raise ConfigInvalide(f"ligne {ligne['id']} : sens doit définir gauche_vers_droite et droite_vers_gauche")
    analyse = cfg["analyse"]
    for cle in ("cadence_analyse", "modele", "seuil_detection", "seuil_nms", "suivi"):
        if cle not in analyse:
            raise ConfigInvalide(f"analyse.{cle} est obligatoire")
    if analyse["cadence_analyse"] <= 0:
        raise ConfigInvalide("analyse.cadence_analyse doit être positive")
    if "maintien_ms" not in cfg["regle_passage"]:
        raise ConfigInvalide("regle_passage.maintien_ms est obligatoire")
