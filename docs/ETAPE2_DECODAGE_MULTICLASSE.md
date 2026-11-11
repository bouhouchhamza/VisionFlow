# Étape 2 : décodage multi-classe de YOLOX, sans activation

> Statut : **[Proposition] exécutée le 2026-11-11** après approbation du porteur (commits `b194549`, `7936546`,
> `9708503`), avec les corrections ci-dessous. Décision : D-026 (Proposition). Résultats : `experiments/E2/RESULTATS_S1.md`
> §7. Le multi-classe n'est **pas** activé en production.
> État étudié : commit `971e5b4`. Sources YOLOX lues le 2026-11-11 sur GitHub (tag `0.1.1rc0` et branche `main`).
>
> Corrections apportées à cette proposition avant l'exécution :
> 1. le pseudo-code du §3.1 divisait les boîtes par le ratio **après** la NMS ; le code actuel le fait **avant**, et
>    l'IoU « +1 pixel » de la NMS dépend de l'échelle. Corrigé : division avant la NMS ;
> 2. le test du seuil exact (§6, test 3) utilisait 0,5, exact en binaire, qui ne distingue pas une comparaison en
>    float32 d'une comparaison en float64. Remplacé par `float32(0,1)` (exclu) et la valeur suivante (`nextafter`, gardée) ;
> 3. familles reportées : NMS par classe seule (stratégie A du §4) ; leur clé s'appellera `analyse.familles_suivi`,
>    comme dans `CONCEPTION_MULTICLASSE.md`, et non `analyse.familles` ;
> 4. `analyse.classes` est **refusée** à la validation de la configuration au lieu d'être ignorée sans erreur (§5) ;
> 5. vérification du nombre de colonnes de sortie du modèle ajoutée à la construction (§3.2, test 16) ;
> 6. `THIRD_PARTY_NOTICES.md`, créé après cette proposition, mentionne la liste des classes reprise de YOLOX.

## 1. Correspondance des 80 classes COCO (vérifiée)

Source : `yolox/data/datasets/coco_classes.py` au tag `0.1.1rc0`, tuple `COCO_CLASSES` de 80 noms. L'indice de
classe `k` correspond à la colonne `5 + k` de la sortie du modèle (`[1, 8400, 85]`, vérifié sur `models/yolox_s.onnx`).

| Indice | Classe | Indice | Classe | Indice | Classe | Indice | Classe |
|---|---|---|---|---|---|---|---|
| 0 | person | 20 | elephant | 40 | wine glass | 60 | dining table |
| 1 | bicycle | 21 | bear | 41 | cup | 61 | toilet |
| 2 | car | 22 | zebra | 42 | fork | 62 | tv |
| 3 | motorcycle | 23 | giraffe | 43 | knife | 63 | laptop |
| 4 | airplane | 24 | backpack | 44 | spoon | 64 | mouse |
| 5 | bus | 25 | umbrella | 45 | bowl | 65 | remote |
| 6 | train | 26 | handbag | 46 | banana | 66 | keyboard |
| 7 | truck | 27 | tie | 47 | apple | 67 | cell phone |
| 8 | boat | 28 | suitcase | 48 | sandwich | 68 | microwave |
| 9 | traffic light | 29 | frisbee | 49 | orange | 69 | oven |
| 10 | fire hydrant | 30 | skis | 50 | broccoli | 70 | toaster |
| 11 | stop sign | 31 | snowboard | 51 | carrot | 71 | sink |
| 12 | parking meter | 32 | sports ball | 52 | hot dog | 72 | refrigerator |
| 13 | bench | 33 | kite | 53 | pizza | 73 | book |
| 14 | bird | 34 | baseball bat | 54 | donut | 74 | clock |
| 15 | cat | 35 | baseball glove | 55 | cake | 75 | vase |
| 16 | dog | 36 | skateboard | 56 | chair | 76 | scissors |
| 17 | horse | 37 | surfboard | 57 | couch | 77 | teddy bear |
| 18 | sheep | 38 | tennis racket | 58 | potted plant | 78 | hair drier |
| 19 | cow | 39 | bottle | 59 | bed | 79 | toothbrush |

Ce sont les 80 classes « contiguës » de YOLOX, pas les identifiants COCO d'origine, qui vont de 1 à 90 avec des trous.
La démo ONNX de YOLOX (`demo/ONNXRuntime/onnx_inference.py`) indexe `COCO_CLASSES` par l'indice de colonne : c'est la
convention que reprendra l'adaptateur.

**Point d'attention (sans changement proposé)** : au tag `0.1.1rc0`, la démo ONNX normalise encore l'entrée
(moyenne et écart-type). La démo de la branche `main` ne le fait plus, et la page de la démo ONNX sur `main` renvoie
vers le fichier `0.1.1rc0/yolox_s.onnx` que nous utilisons. Notre prétraitement (BGR 0-255, sans normalisation) suit
donc la documentation actuelle. Aucune mesure indépendante ne le confirme ; la première image de S1 produit des
détections, ce qui est cohérent sans valoir preuve.

## 2. Calcul actuel (commit `971e5b4`)

`passages/detection.py` :

1. **Prétraitement** (`pretraiter`, l. 38-44) : redimensionnement de rapport `r = min(640/H, 640/W)`, interpolation
   bilinéaire, remplissage à 114, transposition CHW, float32.
2. **Décodage** (`decoder`, l. 46-62), sur les 8 400 ancres :
   - `pred = sortie.copy()` ; centres `(xy + grille) × pas` ; tailles `exp(wh) × pas` (float32) ;
   - **score personne** = `pred[:, 4] * pred[:, 5 + 0]` (objectness × probabilité de la classe 0), produit float32,
     calculé pour **chaque** ancre, que « personne » y soit la classe dominante ou non (multi-étiquette) ;
   - **filtrage strict** : `scores > seuil` (0,1 pour S1), comme `multiclass_nms` de la démo YOLOX ;
   - boîtes xyxy calculées sur les seules ancres retenues, dans l'ordre des ancres, puis divisées par `r` ;
   - **NMS** (`nms`, l. 74-89, reprise de `demo_utils.nms`) : tri `scores.argsort()[::-1]` (tri par défaut, non
     stable), IoU avec la convention « +1 pixel », suppression si IoU > 0,45 ; ordre de sortie = ordre de conservation,
     donc scores décroissants.
3. **Bornage** (`detecter`, l. 64-71) : après la NMS, les boîtes sont bornées à `[0, W-1] × [0, H-1]`. La NMS porte
   donc sur des boîtes non bornées, comme dans YOLOX.

Ce calcul est exactement le cas « une classe » de `multiclass_nms` de la démo YOLOX. Ce n'est **pas** le
`postprocess` d'évaluation (`yolox/utils/boxes.py`), qui garde une seule classe par ancre (l'argmax), filtre avec
`>=` et applique une NMS par classe (`batched_nms`).

## 3. Décodage proposé

### 3.1 Principe

Généraliser le décodage actuel **sans branche spéciale** pour la classe personne : le mode `person` passe par le même
code que le multi-classe.

Version corrigée et exécutée (NMS par classe, division par le ratio **avant** la NMS) :

```text
entrées : sortie (8400, 85), ratio (float Python), classes demandées C (indices), seuil (float Python), seuil_nms
1. pred = sortie.copy() ; centres et tailles, comme aujourd'hui
2. pour chaque k de C, par indice croissant :
     scores = pred[:, 4] * pred[:, 5 + k]          # même produit float32 qu'aujourd'hui
     candidats = ancres où scores > seuil          # ordre des ancres conservé ; comparaison en float32
     boîtes xyxy des candidats, puis boîtes /= ratio   # AVANT la NMS, comme aujourd'hui
     garde = nms(boîtes, scores des candidats, seuil_nms)   # fonction nms actuelle, inchangée
     sortie de la classe = candidats[garde], avec l'indice k en int64
3. résultat = concaténation des classes ; vide : formes (0, 4), (0,), (0,)
```

La première version de ce pseudo-code regroupait les classes par familles et divisait par le ratio après la NMS ;
elle est remplacée (voir l'en-tête).

**Pourquoi le mode `person` est exactement reproduit** : avec `C = (0,)`, les candidats sont les mêmes ancres, dans
le même ordre, avec les mêmes valeurs (même produit float32, mêmes opérations élément par élément sur les boîtes,
même division avant la NMS), et la même fonction `nms` reçoit les mêmes tableaux. La sortie est donc identique au bit
près, ordre compris. Les tests du §6 et les rejouées l'ont vérifié (`experiments/E2/RESULTATS_S1.md` §7).

Contrainte d'implémentation : ne changer ni `nms`, ni le type de tri, ni l'ordre « filtrer, calculer les boîtes,
diviser par le ratio », ni l'ordre « NMS puis bornage ».

### 3.2 Interface

Interface exécutée :

- `passages/detection.py` :
  - `COCO_CLASSES` (80 noms, repris de YOLOX, Apache-2.0, mention dans `THIRD_PARTY_NOTICES.md`) ;
  - `indices_classes(noms)` : noms vers indices triés ; liste vide, nom inconnu, élément non textuel ou doublon
    refusés (`ValueError`) ;
  - `DetecteurYolox(..., classes=(0,))` : indices entiers Python distincts dans [0, 79] ; `decoder` et `detecter`
    rendent `(boîtes, scores, ids)`, avec `ids` en int64 ;
  - vérification à la construction, sans inférence : la dernière dimension déclarée de la sortie
    (`session.get_outputs()[0].shape[-1]`) doit être l'entier 85. Une dimension symbolique ou inconnue est refusée,
    car rien ne garantirait alors que les colonnes 5 à 84 sont les 80 classes de `COCO_CLASSES` ; un modèle exporté
    avec une sortie dynamique demandera une décision explicite.
- `passages/detecteur.py` : `AdaptateurYolox` traduit `ids` en noms (`COCO_CLASSES[id]`) et construit `Detections`.
  `creer_detecteur` ne transmet aucune classe : **la production reste en mode `person`**.
- `passages/config.py` : `analyse.classes` refusée (§5).
- `run.py`, la configuration S1, ByteTrack, les identifiants de piste, les événements et le format des runs : inchangés.

## 4. Doublons entre classes et stratégies de NMS

YOLOX prédit **une seule boîte par ancre**. Une ancre qui dépasse le seuil pour deux classes produit donc deux
candidats de **boîtes strictement identiques** (IoU = 1), par exemple « car » à 0,62 et « truck » à 0,35.

| Stratégie | Doublon « car / truck » sur une même ancre | Objets différents qui se recouvrent (personne sur une moto, personne devant une voiture) | Mode `person` identique ? |
|---|---|---|---|
| A. NMS par classe (démo YOLOX) | **Gardé** : deux détections pour un véhicule | Gardés | Oui |
| B. NMS indépendante de la classe, sur toutes les classes | Supprimé | **Supprime à tort** l'un des deux si l'IoU > 0,45 | Oui avec la seule personne |
| C. Une classe par ancre (argmax, `postprocess` de YOLOX) | Supprimé à l'ancre ; reste possible entre ancres voisines | Gardés si les classes diffèrent | **Non** : une ancre où « personne » n'est pas dominante perdrait sa personne |
| D. **NMS par famille** (A dans une famille d'une seule classe, B dans une famille de plusieurs classes) | Supprimé si « car » et « truck » sont dans la même famille | Gardés si les classes sont dans des familles différentes | Oui |

**Proposition initiale : D**, avec par défaut une famille par classe. **Retenu à l'étape 2 : A** (NMS par classe),
sur décision du porteur ; les familles (D) sont reportées à l'étape du suivi par famille, avec laquelle elles
seront décidées.

Effets résiduels de A :
- une ancre au-dessus du seuil pour « car » et « truck » donne **deux détections de même boîte** ; de même pour une
  « personne » et un « chien » sur la même ancre. Ce doublon est connu et testé, pas corrigé à cette étape ;
- **égalité de scores** dans une classe : le tri non stable de `nms` rend un choix **déterministe mais non spécifié**.
  On ne change pas le tri, pour ne pas toucher au mode `person`. Les tests vérifient l'égalité à l'oracle et la
  stabilité du résultat sur dix appels ;
- le seuil 0,1 a été fixé pour les personnes de S1 : appliqué tel quel aux autres classes, il donnera probablement
  beaucoup de détections faibles. **[Hypothèse]**, à mesurer plus tard, sans réglage maintenant.

## 5. Configuration (pour l'étape 3 ; refusée à l'étape 2)

```yaml
analyse:
  classes: [person]                        # optionnel ; défaut : [person] ; noms du vocabulaire du modèle
  familles_suivi: [[car, truck, bus]]      # optionnel ; une classe non citée forme sa propre famille
```

**État après l'étape 2** : `config.valider` refuse `analyse.classes` avec un message explicite (`ConfigInvalide`),
même réduite à `[person]`, avant toute création de dossier de run et sans modifier la configuration. Aucune clé
n'est lue. Le paragraphe « Pourquoi ne rien lire à l'étape 2 » ci-dessous est conservé comme justification, mais sa
dernière phrase (clé « ignorée sans erreur ») est remplacée par ce refus.

- **Rétrocompatibilité** : les deux clés sont absentes de `configs/s1_g420.yaml`, dont l'empreinte canonique ne change
  donc pas. L'absence vaut le comportement actuel.
- **Validation** (étape 3) : noms connus du vocabulaire du détecteur, pas de doublon, chaque classe dans une seule
  famille, familles incluses dans `classes`, clés inconnues refusées.
- **Seuils** : `seuil_detection` et `seuil_nms` restent globaux. Aucun seuil par classe sans mesure.
- **Pourquoi ne rien lire à l'étape 2** : tant que le suivi mélange les classes (étape 4), activer plusieurs classes
  en production ferait associer une personne et une voiture dans une même piste. À l'étape 2, une clé `classes` serait
  ignorée sans erreur, comme aujourd'hui toute clé inconnue ; le refus arrive à l'étape 3.

## 6. Tests synthétiques à écrire

Les sorties de modèle sont fabriquées (tableaux `(8400, 85)` ou plus petits, avec la grille réelle), marquées comme
synthétiques. **Oracle** : une copie figée du décodage actuel (`decoder` et `nms` du commit `971e5b4`), placée dans le
fichier de test, sert de référence d'équivalence.

**Équivalence du mode `person`** :
1. Sorties aléatoires de graine fixe (20 graines, scores répartis autour du seuil) : boîtes, scores et ordre égaux au
   bit près à l'oracle ; `ids` tous nuls, en int64.
2. Ancre où « personne » n'est **pas** dominante (car 0,9, personne 0,3) : la personne est gardée en mode `person`.
   Cela prouve le caractère multi-étiquette.
3. Score exactement égal au seuil : objectness 1,0 et classe `float32(0,1)`, avec le seuil 0,1 de S1 : exclue (`>`
   strict, comparaison en float32) ; la valeur float32 suivante (`nextafter`) est gardée. *(Corrigé : la version
   initiale utilisait 0,5, qui ne distingue pas une comparaison en float32 d'une comparaison en float64.)*
4. Aucune ancre au-dessus du seuil : tableaux vides de formes (0, 4), (0,) et (0,), types float32, float32 et int64.
5. Classe très bien notée mais non demandée (car 0,99) : absente de la sortie.
6. Boîtes qui débordent de l'image : bornage après la NMS, comme l'oracle.
7. Sorties réelles : le modèle est exécuté sur quelques images de S1 (réglage), et le résultat du nouveau décodage
   est comparé à l'oracle. Test ignoré proprement si la vidéo ou le modèle sont absents.

**Plusieurs scores élevés sur une même boîte** :
8. Ancre personne 0,9 et car 0,8, classes `(person, car)` : deux détections de boîtes identiques, « person » en premier
   (ordre des indices).
9. Ancre car 0,6 et truck 0,7, classes `(car, truck)` : deux détections (doublon connu, familles reportées).
10. et 11. *(familles : reportés avec elles.)* Remplacés par : une personne et une voiture qui se chevauchent
    (IoU d'environ 0,8) survivent toutes deux ; deux personnes à la même place, une seule.
12. Égalité exacte de scores dans une classe : égalité à l'oracle et même résultat sur dix appels.
13. L'ordre des classes demandées ne change pas la sortie ; sortie par classe croissante, puis score décroissant.
    Ajouté : en multi-classe, le bloc des personnes est en tête et égal au bit près au mode `person` seul.

**Validation** :
14. Classe inconnue, classe en double, liste vide, chaîne seule, élément non textuel ; indice hors de [0, 79], booléen,
    entier NumPy ou flottant : `ValueError`. *(Les cas « familles » sont reportés.)*
15. Vocabulaire : 80 noms uniques ; `person` = 0, `bicycle` = 1, `car` = 2, `motorcycle` = 3, `bus` = 5,
    `truck` = 7, `boat` = 8 ; empreinte SHA-256 de la liste jointe, figée dans le test.
16. Sortie déclarée à 84 ou 86 colonnes, ou dimension symbolique ou inconnue : refusée à la construction (session
    simulée) ; 85 acceptée sans aucun appel d'inférence ; le vrai modèle déclare `[1, 8400, 85]` (ignoré sans modèle).
17. Adaptateur : `ids_modele` et `classes` cohérents (`COCO_CLASSES[id]`) ; `creer_detecteur` produit le mode `person`.
18. Configuration : `analyse.classes` refusée (`[person, car]` comme `[person]`), sans mutation ; la configuration S1
    reste acceptée avec son empreinte canonique `1887f2c2…`.

Correspondance avec les tests écrits (`tests/test_detection_multiclasse.py`, numéros T1 à T21) : voir
`experiments/E2/RESULTATS_S1.md` §7.

## 7. Plan d'implémentation minimal

| Ordre | Action | Fichiers |
|---|---|---|
| 1 | Écrire l'oracle figé et le banc des tests 1 à 7 **avant** de toucher au décodeur ; vérifier d'abord que l'oracle reproduit le `decoder` actuel au bit près | `tests/test_detection_multiclasse.py` (créé) |
| 2 | Généraliser `decoder` et `detecter` (§3) ; ajouter `COCO_CLASSES` et les vérifications | `passages/detection.py` |
| 3 | Adapter `AdaptateurYolox` à `(boîtes, scores, ids)` ; adapter le faux YOLOX des tests | `passages/detecteur.py`, `tests/test_detecteur.py` |
| 4 | Tests 8 à 17 ; suite complète | `tests/test_detection_multiclasse.py` |
| 5 | Rejouées de 20 s puis complète dans `runs/non_regression/multiclasse_etape2/` (à autoriser) ; comparaison à S1, à l'essai et aux rejouées de l'étape 1 | — |
| 6 | Documentation : `RESULTATS_S1.md` §7, avancement de `CONCEPTION_MULTICLASSE.md`, note à D-022 (vocabulaire et convention des indices) | docs |

Fichiers **non modifiés** : `passages/run.py`, `configs/s1_g420.yaml`, `crossing.py`, `video.py`,
`non_regression.py`, `requirements*`, le modèle, les runs existants. Aucune nouvelle dépendance.

**Exécution (2026-11-11)** : ordre suivi, avec deux écarts au tableau, décidés par le porteur : `passages/config.py`
est modifié (refus de `analyse.classes`, commit `9708503`) et `THIRD_PARTY_NOTICES.md` est mis à jour (commit
`7936546`). Commits : `b194549` (oracle et T1, vérifiés sur le code non modifié), `7936546` (décodage, adaptateur,
tests), `9708503` (configuration). Rejouées sur le commit `9708503`, arbre propre.

## 8. Critères d'acceptation

1. Tous les tests passent (68 existants et nouveaux), aucun ignoré sur ce poste.
2. Tests d'équivalence 1 à 7 : égalité au bit près, ordre compris, face à l'oracle figé.
3. `git diff --stat` : seuls `detection.py`, `detecteur.py`, les tests et la documentation sont modifiés ;
   `run.py` et la configuration sont inchangés (empreintes git `dc786b85…` et `cb4ab36a…`).
4. Le décodage n'a pas de branche spéciale pour la classe personne (relecture du diff).
5. Aucun chemin de production ne permet d'activer une autre classe : `creer_detecteur` n'en transmet aucune, et la CLI
   n'expose rien de nouveau.
6. Rejouée de 20 s : **IDENTIQUE** à l'essai, à S1 tronqué et à `20261111T132821Z-a4962c`.
7. Rejouée complète : **IDENTIQUE** à S1 et à `20261111T133101Z-4c907c`.
8. Empreintes de S1 et de l'essai inchangées ; R1 et R2 non touchées.
9. En cas d'écart à un point quelconque : arrêt, et présentation de l'écart sans correction ni masquage.

**Résultat (2026-11-11)** : critères 1 à 8 atteints, aucun écart. Le critère 3 inclut désormais `config.py` et
`THIRD_PARTY_NOTICES.md` (voir §7). Le critère 4 est tenu : aucune branche spéciale pour `person`, `nms` inchangée.
Détail et identifiants des rejouées : `experiments/E2/RESULTATS_S1.md` §7.

## 9. Risques

| Risque | Parade |
|---|---|
| Écart au bit près introduit par une réorganisation des calculs (boîtes calculées sur un autre sous-ensemble, autre ordre d'opérations) | Oracle figé, 20 graines, images réelles, rejouées ; contrainte d'implémentation du §3.1 |
| Tri non stable : bascule d'ordre en cas d'égalité | `nms` et le tri restent inchangés ; égalités multi-classes couvertes par un test de déterminisme |
| Activation prématurée du multi-classe avec un suivi qui mélange les classes | `analyse.classes` refusée à la validation ; `creer_detecteur` ne transmet aucune classe ; aucun multi-classe en production avant le suivi par classe |
| Doublons entre classes (même ancre « car » et « truck ») | Connus et testés ; familles reportées à l'étape du suivi |
| Modèle dont les colonnes ne correspondent pas au vocabulaire | Sortie déclarée de 85 colonnes exigée à la construction ; dimension symbolique ou inconnue refusée |
| Seuils de S1 inadaptés aux autres classes | Hypothèse notée ; aucune mesure ni réglage à cette étape |
| Convention d'indices erronée | Indices vérifiés dans le source du tag ; empreinte de la liste figée dans un test |
| Doute sur le prétraitement (normalisation au tag `0.1.1rc0`) | Hors périmètre ; signalé au §1 pour une décision ultérieure |
