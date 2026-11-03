"""Contrôle E3 du lecteur d'annotation : une image obtenue par saut doit être identique, au pixel près, à l'image de
même rang obtenue par décodage séquentiel. Usage : python experiments/E3/controle_lecteur.py --config <yaml> [--n 40]
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from passages.annotate import Navigateur, table_images  # noqa: E402
from passages.config import charger, sha256_fichier  # noqa: E402
from passages.run import RACINE  # noqa: E402
from passages.video import lire  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--graine", type=int, default=42)
    a = p.parse_args()
    cfg, _ = charger(a.config)
    chemin = str(RACINE / cfg["video"]["chemin"])
    mode = cfg["video"].get("mode_temps", "pts")
    sha = sha256_fichier(chemin).upper()
    table = table_images(chemin, sha, mode)
    n = len(table["t_ms"])
    rng = random.Random(a.graine)
    cibles = rng.sample(range(n), a.n) + [0, n - 1] + [c[1] for c in table["cles"][1:4]] + [c[1] - 1 for c in table["cles"][1:4]]
    voulues = set(cibles)
    reference = {}
    largeur = None
    for im in lire(chemin, mode=mode):
        if im.index in voulues:
            img = im.trame.to_ndarray(format="bgr24")
            largeur = img.shape[1]
            reference[im.index] = hashlib.md5(img.tobytes()).hexdigest()
    nav = Navigateur(chemin, table["cles"], largeur, taille_cache=1)
    ecarts = []
    for i in cibles:
        nav.cache.clear()
        obtenu = hashlib.md5(nav.image(i).tobytes()).hexdigest()
        if obtenu != reference[i]:
            ecarts.append(i)
    nav.fermer()
    print(f"video={Path(chemin).name} mode={mode} images={n} sauts_testes={len(cibles)} "
          f"identiques={len(cibles) - len(ecarts)} differents={len(ecarts)} {ecarts[:20]}")
    return 1 if ecarts else 0


if __name__ == "__main__":
    raise SystemExit(main())
