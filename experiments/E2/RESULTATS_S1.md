# Prototype scénario A — résultats sur S1 (2026-11-03)

Statut : **pipeline exécuté de bout en bout sur l'extrait de réglage S1 ; aucune mesure d'erreur**, car l'annotation
humaine de référence n'existe pas encore. Rien ici ne valide le comptage.

## 1. Commandes reproductibles

Depuis la racine du projet, sous Windows PowerShell :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock
# vidéo S1 et modèle : URL et empreintes dans experiments/E0/INVENTAIRE.md et docs/DECISIONS.md D-022
#   data/videos/meva/2018-03-07.16-50-01.16-55-01.school.G420.r13.avi
#   models/yolox_s.onnx  (https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx)

.\.venv\Scripts\python -m pytest -q tests                                            # tests N0
.\.venv\Scripts\python -m passages analyser --config configs/s1_g420.yaml            # crée runs/<run_id>/
.\.venv\Scripts\python -m passages rendre --run runs/<run_id>                         # runs/<run_id>/rendus/video_annotee.mp4
.\.venv\Scripts\python -m passages annoter --config configs/s1_g420.yaml --annotateur <nom> --passe 1 --echantillon S1
.\.venv\Scripts\python -m passages comparer --run runs/<run_id> --reference data/annotations/<sha16>/<nom>_passe1.json
.\.venv\Scripts\python -m passages comparer-runs --reference runs/<run_a> --candidat runs/<run_b>   # non-régression (§7)
```

`analyser` vérifie les empreintes de la vidéo et du modèle avant de commencer. Il écrit dans `runs/<run_id>.tmp/`,
puis renomme le dossier seulement en cas de succès : un dossier `.tmp` n'est jamais un run valide. `rendre` et
`comparer` ajoutent des sous-dossiers (`rendus/`, `comparaisons/`) et ne modifient pas les fichiers du run.

## 2. Contenu d'un run

| Fichier | Contenu |
|---|---|
| `manifest.json` | `run_id`, commande, configuration complète et empreinte canonique, empreintes de la vidéo et du modèle, bilan du temps vidéo, versions (Python, paquets, commit git, modifications locales), processeur, chronométrage |
| `pistes.jsonl` | Une ligne par image analysée : rang, temps vidéo, PTS brut, boîtes, scores, numéros de piste (−1 = non confirmée) |
| `evenements.json` | Franchissements bruts (observations machine), passages dérivés par la règle de maintien (hypothèse), doublons probables, début et fin de chaque piste |
| `rendus/` | Vidéo annotée et sa fiche (`rendu.json` : empreinte, encodeur) |
| `comparaisons/` | Rapports `.md` et `.json` contre une annotation humaine |

Chaque événement est daté par le **temps vidéo** (rang d'affichage × 1/30 s pour S1, temps reconstruit : D-023), jamais
par la vitesse d'exécution. L'heure murale se déduit du début déclaré `2018-03-07T16:50:01`, tiré du nom de fichier,
dont le fuseau horaire n'est pas documenté.

## 3. Run `20261103T172241Z-b3b507` (S1 entière)

Configuration : `configs/s1_g420.yaml`, empreinte canonique dans le manifeste. Aucun paramètre n'a été réglé
d'après les résultats : ce sont les valeurs de départ.

### Temps vidéo

9 000 paquets, aucun vide ; 9 000 images décodées ; 4 328 reculs de PTS bruts (attendus, E3 §4.3). Le temps
reconstruit est régulier **par construction** (33,33 ms entre images) : la régularité de la capture à 30 images/s reste
une hypothèse propre à S1, que ces comptes ne prouvent pas.

### Observations machine (non validées)

| Mesure | Valeur |
|---|---|
| Images analysées | 3 000 (10 par seconde de temps vidéo) |
| Pistes confirmées | 24 |
| Franchissements bruts | 22 (21 entre 2,4 s et 16,8 s, 1 à 181,9 s) |
| Passages retenus, maintien 1 000 ms | 14, tous des sorties |
| Franchissements annulés par aller-retour | 8 (pistes 13, 19 et 5) |
| Paires « doublon probable » (même sens, < 1,5 s, pistes différentes) | 14 paires, toutes pendant la sortie de groupe des 17 premières secondes |

Lecture prudente : au début de l'extrait, un groupe sort par les portes ; les allers-retours rapides d'une même piste
ressemblent à des oscillations du point d'ancrage autour de la ligne (personnes serrées, pieds masqués). C'est une
**hypothèse** à confirmer ou infirmer par l'annotation humaine. Le signal « doublon probable » ne distingue pas un vrai
doublon de deux personnes qui marchent ensemble.

### Débit mesuré sur ce poste

Intel Core i7-1255U (12 cœurs logiques), 15,7 Go de RAM, sans GPU, Windows, ONNX Runtime CPU, threads par défaut.
Une seule vidéo à la fois.

| Étape | Temps total | Par image analysée |
|---|---|---|
| Décodage H.264 1920×1072 (les 9 000 images) | 14,3 s | — |
| Conversion en BGR | 32,5 s | 10,8 ms |
| Détection YOLOX-S 640×640 | 567,2 s | 189 ms |
| Suivi et règle de franchissement | 1,8 s | 0,6 ms |
| **Total** | **616,2 s pour 300,0 s de vidéo** | **0,49 s de vidéo par seconde de calcul** |

La vitesse a baissé pendant le run, de 0,62 (première minute) à 0,49 en fin de run. La cause n'est pas mesurée ;
la limitation thermique d'un processeur de portable est une hypothèse.
Rendu de la vidéo annotée : 100 s (second décodage complet et encodage x264), hors mesure ci-dessus.

Ces chiffres ne permettent **aucune extrapolation** à plusieurs caméras, à une autre résolution, à une autre cadence
d'analyse ou à une autre machine : une seule configuration a été mesurée, et ce run seul n'atteint pas le temps réel.
Mémoire maximale : non mesurée.

### Reproductibilité

Un essai indépendant sur les 20 premières secondes (`runs/essais/20261103T172153Z-b5f6a3`, même code, même configuration)
donne des sorties **identiques** à celles du run complet sur cette portion : 201 images analysées sur 201,
21 franchissements sur 21, mêmes statuts. Ce constat vaut pour ce poste et ces versions.

## 4. Vérifications faites

- 23 tests N0 (données synthétiques) : géométrie et côtés, marge morte, segment et extension, instant retenu,
  règle de maintien (aller-retour, hésitation, retour lent, fin de vidéo), échantillonnage sur temps irrégulier,
  appariement un pour un, erreurs compensées, sens inversé, doublon, demi-tour compté, non observable,
  saisie de l'outil d'annotation, `comparer` de bout en bout.
- Lecteur d'annotation : 48 sauts sur 48 rendent l'image exacte (E3 §4.3).
- Vidéo annotée : 3 000 images, 10 images/s, 960×536, 300,0 s (ffprobe).

## 5. Procédure prévue après réception de la référence humaine

Gel jusqu'à la passe 1 : détecteur, suivi, ligne et seuils ne changent pas (empreinte canonique de la configuration
vérifiée identique à celle du run `20261103T172241Z-b3b507`). Aucune optimisation de performance avant d'avoir localisé
les erreurs.

1. Comparaison sur le run existant :
   `python -m passages comparer --run runs/20261103T172241Z-b3b507 --reference <annotation>`
   → appariés, manqués, ajoutés, sens inversés, doublons, tableau par minute.
2. Examen des 14 paires suspectes :
   `python -m passages examiner-paires --run runs/20261103T172241Z-b3b507 --reference <annotation>`
   → indices par paire (recouvrement des pistes, IoU, intervalle et distance de reprise, nombre de franchissements et
   excursion au-delà de la ligne), lecture de la référence (une ou plusieurs personnes humaines dans la fenêtre),
   planches de 4 images par paire. Catégories : fragmentation du suivi, même personne sur deux pistes, oscillation autour
   de la ligne, personnes réellement différentes, vrai aller-retour (lien `retour_de` de la référence). Les catégories
   automatiques sont des indices ; la conclusion se fait sur les planches et la référence.
3. Durées de maintien : la comparaison donne déjà H = 0, 500, 1 000 et 2 000 ms, appliquées de la même façon à la
   machine et à la référence. La référence humaine n'est jamais modifiée ; un désaccord apparent est noté, pas corrigé.
4. Une seule correction ciblée sur la cause d'erreur dominante, consignée dans `docs/DECISIONS.md`, nouveau run,
   nouvelle comparaison : effet mesuré sur S1, présenté comme **résultat de réglage**.
5. Réserves R1 et R2 : seulement après gel d'une première configuration (empreinte notée).

Traçabilité ajoutée pour les prochains runs : commit et état « dirty » de tout le dépôt au démarrage
(`git_commit`, `git_dirty`, `git_fichiers_modifies`), empreintes de la vidéo, du modèle, de la configuration (contenu
canonique et fichier). Les rendus, comparaisons et examens enregistrent aussi le commit de l'outil. Le run existant,
antérieur au premier commit, n'a pas de commit enregistré.

## 6. Limites

- **Aucune mesure d'erreur** : manqués, ajouts, sens inversés et doublons ne sont pas mesurés tant que S1 n'est pas annotée.
  Ensuite, ils ne vaudront que pour S1, extrait de réglage : une estimation optimiste, pas une évaluation.
- Un seul extrait, une seule vue, une seule scène dense (≈ 17 s) ; le reste de l'extrait est presque vide.
- La boucle graphique de l'outil d'annotation (fenêtre, touches) n'a pas été exercée ; seule sa logique l'a été.
- Ancrage au bas de la boîte : sensible aux pieds masqués et aux boîtes coupées par le bord de l'image.
- `lost_track_buffer` vaut 60, soit 2 s, et la cadence d'analyse 10 images/s : ces valeurs de départ ne sont pas réglées.
- Le statut juridique des poids YOLOX et les conditions des données COCO restent non établis (D-022).
- Le comparateur ne compare pas encore deux passes humaines entre elles.

## 7. S1, baseline technique non validée, et non-régression (2026-11-11)

L'annotation de S1 est difficile, à cause de la densité des passages au début. S1 est donc conservé comme **baseline
technique non validée** : le run `20261103T172241Z-b3b507` sert de référence de **comportement** pour les
refactorings, sans que l'évaluation soit terminée. Une égalité de sorties prouve que le comportement est conservé,
pas qu'il est juste. Plan : `docs/PLAN_DECOUPLAGE_DETECTEUR.md`.

Commande :

```powershell
.\.venv\Scripts\python -m passages comparer-runs --reference <run> --candidat <run> [--jusqu-a-ms T] [--sortie <dossier>]
```

Verdicts : `IDENTIQUE`, `ECARTS_D_ARRONDI` (écarts d'un pas d'arrondi sur les boîtes, les scores, `u` ou `point`),
`DIFFERENT` (avec la première divergence, les franchissements manquants et supplémentaires) et `NON_COMPARABLE`
(entrées, versions, processeur, threads ou étendue différents). Le code de sortie vaut 0 seulement pour `IDENTIQUE`.
Les rapports vont dans `runs/non_regression/comparaisons/` par défaut ; l'outil refuse d'écrire dans un run comparé.

Contrôles du comparateur :
- 17 tests N0 sur des runs synthétiques : copie exacte, métadonnées seules, ancien manifeste, un pas d'arrondi,
  boîte décalée, direction inversée, temps décalé, franchissement manquant ou supplémentaire, identifiant de piste,
  statut de passage et statistiques, version de paquet, threads, run limité en mode complet et tronqué, borne trop
  large, divergence avant la borne, absence d'écriture dans les runs comparés.
- Sur des données réelles, l'essai de 20 s (`runs/essais/20261103T172153Z-b5f6a3`) est comparé à S1, avec les
  rapports dans `runs/non_regression/controles_comparateur/` :

| Mode | Verdict attendu | Verdict obtenu | Détail |
|---|---|---|---|
| Tronqué à 20 000 ms | IDENTIQUE | IDENTIQUE | 201 images sur 201, 21 franchissements sur 21, statistiques égales |
| Complet | NON_COMPARABLE | NON_COMPARABLE | `limite_s`, images décodées et analysées, bilan du temps différents |
| Tronqué à 300 000 ms | DIFFERENT | DIFFERENT | 3 000 images contre 201 ; franchissement manquant : piste 23, sortie, 181 900 ms |

Les empreintes SHA-256 des fichiers de S1 et de l'essai sont inchangées après ces contrôles
(`docs/PLAN_DECOUPLAGE_DETECTEUR.md` §3.5).

### Découplage du détecteur (D-025) : rejouées de non-régression

Configuration `configs/s1_g420.yaml` inchangée (même empreinte canonique), threads ONNX Runtime par défaut, même poste,
environnement conforme à `requirements.lock`. Rejouées dans `runs/non_regression/`, rapports dans
`runs/non_regression/comparaisons/`.

| Étape | Run | Code | Comparé à | Verdict |
|---|---|---|---|---|
| Rejouée avant refactoring | `20261111T120056Z-1a879f` (complet) | commit `3d34b9b`, arbre propre | S1 `20261103T172241Z-b3b507` | **IDENTIQUE** |
| Rejouée courte après refactoring | `20261111T124527Z-e027d2` (`--limite-s 20`) | `3d34b9b` + refactoring non commité | essai `20261103T172153Z-b5f6a3` ; S1 tronqué à 20 000 ms | **IDENTIQUE** ; **IDENTIQUE** |
| Rejouée complète après refactoring | `20261111T124731Z-828fc6` (complet) | `3d34b9b` + refactoring non commité | S1 ; rejouée `20261111T120056Z-1a879f` | **IDENTIQUE** ; **IDENTIQUE** |

- Les verdicts IDENTIQUE couvrent 3 000 images sur 3 000, 22 franchissements sur 22 (identifiants, pistes, directions,
  `t_ms`, `num_image`), les passages dérivés, les doublons probables, les débuts et fins de pistes et les statistiques
  recalculées. Ils ne relèvent aucun écart d'arrondi.
- **Provenance de S1 établie a posteriori** : le code du commit `3d34b9b`, dont le chemin d'analyse est inchangé
  depuis `2517bc1`, reproduit S1 à l'identique. S1 reste la référence.
- Les rejouées après refactoring ont été produites avant le commit, sur l'arbre de travail. Leurs manifestes donnent
  `git_commit` = `3d34b9b` et `git_dirty` = vrai, et listent exactement `passages/run.py`, `passages/detecteur.py` et
  `tests/test_detecteur.py`. Empreintes git de ces fichiers pendant les rejouées, identiques à celles du commit du
  refactoring : `a32a393e…` (`run.py`), `cac94128…` (`detecteur.py`), `7874b9bf…` (`test_detecteur.py`).
- Durées de calcul notées sans interprétation : 2 621 s et 1 516 s pour les deux rejouées complètes, contre 616 s le
  2026-11-03, avec la même configuration et le même poste. La cause n'est pas mesurée ; ce n'est pas un benchmark.
- Ce résultat établit une **équivalence de comportement**, pas une justesse : S1 n'est toujours pas annotée.

### Type `Detections` (étape 1 de `docs/CONCEPTION_MULTICLASSE.md`) : rejouées de non-régression (2026-11-11)

Changement : `Detector.detecter` rend un `Detections` (boîtes float32 (N, 4), scores float32 (N,), noms de classe,
indices de classe du modèle en int64), dont les invariants sont vérifiés à la construction. `AdaptateurYolox` reprend
sans copie les tableaux de `DetecteurYolox` et y ajoute la classe `person` (indice COCO 0). `run.py` ne fait que lire
`boites` et `scores` ; la classe transmise au suivi reste forcée à 0. Inchangés : `passages/detection.py`, ByteTrack,
seuils, configuration (empreinte git `cb4ab36a…`), événements, identifiants de piste, format des runs.

Portée de l'immuabilité : `Detections` est un `dataclass(frozen=True)`. Sa **structure** est figée : on ne peut pas
réaffecter ses champs. Le **contenu** de ses tableaux NumPy ne l'est pas : `une_classe` reprend sans copie les
tableaux du détecteur, qui restent partagés et modifiables en place par quiconque en détient une référence. Le
pipeline actuel ne les modifie pas (`run.py` les convertit par `astype`, qui crée une copie). Un futur consommateur
qui voudrait les modifier devra d'abord les copier.

Tests : 68 passent, aucun ignoré. `tests/test_detecteur.py` couvre :
- les invariants (formes, types, longueurs, noms vides, immuabilité) et le cas vide ;
- la reprise sans copie, et l'adaptateur sur un faux YOLOX, vide ou non ;
- l'égalité de l'adaptateur et de YOLOX sur deux images synthétiques. Elles ne donnent **aucune détection**, donc ce
  test ne couvre que le cas vide ;
- l'égalité de l'adaptateur et de YOLOX sur la première image de S1, avec au moins une détection.

Rejouées dans `runs/non_regression/multiclasse_etape1/`, rapports dans son sous-dossier `comparaisons/`. Code :
commit `5a6ddbc` plus des modifications non commitées. Les manifestes listent `passages/detecteur.py`,
`passages/run.py`, `tests/test_detecteur.py` et `docs/CONCEPTION_MULTICLASSE.md`, ce dernier non suivi par git.
Empreintes git des fichiers modifiés, identiques avant et après les rejouées : `d6a72557…` (`detecteur.py`),
`dc786b85…` (`run.py`), `b8a60a7a…` (`test_detecteur.py`). Après les rejouées, seule la docstring de
`test_detecteur.py` a été corrigée (elle disait toutes les images synthétiques). Ce fichier n'intervient pas dans
l'analyse ; `detecteur.py` et `run.py` sont commités avec les empreintes testées.

| Run | Étendue | Comparé à | Verdict |
|---|---|---|---|
| `20261111T132821Z-a4962c` | `--limite-s 20` | essai `20261103T172153Z-b5f6a3` ; S1 tronqué à 20 000 ms ; rejouée `20261111T124527Z-e027d2` | **IDENTIQUE** ×3 |
| `20261111T133101Z-4c907c` | complète | S1 `20261103T172241Z-b3b507` ; rejouée `20261111T124731Z-828fc6` | **IDENTIQUE** ×2 |

La rejouée complète couvre 3 000 images sur 3 000 et 22 franchissements sur 22, avec 24 pistes et 14 passages
retenus, sans écart d'arrondi. Les empreintes SHA-256 de S1 et de l'essai sont inchangées. Durée de calcul :
2 532 s, notée sans interprétation. Équivalence de comportement, pas une mesure de justesse.

### Décodage multi-étiquette (étape 2, D-026) : rejouées de non-régression (2026-11-11)

Changement : `DetecteurYolox` décode une liste de classes COCO (par défaut la seule classe 0), avec un score
multi-étiquette et une NMS par classe ; il vérifie à la construction que la sortie déclarée du modèle compte 85
colonnes ; `AdaptateurYolox` nomme les indices ; `config.valider` refuse `analyse.classes`. `creer_detecteur` ne
transmet aucune classe : la production reste en mode `person`. Inchangés : `run.py` (empreinte git `dc786b85…`),
`configs/s1_g420.yaml` (`cb4ab36a…`, empreinte canonique `1887f2c2…`), ByteTrack, identifiants de piste, événements,
format des runs, comparateur. Proposition et corrections : `docs/ETAPE2_DECODAGE_MULTICLASSE.md`.

Tests (`tests/test_detection_multiclasse.py`, sorties de modèle synthétiques sauf T10) :
- l'oracle, copie figée de `decoder` et `nms` du commit `878f08f`, a d'abord été vérifié égal au bit près au décodeur
  **non modifié** sur 20 sorties synthétiques, dont 10 avec de nombreux scores ex aequo (T1, commit `b194549`) ;
- mode `person` égal à l'oracle au bit près, ordre compris : 20 sorties synthétiques (T2), ex aequo et stabilité sur
  dix appels (T3), score égal à `float32(0,1)` exclu et valeur suivante gardée (T4), personne non dominante gardée
  (T5), chevauchements autour de 0,45 (T6), cas vide (T7), classe non demandée (T8), bornage après la NMS (T9), sortie
  réelle du modèle sur la première image de S1 (T10) ;
- multi-classe : vocabulaire et empreinte de la liste (T11), filtrage (T12), personne et voiture chevauchantes gardées
  (T13), même ancre pour deux classes (T14), doublon « car » / « truck » connu (T15), ordre de sortie (T16), bloc des
  personnes égal au mode `person` seul (T17), classes invalides (T18), adaptateur (T19), fabrique en mode `person`
  (T20) ; sortie à 84, 86 colonnes ou dimension symbolique ou inconnue refusée, 85 acceptée sans inférence, vrai
  modèle à `[1, 8400, 85]` ;
- configuration : `analyse.classes` refusée sans mutation, configuration S1 acceptée avec son empreinte (T21) ;
- `tests/test_detecteur.py` adapté au triplet `(boîtes, scores, ids)` (T22).

Résultats : **171 tests passent sur ce poste, aucun ignoré**. Dans un clone temporaire sans modèle ni vidéo : 166
passent, 5 ignorés (les tests qui exigent le modèle ou la vidéo S1).

Rejouées dans `runs/non_regression/multiclasse_etape2/`, rapports dans son sous-dossier `comparaisons/`. Code : commit
`9708503`, **arbre propre** (manifestes : `git_dirty` faux, aucun fichier modifié). Threads ONNX Runtime par défaut.

| Run | Étendue | Comparé à | Verdict |
|---|---|---|---|
| `20261111T155110Z-f79da9` | `--limite-s 20` | essai `20261103T172153Z-b5f6a3` ; S1 tronqué à 20 000 ms ; rejouée `20261111T132821Z-a4962c` | **IDENTIQUE** ×3 |
| `20261111T155334Z-bc1823` | complète | S1 `20261103T172241Z-b3b507` ; rejouée `20261111T133101Z-4c907c` | **IDENTIQUE** ×2 |

- Rejouée de 20 s : 201 images sur 201, 21 franchissements sur 21, aucun écart d'arrondi.
- Rejouée complète : 3 000 images sur 3 000, 22 franchissements sur 22, 24 pistes, 14 passages retenus, aucun écart
  d'arrondi.
- Empreintes SHA-256 inchangées après les rejouées : S1 (`evenements.json` `701EFF4E…`, `manifest.json` `C77AB752…`,
  `pistes.jsonl` `80831D0C…`), essai (`E04ED57E…`, `96942141…`, `47D65A7F…`), vidéo S1 (`19A8159A…CE4`). R1 et R2 non
  utilisées.
- Durées de calcul relevées dans les manifestes, notées sans interprétation (ce n'est pas un benchmark) : 115,2 s pour
  la rejouée de 20 s, 1 582,5 s pour la rejouée complète.
- Équivalence de comportement, **pas une mesure de justesse**. Aucune autre classe que `person` n'a été analysée sur
  une vidéo.
