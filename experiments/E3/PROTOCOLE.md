# E3 — Contrôle des horodatages et des extraits de preuve

Version du protocole : **1** (2026-11-03). Statut : **terminé pour S1 (extrait de réglage)** ; S2 à S4 non traités ;
R1 et R2 volontairement non traités.

## 1. Questions

1. Le temps vidéo de chaque image est-il lisible de façon fiable (horodatages présents, croissants, cohérents) ?
2. Quand on demande la vignette à l'instant `T`, obtient-on **exactement** l'image attendue ?
3. Quand on demande un extrait `[T − avant, T + après]`, commence-t-il à la bonne image et contient-il les bonnes images ?
4. L'outil de lecture utilisé pour annoter (E1) affiche-t-il le temps de l'image réellement affichée ?

Aucun seuil de précision du produit n'est fixé ici. Le critère est un critère de **justesse des preuves** :
une vignette de preuve doit montrer l'image de l'événement, pas une image voisine.

## 2. Conventions

- **Temps vidéo** (`docs/DATA_AND_RULES.md` R-T1) : temps de présentation de l'image, ramené au début du flux.
- **Image visible à l'instant T** : la dernière image dont le temps est ≤ T. C'est l'« image attendue » du script.
- Un événement est toujours daté sur une image : le cas qui compte pour les preuves est donc l'instant
  **calé sur une image** (`image_exacte`). Les instants quelconques (`quelconque`) servent à révéler les conventions
  de l'outil.
- ffmpeg mesure `-ss` à partir du `start_time` du format. Si la première image vidéo ne commence pas à ce
  `start_time`, il faut convertir ; le script affiche ce décalage.

## 3. Méthode

Script : `experiments/E3/controle_temps.ps1` (PowerShell + ffmpeg/ffprobe, aucune dépendance supplémentaire).

1. **Chronologie** : ffprobe lit le temps de chaque image décodée (`best_effort_timestamp_time`, et l'absence éventuelle
   de PTS) ; ffmpeg calcule l'empreinte MD5 de chaque image décodée (`framemd5`). Les deux listes doivent avoir
   le même nombre d'images, sinon le script s'arrête.
2. **Instants** : tirage reproductible (graine) d'instants quelconques, chacun doublé de sa version calée sur une image.
3. **Méthodes testées** :
   - `vignette_ss_avant_entree` : `ffmpeg -ss T -i fichier` (recherche rapide dans l'entrée) ;
   - `vignette_ss_apres_entree` : `ffmpeg -i fichier -ss T` (décodage depuis le début, lent mais de référence) ;
   - `extrait_copie` : `-ss` en entrée + `-c copy` (sans réencodage) ;
   - `extrait_reencode_sans_perte` : `-ss` en entrée + réencodage FFV1 sans perte. Le sans-perte sert uniquement
     à retrouver les images par empreinte ; la qualité des extraits finaux est un réglage séparé.
4. **Identification** : l'image obtenue (première image de la vignette ou de l'extrait) est retrouvée par son empreinte
   dans la chronologie. Si plusieurs images ont la même empreinte (images dupliquées), le statut est `ambigu`.
5. **Sorties** (non versionnées) : `out/<fichier>/chronologie.csv`, `mesures.csv`, `resume.txt`.

Commandes :

```powershell
# mires synthétiques (CFR, VFR avec trous, MPEG-TS débutant à 10 s)
powershell -ExecutionPolicy Bypass -File experiments\E3\controle_temps.ps1 -GenererMires
# fichier réel ; -SansSeekSortie évite la méthode lente sur les longues vidéos
powershell -ExecutionPolicy Bypass -File experiments\E3\controle_temps.ps1 -Video data\videos\...\fichier -NbInstants 8
```

## 4. Constats au 2026-11-03

Outils : ffmpeg/ffprobe 8.1.2 (build gyan.dev « full »), Windows, Windows PowerShell. Ces constats valent pour ces
fichiers et cette version ; ils ne sont pas généralisables sans nouvelle mesure.

### 4.1 Mires synthétiques — niveau N0

8 instants quelconques et 8 calés par mire.

| Mire | Vignette `-ss` avant `-i` (calé) | Vignette `-ss` après `-i` (calé) | Extrait copie | Extrait réencodé (calé) |
|---|---|---|---|---|
| MP4, 25 i/s constant, GOP 50 | 0 image d'écart | 0 | commence 1 à 41 images **trop tôt** (jusqu'à −1,64 s) | 0 |
| MP4, cadence variable (trous), GOP 60 | 0 | 0 | 1 à 45 images trop tôt (jusqu'à −2,17 s) | 0 |
| MPEG-TS, début à 11,4 s | **0 à 35 images trop tard** (jusqu'à +1,4 s) | 0 | −1 à +46 images (jusqu'à +1,84 s, début manquant) | **0 à 46 images trop tard** |

Lecture :
- Sur un instant quelconque, ffmpeg renvoie la **première image dont le temps est ≥ T**, soit une image après l'image
  visible : c'est une convention, sans effet sur les événements, qui sont calés sur une image.
- La copie sans réencodage démarre sur une image clé : l'extrait contient des images en trop avant le début demandé.
- Sur le MPEG-TS, la recherche rapide en entrée renvoie des images fausses, en retard, alors que la recherche après
  l'entrée est juste. Point à surveiller : une future caméra produira probablement des segments MPEG-TS
  (`docs/ARCHITECTURE.md` §7).

### 4.2 Un fichier réel : CAVIAR `OneStopEnter2front.mpg` — 4 + 4 instants

- Flux MPEG-1 brut sans conteneur ; 2 725 images ; **908 sans PTS** ; intervalle régulier de 40 ms sauf un trou
  de 80 ms après la première image et une dernière image sans temps, ramenée à 0 ; 15 images identiques à une autre
  (cohérent avec les images dupliquées signalées par CAVIAR).
- Vignette, recherche en entrée : 1 à 15 images **trop tôt** (jusqu'à −0,6 s).
- Vignette, recherche après l'entrée : 1 image trop tard sur les instants calés. L'origine n'est pas établie ;
  le trou de 80 ms en tête de flux est une piste.
- Extrait copie vers MKV : **échec** (flux sans horodatages).
- Extrait réencodé : 1 à 16 images trop tôt.

Conclusion limitée à ce fichier : il ne doit pas être analysé tel quel ; il faut d'abord le normaliser
(hypothèse H-E3-1 ci-dessous).

### 4.3 Extrait de réglage S1 : MEVA `2018-03-07.16-50-01.16-55-01.school.G420.r13.avi` — 6 + 6 instants

Fichier original conservé sans modification (sha256 `19A8159A…6CE4`, `experiments/E0/INVENTAIRE.md`). **Aucune
transformation du fichier** : rien n'a été réencodé ni remultiplexé. Seule la façon de calculer le temps est choisie.

Constats (ffprobe/ffmpeg 8.1.2 et PyAV 18.1.0) :
- AVI, H.264 High **avec images B**, 1920×**1072** (et non 1080), cadence déclarée 30/1, base de temps 1/30.
- 9 000 paquets, **aucun paquet vide** (pas d'image sautée signalée par le conteneur), `dts` continus 0…8999,
  une image clé toutes les 60 images ; 9 000 images décodées, aucune empreinte en double.
- **Les PTS lus ne sont pas des instants de présentation.** Le démultiplexeur AVI attribue `pts = dts + 1` dans
  l'ordre de **décodage** ; le décodeur rend les images dans l'ordre d'**affichage** avec ces valeurs : **4 328 reculs
  de PTS** sur les 9 000 images (manifeste du run `20261103T172241Z-b3b507`). ffprobe, lui, ne trouve **aucun PTS** (9 000 images
  `pts` absent) et calcule un temps « best effort » croissant, première image à 66,7 ms ; les **deux dernières images**
  (vidées du décodeur en fin de fichier) reçoivent le temps 0.
- Pour les images 0 à 8 997, le temps best effort de ffmpeg vaut exactement `rang/30 + 66,667 ms`
  (écart maximal 0,33 ms, arrondi du CSV).

Temps retenu pour S1 — **reconstruit, et hypothèse de travail propre à S1** : `t = rang d'affichage × 1/30 s` (mode
`rang_cadence_nominale` de `passages/video.py`).
- Éléments **compatibles** avec cette hypothèse : cadence déclarée 30/1, 9 000 paquets sans paquet vide, `dts`
  continus, 9 000 images ≈ 300 s, soit l'écart entre les heures du nom de fichier (16:50:01 → 16:55:01, précision 1 s).
- Ce qui **ne prouve pas** la régularité : le nombre de paquets et l'absence de paquet vide disent seulement que le
  conteneur ne signale pas d'image sautée. Une caméra ou un enregistreur peut avoir perdu, dupliqué ou capté des images
  à intervalles irréguliers **avant** l'encodage, sans aucune trace dans le fichier. L'accord avec ffmpeg n'est pas
  une confirmation indépendante : ffmpeg dérive son temps des mêmes `dts` séquentiels.
- Vérification indépendante possible, non faite : comparer, sur des mouvements réguliers (pas, portes), les vitesses
  apparentes entre portions de la vidéo, ou trouver une horloge de référence dans la scène. Aucune horloge incrustée
  n'est visible dans S1.
- Le décalage de 66,7 ms est une convention de ffmpeg, pas un retard réel.

Extraction de preuves sur S1 (instants exprimés dans le temps de ffmpeg, soit `t + 66,667 ms`) :

| Méthode | Instants calés sur une image | Instants quelconques |
|---|---|---|
| Vignette `-ss` avant `-i` | 0 image d'écart (6/6) | 0 à +1 image (convention « première image ≥ T ») |
| Vignette `-ss` après `-i` | 0 (6/6) | 0 à +1 |
| Extrait copie vers MKV | **échec** (6/6) | échec |
| Extrait réencodé | 0 (6/6) | 0 à +1 |

Lecteur d'annotation (`passages/annotate.py`, question 4) : `experiments/E3/controle_lecteur.py` compare, au pixel près
(MD5), l'image obtenue par saut (avant et arrière, autour des images clés) à l'image de même rang en décodage
séquentiel : **48 sauts sur 48 identiques**. L'outil affiche le temps calculé pour le rang affiché, selon le même mode
que l'analyse.

Conséquences :
- Pour ce fichier, le mode `pts` est refusé par le code (PTS non croissants) ; le mode `rang_cadence_nominale` refuse
  tout fichier contenant un paquet vide.
- Une preuve se désigne par le **rang d'image** ; la conversion vers le temps de ffmpeg (`+66,667 ms`) est propre à ce
  fichier et ne doit pas être généralisée. Les deux dernières images ne sont pas adressables par temps dans ffmpeg.
- H-E3-3 (« chronologie MEVA régulière ») **reste une hypothèse**, y compris pour S1 : le temps reconstruit est
  régulier par construction, ce qui ne dit rien de la régularité de la capture.

## 5. Hypothèses issues des constats, à tester

- **H-E3-1** : remultiplexer un flux brut dans un conteneur en régénérant les temps à la cadence déclarée
  (25 i/s pour CAVIAR) donne une chronologie régulière et des extraits justes. À vérifier avec ce même script sur le
  fichier normalisé ; conserver l'empreinte du fichier original et celle du fichier normalisé.
- **H-E3-2** : une extraction en deux temps (recherche rapide quelques secondes avant, puis sélection par décodage
  de l'image de temps exact) est juste sur tous les formats et nettement plus rapide que le décodage depuis le début.
  Elle reste à écrire et à mesurer.
- **H-E3-3** : les clips MEVA (AVI, H.264, 30 i/s) ont une chronologie régulière. Rien n'est mesuré à ce jour.

## 6. Étapes restantes

- [x] S1 : chronologie, vignettes, extraits, lecteur d'annotation (§4.3).
- [ ] Exécuter le script sur S3 et S4 (MEVA) et S2 (CAVIAR, normalisé ou non). Ne pas l'exécuter sur R1 et R2 avant
      la fin des réglages : la chronologie ne montre pas le contenu, mais on garde la règle simple.
- [ ] Tester H-E3-1 et H-E3-2. La copie sans réencodage échoue sur S1 comme sur CAVIAR : l'extrait de preuve
      sera réencodé.
- [ ] Contrôler la lecture d'un extrait dans un navigateur (lecteur HTML5) : première image affichée et position à
      `#t=` ; contrôle visuel noté, car le navigateur ne peut pas être mesuré par empreinte.

## 7. Décisions permises par E3

- Méthode d'extraction des vignettes et extraits retenue pour le produit, par type de fichier.
- Règle de normalisation à l'enregistrement d'une vidéo (EF-01) pour les flux sans horodatage fiable.
- Précision temporelle annoncée dans les rapports (exprimée en images, avec la méthode utilisée).
