"""Point d'entrée : `python -m passages <commande>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2


def vue_ligne(chemin_config: str, t_s: float, sortie: str) -> Path:
    from passages import dessin
    from passages.config import charger
    from passages.crossing import Ligne
    from passages.run import RACINE
    from passages.video import format_temps, lire

    cfg, _ = charger(chemin_config)
    image = None
    for im in lire(str(RACINE / cfg["video"]["chemin"]), mode=cfg["video"].get("mode_temps", "pts")):
        if im.t_s >= t_s:
            image = im
            break
    if image is None:
        raise ValueError("instant au-delà de la fin de la vidéo")
    img = image.trame.to_ndarray(format="bgr24")
    H, W = img.shape[:2]
    for k in range(1, 10):
        cv2.line(img, (W * k // 10, 0), (W * k // 10, H), dessin.GRIS, 1)
        cv2.line(img, (0, H * k // 10), (W, H * k // 10), dessin.GRIS, 1)
        dessin.texte(img, f"{k / 10:.1f}", (W * k // 10 + 3, 18), 0.5, dessin.GRIS)
        dessin.texte(img, f"{k / 10:.1f}", (3, H * k // 10 - 4), 0.5, dessin.GRIS)
    for l in cfg["lignes"]:
        lg = Ligne.depuis_config(l, W, H)
        dessin.ligne(img, lg, 1.0)
        dessin.texte(img, f"ligne '{lg.id}'  p1={l['p1']}  p2={l['p2']}", (20, H - 50), 0.8, dessin.JAUNE, 2)
    dessin.texte(img, f"t video {format_temps(image.t_ms)}  image {image.index}", (20, H - 20), 0.8, dessin.BLANC, 2)
    chemin = Path(sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(chemin), img)
    print(f"vue de la ligne : {chemin}")
    return chemin


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="passages", description="Prototype de comptage de passages (scénario A).")
    sp = p.add_subparsers(dest="commande", required=True)

    a = sp.add_parser("analyser", help="vidéo -> détection -> suivi -> franchissements -> run horodaté")
    a.add_argument("--config", required=True)
    a.add_argument("--runs", default="runs")
    a.add_argument("--limite-s", type=float, help="n'analyser que les N premières secondes (essai)")
    a.add_argument("--threads", type=int, help="threads ONNX Runtime (défaut : choix de la bibliothèque)")

    r = sp.add_parser("rendre", help="vidéo annotée d'un run")
    r.add_argument("--run", required=True)
    r.add_argument("--largeur", type=int, default=960)

    v = sp.add_parser("vue-ligne", help="image de la ligne, des côtés et du sens d'entrée")
    v.add_argument("--config", required=True)
    v.add_argument("--t", type=float, default=0.0, help="instant vidéo en secondes")
    v.add_argument("--sortie", required=True)

    n = sp.add_parser("annoter", help="annotation manuelle (sans détecteur)")
    n.add_argument("--config", required=True)
    n.add_argument("--annotateur", required=True)
    n.add_argument("--passe", type=int, default=1)
    n.add_argument("--echantillon", required=True, help="identifiant d'échantillon E0, ex. S1")
    n.add_argument("--sortie")
    n.add_argument("--reprendre", action="store_true")
    n.add_argument("--largeur", type=int, default=1280)

    c = sp.add_parser("comparer", help="rapport de comparaison run / annotation")
    c.add_argument("--run", required=True)
    c.add_argument("--reference", required=True)
    c.add_argument("--maintien-ms", type=int)
    c.add_argument("--tolerance-ms", type=int, default=1000)

    e = sp.add_parser("examiner-paires", help="indices sur les paires « doublon probable » d'un run")
    e.add_argument("--run", required=True)
    e.add_argument("--reference")
    e.add_argument("--tolerance-ms", type=int, default=1000)
    e.add_argument("--sans-planches", action="store_true")

    nr = sp.add_parser("comparer-runs", help="non-régression technique : un run candidat face à un run de référence")
    nr.add_argument("--reference", required=True)
    nr.add_argument("--candidat", required=True)
    nr.add_argument("--jusqu-a-ms", type=int, help="ne comparer que les images et franchissements jusqu'à cet instant")
    nr.add_argument("--sortie", help="dossier des rapports (défaut : runs/non_regression/comparaisons)")

    args = p.parse_args(argv)
    if args.commande == "analyser":
        from passages.run import analyser
        analyser(args.config, args.runs, args.limite_s, args.threads)
    elif args.commande == "rendre":
        from passages.render import rendre
        rendre(args.run, args.largeur)
    elif args.commande == "vue-ligne":
        vue_ligne(args.config, args.t, args.sortie)
    elif args.commande == "annoter":
        from passages.annotate import annoter
        annoter(args.config, args.annotateur, args.passe, args.echantillon, args.sortie, args.reprendre, args.largeur)
    elif args.commande == "comparer":
        from passages.evaluate import comparer
        comparer(args.run, args.reference, args.maintien_ms, args.tolerance_ms)
    elif args.commande == "examiner-paires":
        from passages.paires import examiner
        examiner(args.run, args.reference, args.tolerance_ms, not args.sans_planches)
    elif args.commande == "comparer-runs":
        from passages.non_regression import IDENTIQUE, comparer_et_ecrire
        res = comparer_et_ecrire(args.reference, args.candidat, args.jusqu_a_ms, args.sortie)
        return 0 if res["verdict"] == IDENTIQUE else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
