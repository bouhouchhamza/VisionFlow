"""Tests N0 du décodage de YOLOX (étape 2 de `docs/CONCEPTION_MULTICLASSE.md`).

Les sorties de modèle sont **synthétiques** (tableaux (8400, 85) fabriqués, session ONNX Runtime simulée), sauf mention
contraire. L'oracle est une copie figée du décodage `person` de `passages/detection.py` au commit `878f08f` : il sert de
référence d'équivalence au bit près et ne doit pas être modifié.
"""

import hashlib
from types import SimpleNamespace

import numpy as np
import pytest

from passages import config as cfgmod
from passages import detection
from passages.detecteur import AdaptateurYolox, creer_detecteur
from passages.detection import COCO_CLASSES, COLONNES_SORTIE, DetecteurYolox, indices_classes
from passages.run import RACINE

MODELE = RACINE / "models" / "yolox_s.onnx"
CONFIG_S1 = RACINE / "configs" / "s1_g420.yaml"
TAILLE = (640, 640)
SEUIL, SEUIL_NMS = 0.1, 0.45
RATIO_S1 = min(640 / 1072, 640 / 1920)
GRAINES = range(20)


# Oracle figé : `decoder` et `nms` de passages/detection.py au commit 878f08f. Ne pas modifier.

def _grilles_reference(taille):
    grilles, pas = [], []
    for stride in (8, 16, 32):
        h, w = taille[0] // stride, taille[1] // stride
        xv, yv = np.meshgrid(np.arange(w), np.arange(h))
        grilles.append(np.stack((xv, yv), 2).reshape(-1, 2))
        pas.append(np.full((h * w, 1), stride))
    return np.concatenate(grilles).astype(np.float32), np.concatenate(pas).astype(np.float32)


GRILLES, PAS = _grilles_reference(TAILLE)


def nms_reference(boites, scores, seuil):
    x1, y1, x2, y2 = boites.T
    aires = (x2 - x1 + 1) * (y2 - y1 + 1)
    ordre = scores.argsort()[::-1]
    garde = []
    while ordre.size:
        i = ordre[0]
        garde.append(i)
        xx1 = np.maximum(x1[i], x1[ordre[1:]])
        yy1 = np.maximum(y1[i], y1[ordre[1:]])
        xx2 = np.minimum(x2[i], x2[ordre[1:]])
        yy2 = np.minimum(y2[i], y2[ordre[1:]])
        inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
        iou = inter / (aires[i] + aires[ordre[1:]] - inter)
        ordre = ordre[np.where(iou <= seuil)[0] + 1]
    return np.array(garde, dtype=np.int64)


def decoder_reference(sortie, ratio, seuil=SEUIL, seuil_nms=SEUIL_NMS):
    pred = sortie.copy()
    pred[:, :2] = (pred[:, :2] + GRILLES) * PAS
    pred[:, 2:4] = np.exp(pred[:, 2:4]) * PAS
    scores = pred[:, 4] * pred[:, 5 + 0]
    garde = scores > seuil
    pred, scores = pred[garde], scores[garde]
    if not len(scores):
        return np.zeros((0, 4), np.float32), np.zeros((0,), np.float32)
    boites = np.empty((len(pred), 4), np.float32)
    boites[:, 0] = pred[:, 0] - pred[:, 2] / 2
    boites[:, 1] = pred[:, 1] - pred[:, 3] / 2
    boites[:, 2] = pred[:, 0] + pred[:, 2] / 2
    boites[:, 3] = pred[:, 1] + pred[:, 3] / 2
    boites /= ratio
    retenus = nms_reference(boites, scores, seuil_nms)
    return boites[retenus], scores[retenus]


# Outils de test

class FausseSession:
    """Session ONNX Runtime simulée : formes d'entrée et de sortie déclarées, sortie fixée (synthétique)."""

    def __init__(self, colonnes=85, sortie=None):
        self.colonnes, self.sortie, self.appels_run = colonnes, sortie, 0

    def get_inputs(self):
        return [SimpleNamespace(name="images", shape=[1, 3, *TAILLE])]

    def get_outputs(self):
        return [SimpleNamespace(name="output", shape=[1, 8400, self.colonnes])]

    def run(self, noms, flux):
        self.appels_run += 1
        return [self.sortie[None]]


@pytest.fixture
def session(monkeypatch):
    fausse = FausseSession()
    monkeypatch.setattr(detection.ort, "InferenceSession", lambda *a, **k: fausse)
    return fausse


def yolox(**options):
    return DetecteurYolox("modele_simule.onnx", TAILLE, SEUIL, SEUIL_NMS, None, **options)


def sortie_aleatoire(graine):
    """Sortie synthétique : boîtes plausibles, scores répartis autour du seuil ; ex aequo nombreux si graine impaire."""
    rng = np.random.default_rng(graine)
    s = np.empty((8400, 85), np.float32)
    s[:, :2] = rng.uniform(-0.5, 1.5, (8400, 2))
    s[:, 2:4] = rng.uniform(0.0, 3.0, (8400, 2))
    s[:, 4] = rng.uniform(0.0, 1.0, 8400)
    s[:, 5:] = rng.uniform(0.0, 0.3, (8400, 80))
    if graine % 2:
        s[:, 4:] = np.round(s[:, 4:] * 16) / 16
    return s


def identiques(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()


@pytest.mark.parametrize("graine", GRAINES)
def test_oracle_egal_decodeur(session, graine):
    """T1 : l'oracle reproduit `decoder` au bit près, ordre compris (écrit et vérifié sur le code non modifié)."""
    sortie = sortie_aleatoire(graine)
    attendu = decoder_reference(sortie, RATIO_S1)
    obtenu = yolox().decoder(sortie, RATIO_S1)[:2]
    assert len(attendu[0]) > 0
    for a, o in zip(attendu, obtenu):
        assert identiques(a, o)


def sortie_vide():
    """Sortie synthétique sans objet : objectness nulle partout, donc aucun score au-dessus du seuil."""
    return np.zeros((8400, 85), np.float32)


def placer(s, ancre, cx, cy, w, h, objectness, **probas):
    """Écrit à l'ancre les valeurs brutes qui décodent la boîte (cx, cy, w, h), en pixels de l'entrée 640."""
    gx, gy = GRILLES[ancre]
    pas = PAS[ancre, 0]
    s[ancre, 0], s[ancre, 1] = cx / pas - gx, cy / pas - gy
    s[ancre, 2], s[ancre, 3] = np.log(w / pas), np.log(h / pas)
    s[ancre, 4] = objectness
    for nom, p in probas.items():
        s[ancre, 5 + COCO_CLASSES.index(nom)] = p
    return s


# Équivalence du mode `person` (défaut)

@pytest.mark.parametrize("graine", GRAINES)
def test_person_bit_a_bit(session, graine):
    """T2 : classes par défaut, boîtes et scores égaux à l'oracle au bit près ; indices nuls en int64."""
    sortie = sortie_aleatoire(graine)
    boites, scores, ids = yolox().decoder(sortie, RATIO_S1)
    b_ref, s_ref = decoder_reference(sortie, RATIO_S1)
    assert identiques(boites, b_ref) and identiques(scores, s_ref)
    assert ids.dtype == np.int64 and ids.shape == scores.shape and not ids.any()


def test_person_ex_aequo(session):
    """T3 : 40 boîtes chevauchantes de score identique ; égal à l'oracle, et même résultat sur 10 appels."""
    s = sortie_vide()
    for j in range(40):
        placer(s, 1000 + j, 100 + 7 * j, 200, 60, 120, 1.0, person=0.5)
    b_ref, s_ref = decoder_reference(s, RATIO_S1)
    assert 1 < len(s_ref) < 40
    det = yolox()
    for _ in range(10):
        boites, scores, _ids = det.decoder(s, RATIO_S1)
        assert identiques(boites, b_ref) and identiques(scores, s_ref)


def test_seuil_exactement_0_1(session):
    """T4 : un score égal à float32(0,1) est exclu (comparaison stricte, en float32) ; un cran au-dessus est gardé."""
    pile = np.float32(0.1)
    dessus = np.nextafter(pile, np.float32(1))
    s = sortie_vide()
    placer(s, 100, 100, 100, 50, 50, 1.0, person=pile)
    placer(s, 5000, 500, 500, 50, 50, 1.0, person=dessus)
    boites, scores, _ids = yolox().decoder(s, RATIO_S1)
    assert scores.tolist() == [float(dessus)]
    b_ref, s_ref = decoder_reference(s, RATIO_S1)
    assert identiques(boites, b_ref) and identiques(scores, s_ref)


def test_person_non_dominante(session):
    """T5 : à une ancre où `car` domine, la personne est gardée (multi-étiquette, pas d'argmax)."""
    s = placer(sortie_vide(), 100, 100, 100, 50, 50, 1.0, car=0.9, person=0.3)
    _b, scores, ids = yolox().decoder(s, RATIO_S1)
    assert ids.tolist() == [0] and scores.tolist() == [float(np.float32(0.3))]


@pytest.mark.parametrize("decalage, attendues", [(26, 2), (18, 1)])
def test_chevauchement_autour_de_0_45(session, decalage, attendues):
    """T6 : deux personnes d'IoU d'environ 0,40 (gardées) puis 0,54 (une supprimée), comme l'oracle."""
    s = sortie_vide()
    placer(s, 100, 200, 200, 60, 60, 0.8, person=1.0)
    placer(s, 101, 200 + decalage, 200, 60, 60, 0.7, person=1.0)
    boites, scores, _ids = yolox().decoder(s, RATIO_S1)
    b_ref, s_ref = decoder_reference(s, RATIO_S1)
    assert len(scores) == attendues
    assert identiques(boites, b_ref) and identiques(scores, s_ref)


def test_aucune_detection(session):
    """T7 : tableaux vides de formes (0, 4), (0,), (0,) et de types float32, float32, int64."""
    boites, scores, ids = yolox(classes=(0, 2)).decoder(sortie_vide(), RATIO_S1)
    assert boites.shape == (0, 4) and boites.dtype == np.float32
    assert scores.shape == (0,) and scores.dtype == np.float32
    assert ids.shape == (0,) and ids.dtype == np.int64


def test_classe_non_demandee_absente(session):
    """T8 : une voiture très bien notée n'apparaît pas en mode `person`."""
    s = placer(sortie_vide(), 100, 100, 100, 50, 50, 1.0, car=0.99)
    boites, _s, _i = yolox().decoder(s, RATIO_S1)
    assert len(boites) == 0


def test_bornage_apres_nms(session):
    """T9 : `detecter` borne les boîtes à l'image après la NMS, comme l'oracle suivi du bornage."""
    s = sortie_vide()
    placer(s, 0, 5, 5, 100, 100, 1.0, person=0.9)
    placer(s, 6399, 630, 630, 100, 100, 1.0, person=0.8)
    session.sortie = s
    img = np.zeros((1072, 1920, 3), np.uint8)
    boites, scores, ids = yolox().detecter(img)
    b_ref, s_ref = decoder_reference(s, RATIO_S1)
    assert (b_ref < 0).any() and (b_ref[:, 2] > 1919).any()
    b_ref[:, [0, 2]] = np.clip(b_ref[:, [0, 2]], 0, 1919)
    b_ref[:, [1, 3]] = np.clip(b_ref[:, [1, 3]], 0, 1071)
    assert identiques(boites, b_ref) and identiques(scores, s_ref) and not ids.any()


def test_s1_premiere_image_oracle():
    """T10 : sortie réelle du modèle sur la première image de S1 (réglage) ; décodage égal à l'oracle au bit près."""
    from passages.video import lire

    cfg, _ = cfgmod.charger(str(CONFIG_S1))
    video = RACINE / cfg["video"]["chemin"]
    if not (MODELE.exists() and video.exists()):
        pytest.skip("modèle ou vidéo S1 hors git absent")
    img = next(iter(lire(str(video), mode=cfg["video"]["mode_temps"]))).trame.to_ndarray(format="bgr24")
    det = DetecteurYolox(str(MODELE), TAILLE, SEUIL, SEUIL_NMS, 1)
    entree, ratio = det.pretraiter(img)
    sortie = det.session.run(None, {det.entree: entree})[0][0]
    boites, scores, ids = det.decoder(sortie, ratio)
    b_ref, s_ref = decoder_reference(sortie, ratio)
    assert len(s_ref) > 0
    assert identiques(boites, b_ref) and identiques(scores, s_ref) and not ids.any()


# Vocabulaire, plusieurs classes

def test_vocabulaire_coco():
    """T11 : 80 noms uniques, indices du tag 0.1.1rc0, empreinte de la liste figée."""
    assert len(COCO_CLASSES) == len(set(COCO_CLASSES)) == 80 and COLONNES_SORTIE == 85
    attendus = {"person": 0, "bicycle": 1, "car": 2, "motorcycle": 3, "bus": 5, "truck": 7, "boat": 8}
    assert {n: COCO_CLASSES.index(n) for n in attendus} == attendus
    empreinte = hashlib.sha256("\n".join(COCO_CLASSES).encode("utf-8")).hexdigest()
    assert empreinte == "d7654b26101572841ed1cd80aa03aa60e35f1b8acb4aea6906c4066886f16e07"
    assert indices_classes(["truck", "person", "car"]) == (0, 2, 7)


def test_filtrage_par_classe(session):
    """T12 : seules les classes demandées sortent."""
    s = sortie_vide()
    placer(s, 100, 100, 100, 50, 50, 1.0, person=0.8)
    placer(s, 3000, 300, 300, 50, 50, 1.0, car=0.7)
    placer(s, 6000, 500, 500, 50, 50, 1.0, truck=0.9)
    _b, _s, ids = yolox(classes=indices_classes(["person", "car"])).decoder(s, RATIO_S1)
    assert ids.tolist() == [0, 2]


def test_personne_et_voiture_chevauchantes(session):
    """T13 : NMS par classe ; une personne et une voiture qui se chevauchent survivent toutes deux."""
    s = sortie_vide()
    placer(s, 100, 100, 100, 60, 120, 1.0, person=0.8)
    placer(s, 101, 105, 100, 60, 120, 1.0, car=0.7)
    _b, _s, ids = yolox(classes=(0, 2)).decoder(s, RATIO_S1)
    assert ids.tolist() == [0, 2]
    deux_personnes = placer(s.copy(), 101, 105, 100, 60, 120, 1.0, person=0.7)
    assert len(yolox().decoder(deux_personnes, RATIO_S1)[0]) == 1


def test_meme_ancre_deux_classes(session):
    """T14 : une ancre au-dessus du seuil pour person et car donne deux détections de boîtes identiques."""
    s = placer(sortie_vide(), 100, 100, 100, 50, 50, 1.0, person=0.9, car=0.8)
    boites, scores, ids = yolox(classes=(0, 2)).decoder(s, RATIO_S1)
    assert ids.tolist() == [0, 2] and identiques(boites[0], boites[1])
    assert scores.tolist() == [float(np.float32(0.9)), float(np.float32(0.8))]


def test_doublon_car_truck_documente(session):
    """T15 : doublon connu (familles reportées) : même ancre car 0,6 et truck 0,7, deux détections."""
    s = placer(sortie_vide(), 100, 100, 100, 50, 50, 1.0, car=0.6, truck=0.7)
    boites, _s, ids = yolox(classes=(2, 7)).decoder(s, RATIO_S1)
    assert ids.tolist() == [2, 7] and identiques(boites[0], boites[1])


@pytest.mark.parametrize("graine", range(5))
def test_ordre_stable(session, graine):
    """T16 : l'ordre des classes demandées est sans effet ; sortie par classe croissante puis score décroissant."""
    sortie = sortie_aleatoire(graine)
    a = yolox(classes=(7, 0, 2)).decoder(sortie, RATIO_S1)
    b = yolox(classes=(0, 2, 7)).decoder(sortie, RATIO_S1)
    assert all(identiques(x, y) for x, y in zip(a, b))
    boites, scores, ids = a
    assert set(ids.tolist()) == {0, 2, 7} and np.all(np.diff(ids) >= 0)
    for k in (0, 2, 7):
        assert np.all(np.diff(scores[ids == k]) <= 0)


@pytest.mark.parametrize("graine", GRAINES)
def test_bloc_person_inchange_en_multiclasse(session, graine):
    """T17 : en multi-classe, les personnes sont en tête et égales au bit près au mode `person` seul."""
    sortie = sortie_aleatoire(graine)
    boites, scores, ids = yolox(classes=(0, 2, 7)).decoder(sortie, RATIO_S1)
    pb, ps, _pi = yolox().decoder(sortie, RATIO_S1)
    n = len(ps)
    assert not ids[:n].any() and ids[n:].all()
    assert identiques(boites[:n], pb) and identiques(scores[:n], ps)


@pytest.mark.parametrize("noms", [["voiture"], ["person", "person"], [], "person", ["person", 2], None])
def test_noms_invalides(noms):
    """T18 : nom inconnu, doublon, liste vide, chaîne seule ou élément non textuel refusés."""
    with pytest.raises(ValueError):
        indices_classes(noms)


@pytest.mark.parametrize("classes", [(), (80,), (-1,), (0, 0), (True,), (np.int64(0),), (0.0,)])
def test_indices_invalides(session, classes):
    """T18 : indices hors vocabulaire, en double, vides ou non entiers refusés à la construction."""
    with pytest.raises(ValueError):
        yolox(classes=classes)


def test_adaptateur_multiclasse():
    """T19 : l'adaptateur nomme chaque indice par COCO_CLASSES et respecte les invariants de `Detections`."""
    boites = np.arange(12, dtype=np.float32).reshape(3, 4)
    scores = np.array([0.9, 0.8, 0.7], np.float32)
    ids = np.array([0, 2, 7], np.int64)
    faux = SimpleNamespace(detecter=lambda bgr: (boites, scores, ids))
    d = AdaptateurYolox(faux).detecter(np.zeros((8, 8, 3), np.uint8))
    assert d.classes == ("person", "car", "truck") and d.ids_modele is ids
    assert d.boites is boites and d.scores is scores


def test_fabrique_reste_person(session):
    """T20 : `creer_detecteur` ne transmet aucune classe ; une voiture très bien notée n'est pas rendue."""
    cfg, _ = cfgmod.charger(str(CONFIG_S1))
    d = creer_detecteur(cfg["analyse"], "modele_simule.onnx", None)
    assert d.yolox.classes == (0,)
    s = sortie_vide()
    placer(s, 100, 100, 100, 50, 50, 1.0, car=0.99)
    placer(s, 3000, 300, 300, 50, 50, 1.0, person=0.5)
    session.sortie = s
    assert d.detecter(np.zeros((1072, 1920, 3), np.uint8)).classes == ("person",)


# Vérification des colonnes de sortie à la construction

@pytest.mark.parametrize("colonnes", [84, 86, "num_sorties", None])
def test_colonnes_de_sortie_refusees(session, colonnes):
    """Sortie déclarée à 84 ou 86 colonnes, ou dimension symbolique ou inconnue : refus explicite."""
    session.colonnes = colonnes
    with pytest.raises(ValueError, match="85 colonnes"):
        yolox()


def test_85_colonnes_acceptees_sans_inference(session):
    det = yolox()
    assert det.classes == (0,) and session.appels_run == 0


@pytest.mark.skipif(not MODELE.exists(), reason="modèle hors git absent")
def test_vrai_modele_declare_85_colonnes():
    det = DetecteurYolox(str(MODELE), TAILLE, SEUIL, SEUIL_NMS, 1)
    assert det.session.get_outputs()[0].shape == [1, 8400, 85]
