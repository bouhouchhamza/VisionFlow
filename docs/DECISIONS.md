# Journal des décisions

> Statuts : **[Confirmé]** fait établi ou décision prise par le porteur du projet ·
> **[Proposition]** recommandée, en attente de validation · **[Hypothèse]** dépend d'une expérience ·
> **[Ouvert]** non décidée.
>
> Règles du journal : une décision n'est jamais effacée ; si elle change, on ajoute une entrée qui la remplace
> et on note « remplacée par D-xxx ». Une proposition ne devient confirmée que par validation explicite du porteur.

Dernière mise à jour : 2026-11-11.

## Synthèse

| ID | Sujet | Statut | À trancher quand |
|---|---|---|---|
| D-001 | Cadrage documentaire avant implémentation | Confirmé | — |
| D-002 | Un déploiement indépendant par entreprise | Confirmé | — |
| D-003 | Observation vidéo ≠ preuve de vente, paiement ou fraude | Confirmé | — |
| D-004 | Temps vidéo comme référence de datation | Confirmé (règle) / mise en œuvre précisée par D-023 | — |
| D-005 | Premier scénario : comptage de passages | **Confirmé pour le prototype** (2026-11-03) ; produit : multisectoriel | G0 pour la suite |
| D-006 | Stack : tout Python | **Confirmé pour le prototype** (2026-11-03) ; non adopté pour le produit | G0 |
| D-007 | Stockage : SQLite + fichiers de run | Proposition (le prototype n'utilise que des fichiers) | T1.2 |
| D-008 | Détecteur : licences du code, des poids et des données | Ouvert pour le produit ; choix du prototype : D-022 | G0 |
| D-009 | Caméra comme producteur de segments | Proposition | Quand une caméra est engagée |
| D-010 | Emplacement du dépôt git | **Confirmé** (2026-11-03) | — |
| D-011 | Trois couches : brut, corrections, calculé | Confirmé (règle) / Proposition (modèle) | T1.2 |
| D-012 | Floutage des visages dans les preuves | Ouvert | Avant toute démonstration externe |
| D-013 | Version de Python | **Confirmé pour le prototype : 3.11.9** | Avant octobre 2027 (fin de support de 3.11) |
| D-014 | Transfert des corrections vers un nouveau run | Proposition : non en V1 | G1 |
| D-015 | Revue promue en annotation de référence | Proposition : non en V1 | G1 |
| D-016 | Pas d'identification de personnes | Proposition | Validation du porteur |
| D-017 | Nom du produit et de la commande | Ouvert | T1.1 |
| D-018 | Cadre juridique d'un déploiement client | Ouvert | Avant tout pilote |
| D-019 | Normalisation des vidéos à l'enregistrement | Hypothèse | E3 (H-E3-1) |
| D-020 | Réserve d'évaluation fixée avant tout réglage | Confirmé pour E0–E2 (règle) | — |
| D-021 | Licence de l'ffmpeg livré avec un déploiement | Ouvert (complété : FFmpeg embarqué par PyAV) | Avant tout déploiement client |
| D-022 | Détecteur, suivi et versions du prototype | Confirmé pour le prototype | Revoir à G0 |
| D-023 | Mode de calcul du temps choisi par fichier après E3 | Proposition (appliquée au prototype) | G0 |
| D-024 | Annotation de référence : faits observés, maintien en paramètre | Proposition (protocole E1 v2) | Après la passe 1 de S1 |
| D-025 | Détecteur derrière une interface ; refactorings vérifiés par non-régression | **Confirmé pour le prototype** (interface, 2026-11-11) / Proposition (règle générale) | Second détecteur ou classes |

## Entrées

### D-001 — Cadrage documentaire avant implémentation · Confirmé
- **Contexte** : produit démarré par un développeur seul ; dossier vide au 2026-11-03.
- **Décision** : rédiger vision, exigences, architecture, données et règles, plan et décisions avant tout code.
  Aucune dépendance installée pendant le cadrage.
- **Conséquence** : la première tâche de code (T1.1) attend la porte G0.

### D-002 — Un déploiement indépendant par entreprise · Confirmé
- **Conséquence** : pas de multi-tenant, pas de séparation de données par client dans une base commune ;
  une instance = un répertoire de données + une configuration. Les différences entre clients passent par la configuration.

### D-003 — Une observation vidéo ne prouve ni vente, ni paiement, ni fraude · Confirmé
- **Conséquence** : vocabulaire contrôlé (`DATA_AND_RULES.md` §11) ; les écarts sont « à examiner » et listent
  des causes non suspectes possibles ; vérification automatique des mots interdits dans les rapports (T3.3).

### D-004 — Temps vidéo comme référence · Confirmé (règle) / Proposition (mise en œuvre)
- **Décision** : un événement observé est daté par le temps de la vidéo. Mise en œuvre proposée : PTS ramené au début
  du flux, en ms entières ; heure murale = début déclaré + temps vidéo.
- **Alternative écartée** : numéro d'image ÷ cadence (faux sur cadence variable) ; horloge système (date le traitement,
  pas l'observation).
- **À vérifier** : E3.
- **Complément (2026-11-03)** : E3 sur S1 montre que les PTS lus dans un AVI avec images B ne sont pas des instants de
  présentation. Le calcul du temps est donc choisi par fichier : D-023.

### D-005 — Premier scénario : comptage de passages · Proposition
- **Raisons** : données plus faciles à trouver, modèle pré-entraîné probablement suffisant, annotation peu coûteuse,
  erreur mesurable, briques réutilisables pour le scénario B. Comparaison complète : `REQUIREMENTS.md` §2.
- **Compromis accepté** : valeur commerciale initiale plus faible que B ; lien avec les ventes seulement indirect.
- **Condition** : E0 doit montrer des vues de passage exploitables dans les vidéos autorisées.
- **Décision du porteur (2026-11-03)** : scénario A retenu **pour le prototype uniquement**. La vision produit reste la
  supervision opérationnelle multisectorielle ; A n'est pas le périmètre du produit.

### D-006 — Stack : tout Python · Proposition
- **Options** : (1) tout Python avec interface web rendue côté serveur ; (2) analyse Python + application TypeScript.
  Détail : `ARCHITECTURE.md` §8.
- **Raisons** : un seul langage pour un développeur seul ; écosystème de vision natif.
- **Compromis accepté** : interface de revue moins riche ; réversible grâce à la frontière analyse / interface.
- **Condition** : E2 confirme que les paquets nécessaires s'installent et tournent sur le poste.
- **Décision du porteur (2026-11-03)** : socle Python retenu **pour le prototype uniquement** (composants : D-022).
  L'option 2 et l'interface restent ouvertes pour le produit.

### D-007 — Stockage : SQLite + fichiers de run · Proposition
- **Raisons** : déploiement mono-entreprise, un utilisateur local, aucun serveur à administrer ; preuves sous forme de
  fichiers dans le répertoire du run.
- **Révision si** : plusieurs utilisateurs simultanés, ou volume d'événements incompatible (mesuré après E2).

### D-008 — Détecteur : licences du code, des poids et des données · Ouvert
- **Enjeu** : un détecteur combine du code, des poids et des données d'entraînement, chacun avec ses conditions
  (`ARCHITECTURE.md` §8.1). Une licence AGPL ou GPL **n'interdit pas l'usage commercial**. Elle impose de fournir
  le code source correspondant aux destinataires ; avec l'AGPL, cela vaut aussi pour les utilisateurs par réseau.
- **Constat (2026-11-03)** : Ultralytics publie code et modèles YOLO sous AGPL-3.0. Selon sa propre lecture, cela
  couvre aussi les modèles entraînés avec son code, et il vend une licence Enterprise. C'est la position de l'éditeur ;
  elle est à examiner avant engagement.
- **Options** : (a) accepter les obligations AGPL pour le code concerné et le fournir aux clients ; (b) licence
  commerciale de l'éditeur ; (c) composant sous licence permissive.
- **Proposition** : en E2, tout candidat est permis à condition de consigner ici les licences de son code, de ses poids
  et, si elles sont connues, de ses données d'entraînement. Le choix (a), (b) ou (c) se fait à G0 selon les résultats
  et le modèle commercial.
- **Prototype (2026-11-03)** : composant sous licence permissive pour le code (option c), voir D-022. Cela ne tranche
  pas la question pour le produit : la licence des poids et celle des données d'entraînement restent non établies.

### D-009 — Caméra comme producteur de segments · Proposition
- **Décision proposée** : une future caméra produit des segments vidéo enregistrés, traités par le même exécuteur.
- **Raisons** : un seul chemin d'analyse à maintenir ; aucune architecture temps réel à construire tant qu'aucun besoin
  n'existe. Détail et contraintes à respecter dès la V1 : `ARCHITECTURE.md` §7.
- **Compromis** : latence égale à la durée d'un segment ; acceptable pour des rapports, pas pour des alertes immédiates.

### D-010 — Emplacement du dépôt git · Confirmé (2026-11-03)
- **Constat initial** : un dépôt git sans commit existe à la racine `C:\` (branche `master`) et englobait le projet.
- **Décision (autorisée par le porteur)** : dépôt indépendant créé dans `C:\Users\pc\Videos\camera_gestionnaire`
  (branche `main`). `git rev-parse --show-toplevel` renvoie désormais exactement ce dossier. `.gitignore` exclut
  secrets, environnements virtuels, vidéos, poids de modèles, données et sorties volumineuses.
- **Règles** : ne jamais modifier ni supprimer le dépôt de `C:\` ; aucun ajout global ; aucun push sans demande explicite.
- **Vérification** : empreinte des 173 fichiers de `C:\.git` relevée avant et après l'opération, identique.
- **Reste ouvert** : savoir si le dépôt de `C:\` a été créé volontairement. Son dossier contient un sous-dossier `gk`,
  ce qui suggère un outil Git graphique. Ce point relève du porteur, pas du projet.

### D-011 — Trois couches de données · Confirmé (règle) / Proposition (modèle)
- **Règle confirmée** : distinguer observations brutes, corrections humaines et indicateurs calculés.
- **Modèle proposé** : `DATA_AND_RULES.md` §1–§5 ; annotations de référence séparées des corrections.

### D-012 — Floutage des visages dans les preuves · Ouvert
- **Options** : pas de floutage (vidéos autorisées, usage interne) ; floutage systématique des preuves ; floutage
  dans les rapports exportés seulement.
- **Impact** : coût de calcul, risque de rendre une preuve illisible, conformité. À trancher avant de montrer des preuves
  à un tiers.

### D-013 — Version de Python · Confirmé pour le prototype (3.11.9)
- **Constat** : Python 3.14.0 (défaut) et 3.11 installés.
- **Proposition initiale** : 3.11 pour le projet si les paquets d'inférence ne sont pas disponibles en 3.14 ; trancher par E2.
- **Décision (2026-11-03)** : le porteur a demandé Python 3.11 sur CPU pour le prototype ; environnement `.venv` créé avec
  `py -3.11 -m venv .venv` (3.11.9, pip 24.0).
- **Conséquences constatées à l'installation** : les dernières versions de PyAV (19.x), NumPy (2.5.x) et SciPy (1.18.x)
  exigent Python ≥ 3.12. Le prototype fige donc des versions antérieures (D-022). Python 3.11 n'est plus maintenu
  après octobre 2027 : la montée de version est à planifier avant.

### D-014 — Transfert des corrections vers un nouveau run · Proposition : non en V1
- **Raisons** : les observations de deux runs ne se correspondent pas une à une ; un transfert automatique pourrait
  appliquer une décision humaine à un événement différent.
- **Plus tard** : transfert assisté par appariement temporel, chaque correction transférée étant marquée et revalidée.

### D-015 — Revue promue en annotation de référence · Proposition : non en V1
- **Raison** : une revue part des propositions de la machine et tend à manquer ce que la machine a manqué ;
  l'utiliser comme vérité terrain surestimerait le rappel.

### D-016 — Pas d'identification de personnes · Proposition
- **Décision proposée** : ni reconnaissance faciale, ni ré-identification entre vidéos ou journées, ni distinction
  nominative client / salarié. Identifiants de piste locaux au run.
- **Raisons** : réduire le risque juridique et éthique ; le besoin (flux, indicateurs) ne l'exige pas.

### D-017 — Nom du produit et de la commande · Ouvert
- Le nom du dossier (`camera_gestionnaire`) n'est pas considéré comme le nom du produit.

### D-018 — Cadre juridique d'un déploiement client · Ouvert
- Personnes filmées = données personnelles ; règles spécifiques à la vidéo sur le lieu de travail. À faire vérifier par
  une personne compétente avant tout pilote. Sans objet pour les vidéos de démonstration dont l'usage est autorisé.

### D-019 — Normalisation des vidéos à l'enregistrement · Hypothèse
- **Constat E3** : un flux MPEG-1 brut (CAVIAR) a 908 images sur 2 725 sans PTS, une durée annoncée fausse (1,2 s pour
  109 s), et la copie d'extrait échoue.
- **Proposition à tester** : à l'enregistrement, détecter ces cas et produire une copie remultiplexée avec des temps
  régénérés à la cadence déclarée ; l'analyse porte sur la copie ; la fiche garde les deux empreintes et la méthode.

### D-020 — Réserve d'évaluation fixée avant tout réglage · Confirmé (règle)
- Les extraits R1 et R2 (`experiments/E0/INVENTAIRE.md` §4) ont été choisis par règle le 2026-11-03, sans visionnage.
  Ils ne servent qu'à évaluer une configuration gelée. Au-delà de trois évaluations, la réserve est considérée
  comme usée et renouvelée selon la même règle.

### D-021 — Licence de l'ffmpeg livré avec un déploiement · Ouvert
- L'ffmpeg installé sur le poste est un build GPL v3 (constaté). Pour les essais, cela ne pose pas de question.
  Pour un déploiement livré, il faut choisir entre fournir ce build (obligations GPL sur ffmpeg lui-même) et un build
  LGPL, puis vérifier que les fonctions nécessaires, dont l'encodage des extraits, restent disponibles.
- **Complément (2026-11-03)** : le wheel PyAV 18.1.0 embarque ses propres bibliothèques FFmpeg 8.1.2. Elles se déclarent
  « LGPL version 3 or later » (configuration avec `--enable-version3`, sans `--enable-gpl`), mais le wheel contient aussi
  les DLL `libx264` et `libx265`, qui sont des bibliothèques GPL. Le prototype n'utilise PyAV que pour décoder ;
  la vidéo annotée est encodée par l'ffmpeg externe. Statut juridique de cette distribution : non établi, à examiner
  avec le reste de D-021.

### D-022 — Détecteur, suivi et versions du prototype · Confirmé pour le prototype (2026-11-03)
- **Demande du porteur** : choisir un détecteur et une implémentation de suivi après vérification des licences du code et
  des poids et de la compatibilité avec Python 3.11 sur CPU ; consigner versions et dépendances.
- **Détecteur** : YOLOX-S, export ONNX officiel de la version `0.1.1rc0` du dépôt Megvii-BaseDetection/YOLOX
  (`models/yolox_s.onnx`, sha256 `C5C2D13E…8063`, 35 858 002 octets), entrée 640×640, classe COCO 0 (personne).
  - Code : Apache-2.0 (constaté dans le dépôt). Le pré- et post-traitement de `passages/detection.py` en est repris,
    avec mention.
  - Poids : publiés comme fichiers de la version `0.1.1rc0` du même dépôt ; **aucune licence distincte des poids
    trouvée** dans le README ni dans les notes de version. Statut juridique : **non établi**. Leur usage dans le
    prototype est un choix technique pour mesurer, pas une validation juridique.
  - Données d'entraînement : COCO. Conditions non vérifiées (page des conditions illisible sans JavaScript).
  - Écarté pour le prototype : Ultralytics YOLO (AGPL-3.0 et lecture extensive de l'éditeur, D-008) ; non pas interdit,
    mais ses obligations ne sont pas nécessaires pour mesurer.
- **Exécution** : ONNX Runtime 1.31.1 (MIT), fournisseur CPU, attente active des threads désactivée
  (`session.intra_op.allow_spinning = 0`). Mesuré sur 20 s de S1 (201 images analysées) : conversion d'image de
  62 à 12 ms par image, détection de 206 à 167 ms. Le premier essai a été supprimé ensuite, car produit avec le temps
  PTS erroné ; le second est `runs/essais/20261103T172153Z-b5f6a3`.
- **Suivi** : `trackers` 2.6.1 (Roboflow, Apache-2.0), `ByteTrackTracker`, réimplémentation déclarée « clean room »
  de ByteTrack. `supervision` 0.31.4 (MIT) ne contient plus ByteTrack ; il ne sert qu'au type `sv.Detections`.
  Le suivi reçoit le temps vidéo (`timestamp`) ; la durée de conservation d'une piste perdue vaut
  `lost_track_buffer / 30` secondes quelle que soit la cadence d'analyse (constaté dans le code de la bibliothèque).
- **Autres dépendances directes** (`requirements.txt`, transitives figées dans `requirements.lock`) : PyAV 18.1.0
  (BSD-3-Clause, FFmpeg embarqué : D-021), NumPy 2.4.6 (BSD-3-Clause et autres), OpenCV 4.14.0.94 (Apache-2.0 ;
  5.0 évité car `supervision` et `trackers` utilisent l'API 4), SciPy 1.17.1 (BSD, appariement un pour un), PyYAML 6.0.3
  (MIT), pytest 9.2.0 (MIT). Encodage de la vidéo annotée : ffmpeg externe 8.1.2 (build GPL v3, D-021).
- **Compatibilité** : toutes installées depuis des wheels Windows pour CPython 3.11 ; 21 tests unitaires passent.
- **Révision** : à G0, avec les mesures d'erreur ; un autre détecteur se compare sur la même annotation et la même règle.

### D-023 — Mode de calcul du temps choisi par fichier après E3 · Proposition (appliquée au prototype)
- **Constat** : `experiments/E3/PROTOCOLE.md` §4.3. Dans S1 (AVI, H.264 avec images B), les PTS lus sont attribués dans
  l'ordre de décodage et reculent dans l'ordre d'affichage.
- **Décision proposée** : chaque configuration déclare `video.mode_temps` :
  `pts` (défaut ; refuse des PTS non croissants) ou `rang_cadence_nominale` (rang d'affichage × 1/cadence ; refuse un
  paquet vide). Le second mode produit un **temps reconstruit**, marqué comme tel dans le manifeste et les événements
  (`images_temps_reconstruit`), réservé aux conteneurs à cadence fixe par construction après contrôle E3.
- **Ce que ce n'est pas** : ni une normalisation du fichier, ni la récupération d'un temps de capture perdu. Le fichier
  original n'est pas modifié.
- **Statut du temps de S1** : hypothèse propre à S1. Le nombre de paquets et l'absence de paquet vide ne prouvent pas
  que la capture était régulière à 30 images/s (E3 §4.3). Les écarts temporels mesurés entre machine et référence
  dépendent de cette hypothèse, des deux côtés de la même façon.
- **Remplace en partie** l'alternative écartée de D-004 (« numéro d'image ÷ cadence ») : elle reste fausse sur un
  flux à cadence variable, d'où la restriction et le contrôle des paquets vides.

### D-024 — Annotation de référence : faits observés, maintien en paramètre · Proposition
- **Demande du porteur** : la durée de maintien de 1 s reste une hypothèse ; distinguer franchissement, demi-tour et cas
  non observable ; ne pas générer la référence à partir du détecteur évalué.
- **Décision proposée** (protocole E1 v2) : l'annotateur saisit des franchissements (avec lien de retour), des
  demi-tours sans franchissement et des intervalles non observables, dans un outil qui n'affiche aucune sortie de
  l'analyse. La règle de maintien H est appliquée **à l'évaluation**, de façon identique à la référence et à la
  machine ; le rapport montre l'effet de H = 0, 500, 1 000 et 2 000 ms.

### D-025 — Détecteur derrière une interface ; refactorings vérifiés par non-régression · Confirmé pour le prototype (interface, 2026-11-11) / Proposition (règle générale)
- **Constat** : `docs/AUDIT_ARCHITECTURE.md` §4 (couplage C1) ; `run.py` importait et construisait `DetecteurYolox`
  directement. Plan validé par le porteur le 2026-11-11 : `docs/PLAN_DECOUPLAGE_DETECTEUR.md`.
- **Mis en œuvre** :
  - `passages/detecteur.py` : `Protocol` `Detector` (nom retenu par le porteur) avec une méthode
    `detecter(bgr) -> (boîtes xyxy float32 (N, 4), scores float32 (N,))`. Entrée : BGR uint8 en pleine résolution ;
    sortie bornée à l'image, une seule classe (personne), ordre déterministe. Fabrique
    `creer_detecteur(analyse, chemin_modele, threads)`.
  - `run.py` n'importe plus que la fabrique. `passages/detection.py`, le suivi, la ligne, les seuils,
    `configs/s1_g420.yaml` et le format des événements sont inchangés. YOLOX reste l'unique implémentation (D-022).
- **Vérifié** (`experiments/E2/RESULTATS_S1.md` §7) : la rejouée du code avant refactoring et la rejouée après
  refactoring sont **IDENTIQUES** au run S1 `20261103T172241Z-b3b507` au sens de `passages/non_regression.py` :
  3 000 images, 22 franchissements, pistes, passages, doublons et statistiques égaux. C'est une équivalence de
  comportement, **pas une mesure de justesse** : S1 reste une baseline technique non validée.
- **Proposé, non encore décidé** : exiger un verdict IDENTIQUE face à S1 (ou à une rejouée de référence documentée)
  pour tout refactoring du chemin d'analyse. Seuls l'identifiant de run, les dates, les durées et l'état git sont
  exclus de la comparaison.
- **Hors périmètre** : classes, clé de configuration du type de détecteur, description du détecteur dans le manifeste,
  second détecteur (RF-DETR). Chacun fera l'objet d'une entrée propre.
- **Dépendances** : aucune nouvelle (`typing.Protocol` fait partie de la bibliothèque standard).
- **Révision** : quand un second détecteur sera décidé, ou quand l'interface devra transporter des classes.
- **Complément du 2026-11-11** (étape 1 de `docs/CONCEPTION_MULTICLASSE.md`, exécutée sur demande du porteur, en
  attente de validation du commit) : `detecter` rend désormais un `Detections` (boîtes, scores, noms de classe,
  indices de classe du modèle). YOLOX passe par `AdaptateurYolox`, qui fixe la classe `person` ; `detection.py` ne
  change pas. Rejouées IDENTIQUES à S1 (`experiments/E2/RESULTATS_S1.md` §7). Le multi-classe n'est pas activé.
