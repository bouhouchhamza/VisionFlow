# Plan du premier refactoring : découpler YOLOX de `run.py`

> Statut : **validé par le porteur le 2026-11-11** (deux commits locaux, rejouées autorisées, interface nommée
> `Detector`) ; exécution en cours. Les résultats sont consignés dans `experiments/E2/RESULTATS_S1.md` §7.
> Source : `docs/AUDIT_ARCHITECTURE.md` §4 (couplage C1) et §8 (étapes 1 à 3). Plan rédigé sur l'état `d73403c`.

## 0. Cadre

- **S1 = baseline technique non validée.** Le run `runs/20261103T172241Z-b3b507` sert de référence de
  **comportement** : on vérifie que le refactoring produit exactement les mêmes sorties. Cela ne dit rien de la
  justesse : l'annotation de S1 n'est pas faite (passages denses), et aucune erreur n'est mesurée.
- **Gel maintenu** : détecteur YOLOX (`passages/detection.py`), suivi ByteTrack, ligne, seuils et
  `configs/s1_g420.yaml` ne changent pas. R1 et R2 ne sont pas touchées. RF-DETR n'est pas intégré.
- **Aucune optimisation, aucun benchmark** : les durées enregistrées dans les manifestes des runs de contrôle ne
  sont pas interprétées.

## 1. Plus petit changement qui découple YOLOX de `run.py`

État actuel : `run.py` importe la classe concrète et l'instancie avec des arguments propres à YOLOX.

```19:19:passages/run.py
from passages.detection import DetecteurYolox
```

```72:73:passages/run.py
    detecteur = DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]), float(analyse["seuil_detection"]),
                               float(analyse["seuil_nms"]), threads)
```

Le reste de la boucle n'utilise que `detecteur.detecter(bgr) -> (boites, scores)` (ligne 101).

**Changement proposé (minimal)** :
1. Nouveau module `passages/detecteur.py` contenant :
   - un `Protocol` nommé `Detector` (nom retenu par le porteur ; la méthode et la fabrique restent en français comme
     le reste du code). Il ne déclare qu'une méthode, `detecter` ;
   - une fabrique `creer_detecteur(analyse, chemin_modele, threads)` qui construit `DetecteurYolox` **avec exactement
     les mêmes arguments et conversions** que les lignes 72-73.
2. Dans `run.py`, deux modifications seulement : l'import (ligne 19) et la construction (lignes 72-73) deviennent un
   appel à la fabrique. La boucle, la construction de `sv.Detections`, la classe forcée à 0, l'ancrage, le manifeste
   et les formats de sortie restent tels quels.
3. `passages/detection.py` **n'est pas modifié** : un `Protocol` est satisfait par la forme des méthodes, sans
   héritage, donc `DetecteurYolox` est conforme tel quel.

Ce qui est volontairement **exclu** de ce changement, et reporté aux étapes suivantes de l'audit :
- clé de configuration `type` du détecteur (changerait l'empreinte canonique de la configuration) ;
- classes dans la sortie du détecteur, `class_id` réel (couplages C2, C3) ;
- description du détecteur dans le manifeste (C8) ;
- ancrage configurable, refus des clés inconnues (C6) ;
- registre de plusieurs détecteurs, chargement différé d'ONNX Runtime.

Une seule implémentation existe : une fabrique sans choix suffit à sortir le nom YOLOX de `run.py`. Un registre sans
second détecteur serait du code non exercé.

## 2. Interface `Detector` proposée

Esquisse, non appliquée :

```python
"""Interface commune des détecteurs et construction du détecteur d'un run."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from passages.detection import DetecteurYolox


@runtime_checkable
class Detector(Protocol):
    def detecter(self, bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Image BGR uint8 (H, W, 3) en pleine résolution de la vidéo.

        Rend (boîtes, scores) : boîtes xyxy float32 (N, 4) en pixels de cette image, bornées à [0, W-1] × [0, H-1] ;
        scores float32 (N,) dans [0, 1], déjà filtrés par le seuil ; une seule classe (personne) ; ordre déterministe,
        conservé tel quel par le suivi.
        """
        ...


def creer_detecteur(analyse: dict, chemin_modele: str, threads: int | None = None) -> Detector:
    return DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]), float(analyse["seuil_detection"]),
                          float(analyse["seuil_nms"]), threads)
```

Et dans `run.py` :

```diff
-from passages.detection import DetecteurYolox
+from passages.detecteur import creer_detecteur
 ...
-    detecteur = DetecteurYolox(chemin_modele, tuple(analyse["modele"]["taille_entree"]), float(analyse["seuil_detection"]),
-                               float(analyse["seuil_nms"]), threads)
+    detecteur = creer_detecteur(analyse, chemin_modele, threads)
```

Compatibilité avec les sorties actuelles :
- **Contrat d'entrée** : celui d'aujourd'hui (`trame.to_ndarray(format="bgr24")`), désormais écrit.
- **Contrat de sortie** : celui de `DetecteurYolox.detecter`. YOLOX rend déjà du float32 dans les deux cas, liste vide
  comprise, et `run.py` reconvertit en float32 de toute façon.
- **Ordre des détections** : après NMS, par score décroissant (`detection.py` l. 74-89). Le contrat l'exige stable,
  car l'ordre d'entrée peut influer sur l'association du suivi en cas d'égalité.
- **Sortie sans classe** : on garde l'interface actuelle pour ne pas modifier `detection.py`. Les classes
  arriveront avec C2 et C3, et changeront l'interface à ce moment-là, alors qu'il n'existera encore qu'une seule
  implémentation.

## 3. Test de non-régression déterministe

### 3.1 Ce qui est comparé

Un nouvel outil compare un run **candidat** à un run de **référence**, en lecture seule sur les deux. Proposition :
module `passages/non_regression.py` et commande `comparer-runs`.

| Bloc | Champs | Règle |
|---|---|---|
| Préalables de comparabilité | sha256 vidéo et modèle, sha256 canonique de la configuration, `mode_temps`, `bilan_temps`, versions de Python et des paquets, processeur, `threads_onnxruntime`, `limite_s`, images décodées et analysées | Égalité stricte, sinon verdict **NON_COMPARABLE** (ce n'est pas une régression, c'est une comparaison invalide) |
| Pistes (`pistes.jsonl`), image par image | `num_image`, `t_ms`, `pts`, `temps_reconstruit`, `detections_brutes`, nombre d'objets, identifiants de piste dans l'ordre | Égalité stricte |
| | boîtes (arrondies à 0,1 px), scores (arrondis à 1e-4) | Égalité stricte attendue ; un écart d'au plus un pas d'arrondi est classé à part (voir §3.3) |
| Événements (`evenements.json`) | franchissements : `id`, `ligne`, `piste`, `sens_geometrique`, `direction`, `t_ms`, `num_image`, `t_ms_avant`, `num_image_avant` | Égalité stricte |
| | franchissements : `u`, `point`, `confiance` | Même règle que les boîtes et les scores |
| | `passages_derives`, `doublons_probables`, `pistes` (début et fin), `temps`, `regle_passage`, `nature`, `format`, `version_format` | Égalité stricte |
| Statistiques recalculées par l'outil depuis les deux fichiers d'événements | nombre de pistes, franchissements par ligne et par direction, passages par statut et par direction, nombre de doublons, passages par minute de temps vidéo et par direction | Égalité stricte |
| Exclus (attendus différents) | `run_id` (manifeste et événements), `cree_le_utc`, `commande`, `duree_calcul_s`, `chronometrage_s`, `vitesse_s_video_par_s_calcul`, `git_commit`, `git_dirty`, `git_fichiers_modifies`, `config.sha256_fichier` (absent du run S1) | Ignorés, et listés dans le rapport |

Verdicts :
- **IDENTIQUE** : tout ce qui est comparé est égal.
- **ÉCARTS_D_ARRONDI** : seuls des écarts d'un pas d'arrondi existent sur les boîtes, les scores, `u` ou `point`, et
  tout le reste est égal.
- **DIFFÉRENT** : tout autre écart. Le rapport donne alors la **première divergence** (image, `t_ms`, champ) et le
  décompte des écarts par bloc.
- **NON_COMPARABLE** : les préalables diffèrent.

Mode tronqué `--jusqu-a-ms T` : seules les lignes de pistes et les franchissements avec `t_ms ≤ T` sont comparés. Les
passages dérivés, les doublons et les débuts et fins de pistes sont exclus, car ils dépendent de la fin de
l'observation. Dans ce mode, `limite_s` et les nombres d'images décodées et analysées sortent des préalables ; les
autres préalables restent stricts. Ce mode sert à comparer un run limité (`--limite-s`) à un run complet.

Le rapport, en JSON et en Markdown, est écrit dans `runs/non_regression/comparaisons/` (ou dans le dossier passé par
`--sortie`). L'outil refuse d'écrire dans le dossier de l'un des deux runs comparés. La commande renvoie le code 0 si le
verdict est IDENTIQUE, 1 sinon.

### 3.2 Sources de non-déterminisme

| Source | Effet possible | Traitement |
|---|---|---|
| Identifiant de run, dates, commande, durées, état git | Toujours différents | Exclus de la comparaison (§3.1) |
| ONNX Runtime multi-thread (CPU, nombre de threads par défaut) | Réductions en virgule flottante parallèles : ONNX Runtime ne garantit pas, à ma connaissance, des résultats bit à bit identiques d'une exécution à l'autre ; non vérifié dans sa documentation | Même machine et même nombre de threads (`threads_onnxruntime` dans les préalables). Une observation existe déjà : l'essai de 20 s et le run complet coïncident sur leurs 20 premières secondes. Un seul accord ne prouve pas la stabilité ; les écarts d'arrondi sont classés à part |
| Version des paquets, jeu d'instructions du processeur | Calculs numériques différents | Préalables stricts (versions, processeur). Vérifié le 2026-11-11 : l'environnement `.venv` correspond exactement à `requirements.lock` (seuls `pip` et `setuptools` s'y ajoutent) |
| Décodage H.264 (FFmpeg dans PyAV) | Le décodage H.264 est exact au bit près par norme, quel que soit le nombre de threads | Aucun traitement ; un écart sur `pts` ou `num_image` serait détecté |
| Redimensionnement OpenCV (SIMD, threads) | Identique sur la même machine et la même version | Préalables |
| Arrondis à l'écriture (0,1 px, 1e-4) | Une variation de 1e-7 peut faire basculer un arrondi | Verdict ÉCARTS_D_ARRONDI distinct ; il impose une analyse avant toute acceptation |
| Identifiants de piste | `trackers` 2.6.1 alloue les identifiants par un compteur **propre à chaque instance** (`core/base.py`, `_next_track_id`) | Déterministe si les entrées le sont ; un seul traqueur par processus |
| Ordre des dictionnaires et des ensembles | Aucun ensemble de chaînes dans le pipeline ; les sorties sont triées ou en ordre d'insertion | Aucun traitement |
| Charge de la machine | Sans effet sur les résultats : l'analyse hors ligne traite toutes les images décodées et échantillonne sur le temps vidéo, pas sur l'horloge | Aucun traitement ; seules les durées varient, et elles sont exclues |
| Fin anticipée (`--limite-s`) | Passages près de la fin, débuts et fins de pistes | Mode tronqué (§3.1) |
| Fichiers d'entrée modifiés | Tout change | `analyser` refuse déjà une vidéo ou un modèle dont l'empreinte diffère ; la configuration est comparée par empreinte canonique |

### 3.3 Politique d'acceptation

- **Le refactoring est accepté seulement si le verdict est IDENTIQUE.** Le changement ne modifie aucun calcul ; un
  autre résultat signale soit une erreur, soit un non-déterminisme qu'il faut comprendre avant de continuer.
- ÉCARTS_D_ARRONDI, sans le refactoring : si deux runs du **même** code donnent ce verdict, le non-déterminisme est
  établi. On le consigne, et on refait la comparaison du refactoring avec `--threads 1` des deux côtés. Les deux runs
  nécessaires à cette comparaison seraient de nouveaux runs, et ne remplaceraient pas S1.

### 3.4 Le run S1 a une provenance incomplète

Le manifeste de S1 indique `git_commit: null` et `git_modifications_locales: true` : il a été produit à 17:22 UTC,
avant le premier commit (`2517bc1`, 17:36 UTC). Entre `2517bc1` et `d73403c`, le chemin d'analyse n'a changé que par
des métadonnées du manifeste (empreinte du fichier de configuration, état git), d'après le `git diff` du 2026-11-11.
Le code exact qui a produit S1 n'est donc pas identifié par un commit.

D'où une **rejouée de contrôle avant refactoring** (§5, étape B) : le code actuel, sur un commit propre, doit
reproduire S1. Si c'est le cas, S1 reste la référence. Sinon, l'écart est consigné, et la rejouée devient la
référence du refactoring, avec S1 conservé tel quel.

### 3.5 Contrôles de l'outil lui-même

Un comparateur qui répond toujours IDENTIQUE ne prouverait rien. Avant usage :
- tests N0 sur des runs **synthétiques** (marqués comme tels dans les fichiers de test) : copie exacte → IDENTIQUE ;
  `run_id` et durées modifiés → IDENTIQUE ; boîte décalée de 0,1 px → ÉCARTS_D_ARRONDI ; une direction inversée →
  DIFFÉRENT avec la bonne première divergence ; un `t_ms` décalé → DIFFÉRENT ; version de paquet différente →
  NON_COMPARABLE ; `sha256_fichier` absent d'un côté → ignoré ; mode tronqué ;
- contrôle positif sur des données réelles : essai de 20 s comparé à S1 avec `--jusqu-a-ms 20000` → attendu
  IDENTIQUE (cohérent avec l'accord déjà constaté) ;
- contrôle négatif sur des données réelles : essai de 20 s comparé à S1 **sans** troncature → attendu NON_COMPARABLE
  (`limite_s` et nombres d'images différents) ; en mode tronqué avec une borne trop large (`--jusqu-a-ms 300000`) →
  attendu DIFFÉRENT, puisque S1 a 22 franchissements et l'essai 21.

Empreintes relevées le 2026-11-11, pour vérifier qu'aucun run de référence n'est modifié :

| Fichier | Octets | SHA-256 |
|---|---|---|
| `runs/20261103T172241Z-b3b507/evenements.json` | 15 238 | `701EFF4E6A135626E8B151F686C656920D5BB8F4489CF02D133161A22ECEC68D` |
| `runs/20261103T172241Z-b3b507/manifest.json` | 5 280 | `C77AB75229BE666125E926CFB0F65F996817E0AFD8480430AEFD2C2E730C89E9` |
| `runs/20261103T172241Z-b3b507/pistes.jsonl` | 535 710 | `80831D0CCC32D783E9F22E047A32BD827A92122FA4CE72F0AF6E8A3DED35F5CA` |
| `runs/essais/20261103T172153Z-b5f6a3/evenements.json` | 14 541 | `E04ED57E5E5E97AE39F9DB31874BC17A4576AFC4425B860A58978DF5D94825B8` |
| `runs/essais/20261103T172153Z-b5f6a3/manifest.json` | 5 332 | `969421410A3842FCFF7A25ADF8A9CDCD13B839E6C17104B3D0DF89FB440FEFCE` |
| `runs/essais/20261103T172153Z-b5f6a3/pistes.jsonl` | 160 215 | `47D65A7FA82298432E8F6083828CEC3E1CDEA4F13DC1DA95556311FC4EF9F970` |

## 4. Fichiers concernés

| Fichier | Commit 1 (outil) | Commit 2 (interface) | Nature |
|---|---|---|---|
| `passages/non_regression.py` | **créé** | — | Comparaison de deux runs, lecture seule |
| `passages/cli.py` | modifié | — | Ajout de la commande `comparer-runs` ; les commandes existantes ne changent pas |
| `tests/test_non_regression.py` | **créé** | — | Tests N0 synthétiques (§3.5) |
| `passages/detecteur.py` | — | **créé** | `Protocol` `Detector` et fabrique |
| `passages/run.py` | — | modifié | Ligne 19 et lignes 72-73 seulement |
| `tests/test_detecteur.py` | — | **créé** | Voir §6 |
| `docs/DECISIONS.md` | — | modifié | Entrée D-025 (§7), si validée |
| `experiments/E2/RESULTATS_S1.md` | modifié | modifié | S1 = baseline technique non validée ; résultats des contrôles de non-régression |
| `docs/AUDIT_ARCHITECTURE.md`, ce plan | ajoutés | — | Documents de cette série, non commités à ce jour |
| `AGENTS.md` | — | modifié (une ligne) | Exiger la non-régression S1 pour tout refactoring du pipeline, si D-025 est validée |

**Non modifiés** : `passages/detection.py`, `crossing.py`, `video.py`, `config.py`, `render.py`, `annotate.py`,
`evaluate.py`, `paires.py`, `versions.py`, `configs/s1_g420.yaml`, `requirements.txt`, `requirements.lock`, `models/`,
les runs existants, R1 et R2. Aucun autre module n'importe `detection` (vérifié par recherche dans le dépôt).

**Créés hors git** : `runs/non_regression/<run_id>/` pour les rejouées (le dossier `runs/` est ignoré par git), et
les rapports dans `runs/non_regression/comparaisons/` et `runs/non_regression/controles_comparateur/`. Pas de vidéo annotée nécessaire.

## 5. Séquence d'exécution proposée

Chaque ligne marquée ⏸ attend votre autorisation.

| Étape | Action | Coût | Résultat attendu |
|---|---|---|---|
| A | Écrire l'outil, ses tests, la commande ; `python -m pytest -q tests` | Quelques secondes | 27 tests existants + nouveaux, tous passent |
| A' | Contrôles positif et négatif de l'outil sur l'essai de 20 s et S1 (§3.5) | Lecture de fichiers | IDENTIQUE en mode tronqué, NON_COMPARABLE sans |
| ⏸ Commit 1 | « Outil de non-régression entre deux runs » | — | Arbre propre |
| ⏸ B | Rejouée de contrôle, **code actuel** sur commit propre : `analyser --config configs/s1_g420.yaml --runs runs/non_regression` (300 s de vidéo ; S1 avait pris 616 s de calcul) | ≈ 10 min de machine | IDENTIQUE à S1. Sinon, consigner l'écart ; la rejouée B devient la référence (§3.4) |
| C | Écrire `detecteur.py`, modifier `run.py`, tests ; `pytest` | Quelques secondes | Tous les tests passent |
| C' | Rejouée courte, arbre modifié : `analyser … --limite-s 20 --runs runs/non_regression`, comparée à l'essai de 20 s | ≈ 40 s de machine | IDENTIQUE ; le manifeste indique `git_dirty: true` et liste les fichiers modifiés |
| ⏸ Commit 2 | « Interface Detecteur : run.py ne dépend plus de YOLOX » | — | Arbre propre |
| ⏸ D | Rejouée complète sur le commit 2, comparée à la référence retenue en B (et à S1) | ≈ 10 min de machine | IDENTIQUE |
| E | Vérifier les empreintes du §3.5 ; consigner les verdicts dans `RESULTATS_S1.md` | Lecture | Empreintes inchangées |

Les étapes B et D ne sont ni des benchmarks ni des réglages : elles exécutent la configuration gelée, sans aucun
paramètre nouveau, et seule l'égalité des sorties est examinée. Aucun push.

Variante possible : fusionner les commits 1 et 2. Je la déconseille. Le commit de l'outil doit exister et être
contrôlé **avant** le refactoring, pour que la rejouée B soit produite par un commit propre. De plus, le diff du
refactoring reste ainsi limité à trois fichiers.

## 6. Premier commit du refactoring (commit 2) et critères d'acceptation

**Contenu** : `passages/detecteur.py` (créé), `passages/run.py` (deux endroits), `tests/test_detecteur.py` (créé),
`docs/DECISIONS.md` (D-025), `experiments/E2/RESULTATS_S1.md` (verdicts), éventuellement `AGENTS.md`.

**Tests ajoutés (`tests/test_detecteur.py`)** :
- un faux détecteur minimal est reconnu comme `Detector` ; un objet sans `detecter` ne l'est pas ;
- `creer_detecteur` construit un `DetecteurYolox` avec `taille`, `seuil` et `seuil_nms` égaux à ceux de
  `configs/s1_g420.yaml` (test ignoré proprement si `models/yolox_s.onnx` est absent, puisque le modèle est hors git) ;
- `run.py` ne nomme plus YOLOX : aucune occurrence de `DetecteurYolox` ni de `detection` dans son source.

**Critères d'acceptation (tous requis)** :
1. `.\.venv\Scripts\python -m pytest -q tests` : tous les tests passent (27 existants et nouveaux).
2. `passages/detection.py`, `configs/s1_g420.yaml`, `requirements*.txt` et `requirements.lock` sont inchangés
   (`git diff --stat` ne les cite pas).
3. Le diff de `run.py` se limite à l'import et à la construction du détecteur.
4. Rejouée courte C' : IDENTIQUE à l'essai de 20 s.
5. Rejouée complète D : IDENTIQUE à la référence retenue en B. Les verdicts couvrent les événements, les directions,
   les identifiants de piste et de franchissement, les `t_ms` et les statistiques.
6. Les empreintes des runs de référence (§3.5) sont inchangées.
7. Les verdicts, les identifiants des rejouées et le commit sont consignés dans `RESULTATS_S1.md`, avec la mention :
   « équivalence de comportement, pas une mesure de justesse ».

En cas d'échec d'un critère, le commit n'est pas fait. Le run fautif est gardé pour diagnostic, et le constat vous
est présenté avant toute correction.

## 7. Risques

| Risque | Probabilité | Effet | Parade |
|---|---|---|---|
| Le code actuel ne reproduit pas S1 (provenance incomplète, §3.4) | Faible : le chemin d'analyse n'a pas changé depuis `2517bc1` ; inconnue avant ce commit | Référence à déplacer vers la rejouée B | Étape B avant le refactoring ; S1 conservé |
| Non-déterminisme d'ONNX Runtime | Inconnue ; un accord partiel déjà observé | Faux signal de régression | Verdict ÉCARTS_D_ARRONDI distinct ; contrôle avec `--threads 1` (§3.3) |
| Conversion d'arguments modifiée par mégarde dans la fabrique (`tuple`, `float`) | Faible | Seuils effectifs différents | Test de la fabrique ; non-régression |
| Comparateur trop permissif | Moyenne si non testé | Fausse assurance | Tests négatifs et contrôle négatif sur des données réelles (§3.5) |
| Écriture accidentelle dans le dossier S1 | Faible | Perte de la référence | Lecture seule, rapports hors des runs comparés (refus codé), empreintes vérifiées à l'étape E |
| Glissement de périmètre (registre, classes, clé de configuration) | Moyenne | Diff plus large, empreinte de configuration changée | Exclusions explicites (§1) |
| Environnement modifié entre deux rejouées | Faible | NON_COMPARABLE | Préalables ; contrôle du verrou avant B et D |
| Confusion entre équivalence et validation | Moyenne | Conclusion fausse sur la qualité | Mention obligatoire (critère 7) ; S1 reste « baseline technique non validée » |
| Temps de machine (≈ 20 min pour B et D) | Certaine | Délai | Rejouée courte C' d'abord, pour détecter tôt une régression |

## 8. Proposition d'entrée pour `docs/DECISIONS.md` (non insérée)

```markdown
### D-025 — Détecteur derrière une interface ; refactorings vérifiés par non-régression · Proposition
- **Constat** : `docs/AUDIT_ARCHITECTURE.md` §4 (C1) ; `run.py` importe et construit `DetecteurYolox` directement.
- **Décision proposée** :
  - `run.py` ne connaît qu'un `Protocol` `Detector` (méthode `detecter(bgr) -> (boîtes xyxy float32, scores
    float32)`, contrat d'entrée BGR uint8 pleine résolution, ordre de sortie déterministe) et une fabrique
    `creer_detecteur` dans `passages/detecteur.py`. YOLOX reste l'unique implémentation, inchangée (D-022).
  - Tout refactoring du chemin d'analyse doit produire un run **IDENTIQUE** à la référence S1 au sens de
    `passages/non_regression.py` : événements, directions, identifiants, temps vidéo et statistiques égaux ; seuls
    l'identifiant de run, les dates, les durées et l'état git sont exclus.
- **Statut de S1** : baseline **technique** non validée. L'égalité prouve que le comportement est conservé, pas qu'il
  est juste.
- **Hors périmètre** : classes, clé de configuration du type de détecteur, description du détecteur dans le
  manifeste, second détecteur (RF-DETR) : chacun fera l'objet d'une entrée propre.
- **Dépendances** : aucune nouvelle (`typing.Protocol` fait partie de la bibliothèque standard).
- **Révision** : quand un second détecteur sera décidé, ou quand l'interface devra transporter des classes.
```

Ligne de synthèse correspondante :
`| D-025 | Détecteur derrière une interface ; refactorings vérifiés par non-régression | Proposition | Avant le commit 2 |`

## 9. Points à valider

1. Le nom de l'interface : `Detector` retenu (2026-11-11), dans `passages/detecteur.py`.
2. L'interface laissée volontairement sans classes (§2).
3. Deux commits (outil, puis interface) plutôt qu'un seul.
4. Les règles de verdict, en particulier le refus d'ÉCARTS_D_ARRONDI pour accepter le refactoring.
5. L'autorisation des deux rejouées complètes de S1 (B et D, environ 10 min chacune) dans `runs/non_regression/`.
6. L'insertion de D-025 dans `docs/DECISIONS.md` au moment du commit 2.
