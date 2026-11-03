"""Tests N0 (trajectoires synthétiques) des indices d'examen des paires suspectes."""

from passages.crossing import Ligne
from passages.paires import indice_categorie, indices_paire, indices_piste

LIGNE = Ligne(id="l", p1=(0.0, 500.0), p2=(1000.0, 500.0),
              sens={"gauche_vers_droite": "entree", "droite_vers_gauche": "sortie"})


def traj(points, t0=0):
    return [{"t_ms": t0 + 100 * k, "num_image": 3 * k, "boite": [x - 20, y - 200, x + 20, y]} for k, (x, y) in enumerate(points)]


def fr(t, geo="gauche_vers_droite"):
    return {"t_ms": t, "sens_geometrique": geo}


def test_fragmentation_reprise_proche_sans_recouvrement():
    a = traj([(100, 450), (110, 480), (120, 510)])
    b = traj([(125, 530), (130, 560)], t0=500)
    ip = indices_paire(a, b)
    assert ip["recouvrement_images"] == 0 and ip["ecart_fin_debut_ms"] == 300
    assert indice_categorie(ip, indices_piste(a, LIGNE, [fr(200)]), indices_piste(b, LIGNE, [])) == "fragmentation_du_suivi"


def test_meme_personne_deux_pistes_simultanees():
    a = traj([(100, 450), (110, 520)])
    b = traj([(102, 452), (111, 521)])
    ip = indices_paire(a, b)
    assert indice_categorie(ip, indices_piste(a, LIGNE, [fr(100)]), indices_piste(b, LIGNE, [fr(100)])) == "meme_personne_deux_pistes"


def test_oscillation_faible_excursion():
    a = traj([(100, 490), (100, 505), (100, 495), (100, 504), (100, 480)])
    b = traj([(400, 450), (400, 520), (400, 600), (400, 700), (400, 800)])
    ia = indices_piste(a, LIGNE, [fr(100), fr(200, "droite_vers_gauche"), fr(300)])
    ip = indices_paire(a, b)
    assert indice_categorie(ip, ia, indices_piste(b, LIGNE, [fr(100)])) == "oscillation_autour_de_la_ligne"


def test_personnes_differentes_eloignees():
    a = traj([(100, 450), (100, 550), (100, 650)])
    b = traj([(600, 450), (600, 550), (600, 650)])
    ip = indices_paire(a, b)
    assert indice_categorie(ip, indices_piste(a, LIGNE, [fr(100)]), indices_piste(b, LIGNE, [fr(100)])) == "personnes_differentes"
