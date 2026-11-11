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
