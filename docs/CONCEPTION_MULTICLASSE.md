# Conception : prise en charge future de plusieurs classes d'objets

> Statut : **[Proposition]**, étude de conception seulement. Aucun code, aucune configuration, aucun run modifié ou
> créé. État étudié : commit `5a6ddbc` (après D-025). Date : 2026-11-11.
>
> Avancement : **étape 1 exécutée le 2026-11-11** (validée par le porteur), rejouées IDENTIQUES, commitée ensuite
> (`971e5b4`). Résultats : `experiments/E2/RESULTATS_S1.md` §7. Écart à la conception : `detection.py` n'est pas
> modifié ; la classe est ajoutée par un adaptateur (`AdaptateurYolox`, dans `detecteur.py`) qui enveloppe
> `DetecteurYolox`. L'immuabilité de `Detections` porte sur sa structure (champs non réaffectables), pas sur le contenu
> des tableaux NumPy, partagés sans copie avec le détecteur.
>
> **Étape 2 exécutée le 2026-11-11** (D-026, Proposition ; `docs/ETAPE2_DECODAGE_MULTICLASSE.md`), rejouées
> IDENTIQUES. Écarts à la conception : NMS **par classe** seulement, les familles sont reportées à l'étape du suivi
> (étape 4) ; `analyse.classes` est **refusée** à la validation tant que le suivi ne distingue pas les classes. La
> production reste en mode `person`. Les étapes 3 à 7 restent des propositions. Le tableau du §1 décrit l'état
> antérieur à l'étape 1 ; les lignes citées de `detection.py` ont changé à l'étape 2.

## 1. État actuel : comment « personne » est imposée

| Endroit | Ce qui fixe la classe |
|---|---|
| `detection.py` l. 13 et 50 | `CLASSE_PERSONNE = 0` ; score = objectness × probabilité de la classe 0, calculé pour **chaque** ancre, même si une autre classe y domine |
| `detection.py` l. 61 | NMS sur la seule classe personne |
| `detecteur.py` | Le contrat `Detector` rend `(boîtes, scores)`, sans classe |
| `run.py` l. 102-103 | `sv.Detections(..., class_id=np.zeros(...))` : la classe est forcée à 0 avant le suivi |
| `run.py` l. 116 | Ancrage bas-centre pour tout objet suivi |
| `pistes.jsonl`, `evenements.json` | Aucun champ de classe ; `piste` (entier) est la clé partout (`crossing`, `evaluate`, `paires`, `render`, `annotate`, `non_regression`) |
| `crossing.doublons_probables` | Même ligne, même sens, pistes différentes : pas de condition de classe |
| Protocole E1 v2 | La référence humaine n'a pas de classe |

Faits vérifiés le 2026-11-11 :
- **[Confirmé]** Le modèle `yolox_s.onnx` rend `[1, 8400, 85]` : 4 coordonnées, l'objectness et **80 scores de
  classe**. Les classes sont donc déjà calculées, puis ignorées. L'ordre des classes (COCO, personne = 0) est celui du
  dépôt YOLOX (`yolox/data/datasets/coco_classes.py`) : **[Hypothèse]** pour les autres indices, à vérifier dans le
  source avant usage. *Vérifié depuis (étape 2, D-026) : les 80 noms du tag `0.1.1rc0` sont repris tels quels dans
  `COCO_CLASSES` ; `car` = 2, `bus` = 5, `truck` = 7.*
- **[Confirmé]** `trackers` 2.6.1 `ByteTrackTracker` associe par IoU seule, **sans regarder la classe**. Il rend un
  sous-ensemble des détections d'entrée (`detections[idx]`), donc `class_id` est transporté, mais une même piste peut
  changer de classe d'une image à l'autre. Ses identifiants viennent d'un compteur propre à chaque instance.

## 2. Représentation proposée (sans couplage à YOLOX)

Un type d'échange interne, dans `detecteur.py`, à la place du couple `(boîtes, scores)` :

```python
@dataclass(frozen=True)
class Detections:
    boites: np.ndarray       # float32 (N, 4), xyxy en pixels de l'image        -> « bbox »
    scores: np.ndarray       # float32 (N,)                                     -> « confidence »
    classes: tuple[str, ...] # N noms de classe du domaine, ex. "person", "car" -> « class_name »
    ids_modele: np.ndarray   # int (N,), indice de classe propre au modèle      -> « class_id », traçabilité seulement
```

Règles :
- **Le domaine raisonne sur le nom de classe**, jamais sur l'indice : `class_id` dépend du modèle (l'indice 2 vaut
  « car » dans COCO, autre chose dans un modèle réglé pour un port). L'indice est gardé pour la traçabilité.
- **Le vocabulaire appartient à l'adaptateur** : chaque détecteur déclare la liste de ses classes (YOLOX : les 80
  noms COCO), et le manifeste l'enregistre avec son empreinte.
- **On garde les noms de champs existants** dans les fichiers (`boite`, `score`) ; on ajoute seulement `classe`.
- `sv.Detections` reste confiné à l'adaptateur de suivi : c'est le format d'entrée de `trackers`, pas un type du
  domaine (audit §5).

Point délicat, qui conditionne la compatibilité : passer au décodage habituel de YOLOX (une classe par ancre, l'argmax)
**changerait les détections de personnes**, car aujourd'hui une ancre où « personne » n'est pas la classe dominante
peut quand même produire une personne. Pour préserver S1, il faut un décodage **multi-étiquette** : un score par
classe demandée, puis une NMS par classe. Avec la seule classe personne, c'est exactement le calcul actuel.

## 3. Effets sur le suivi, les identifiants et les événements

| Sujet | Options | Proposition |
|---|---|---|
| Association entre classes | (a) un seul traqueur, toutes classes mêlées ; (b) un traqueur par classe ; (c) un traqueur par **famille de suivi** déclarée | **(c)**. Une famille regroupe les classes qu'un détecteur confond (ex. `vehicule: [car, truck, bus]`) et sépare celles qui ne doivent pas se mélanger (une personne et une voiture qui se croisent). Par défaut, chaque classe forme sa propre famille ; avec la seule classe personne, c'est le cas actuel |
| Doublons entre classes (même véhicule détecté « car » et « truck ») | Ignorer ; NMS entre classes d'une même famille | NMS **par famille**. Avec une famille d'une seule classe, c'est la NMS actuelle |
| Identifiants de piste | Clé composée `(famille, piste)` partout ; identifiant global calculé | Identifiant global entier `piste = id_local × n_familles + rang_famille`. Avec une seule famille, il vaut l'identifiant local : **identique à aujourd'hui**, et les consommateurs gardent leur clé entière |
| Classe d'une piste | Classe de la dernière détection ; vote majoritaire | Observation brute : la classe de chaque détection, dans `pistes.jsonl`. Couche dérivée : la classe de la piste par vote majoritaire, recalculable (règle « brut / dérivé ») |
| Franchissement | — | Ajouter `classe` (observée à l'image de franchissement) ; la clé `(ligne, piste)` de `DetecteurFranchissements` ne change pas |
| Règles par ligne | — | Filtre optionnel `classes` par ligne, et ancrage par ligne (bas-centre par défaut) |
| Règle de maintien | — | Inchangée : elle porte sur une chaîne `(ligne, piste)` |
| Doublons probables | — | Ajouter « même famille » à la condition ; sans effet avec une seule classe |
| Seuils | Globaux ; par classe | Globaux par défaut ; surcharge par famille seulement quand une mesure le justifiera. Les seuils de S1 restent calibrés pour les personnes |

## 4. Compatibilité stricte

1. **Configuration** : nouvelles clés **optionnelles** (`analyse.classes`, `analyse.familles_suivi`,
   `lignes[].classes`). Absentes, elles valent `classes: [person]` et une famille par classe. `configs/s1_g420.yaml` ne
   change pas, donc son empreinte canonique non plus, et le comparateur reste applicable.
2. **Étapes sans changement de sortie** (types internes, décodage multi-étiquette, familles) : verdict **IDENTIQUE**
   exigé face à S1, sans aucune adaptation du comparateur.
3. **Étape qui ajoute le champ `classe`** (format v2) : changement volontaire, et seulement additif. Le comparateur
   reçoit un mode « projection v1 » : tous les champs v1 doivent rester identiques, et les nouveaux champs doivent
   valoir `person` partout sur S1. `render`, `evaluate`, `paires` et `annotate` doivent lire les formats v1 et v2.
   Le run S1 v1 reste lisible tel quel.
4. Clé de configuration inconnue ou classe absente du vocabulaire du modèle : **refus** à la validation (couplage C6).

## 5. Ce qu'il faut abstraire, et ce qui doit rester simple

**Abstraire** (un seul endroit chacun) :
- le type `Detections`, avec des noms de classes ;
- le vocabulaire de classes, déclaré par l'adaptateur de détecteur ;
- les familles de suivi : une table de configuration, un traqueur par famille ;
- le filtre de classes de chaque règle.

**Garder simple** :
- une liste plate de noms, sans ontologie ni hiérarchie de classes ;
- pas de module ni de profil par secteur : un commerce, une route ou un port ne diffèrent que par leur fichier de
  configuration ;
- pas d'alias de classes ni de correspondance entre vocabulaires tant qu'un second modèle n'existe pas ;
- pas d'attributs (couleur, plaque : D-016, D-018) ;
- pas de seuils par classe sans mesure ;
- un seul algorithme de suivi.

## 6. Plan incrémental

| Étape | Contenu | Sorties | Tests | Acceptation |
|---|---|---|---|---|
| **1 (plus petite)** | Type `Detections` ; le `Detector` le rend ; l'adaptateur YOLOX remplit `classes = ("person",)×N` et `ids_modele = 0` ; `run.py` lit `boites` et `scores` comme avant, et ignore les classes | Inchangées | N0 : forme, types et longueurs cohérentes ; liste vide ; YOLOX rend les mêmes tableaux qu'avant sur une sortie de modèle **synthétique** | 47 tests et nouveaux ; rejouées de 20 s puis complète **IDENTIQUES** à S1 |
| 2 | Décodage multi-étiquette paramétré par une liste de classes, NMS par famille ; vocabulaire COCO déclaré (ordre vérifié dans le source YOLOX) | Inchangées (seule « person » est demandée) | N0 sur tenseurs synthétiques : une classe = calcul actuel au bit près ; deux classes, NMS par famille ; classe inconnue refusée | IDENTIQUE à S1 |
| 3 | Clés de configuration optionnelles, valeurs par défaut, refus des clés inconnues ; classes et vocabulaire dans le manifeste | Manifeste enrichi, pas d'autre changement | N0 de validation ; empreinte canonique de S1 inchangée | IDENTIQUE à S1 |
| 4 | Familles de suivi : un traqueur par famille, identifiant global entrelacé | Inchangées avec une seule famille | N0 : deux familles synthétiques, aucune association croisée, identifiants uniques et déterministes | IDENTIQUE à S1 |
| 5 | Format v2 : `classe` dans `pistes.jsonl`, les franchissements et les passages ; lecteurs v1 et v2 ; mode « projection v1 » du comparateur | Champ ajouté | N0 des lecteurs et du mode projection | Projection v1 IDENTIQUE à S1, et `classe` = `person` partout |
| 6 | Filtre de classes et ancrage par ligne ; doublons limités à une même famille ; statistiques et rendu par classe | Inchangées pour S1 | N0 | Projection v1 IDENTIQUE |
| 7 | Premier essai multi-classe sur une vidéo autorisée de réglage (hors R1 et R2), après une entrée dans `DECISIONS.md` et un protocole d'annotation avec classe (E1 v3) | Nouveau run | Comparaison à une référence humaine | Erreurs mesurées par classe, présentées comme **résultats de réglage** |

Les étapes 1 à 6 ne nécessitent ni nouveau modèle ni entraînement. Elles exigent les rejouées de non-régression,
c'est-à-dire de nouveaux runs, à autoriser au moment de l'exécution.

## 7. Compromis et risques

- **Multi-étiquette contre argmax** : le multi-étiquette préserve S1, mais produit des doublons entre classes
  (« car » et « truck » sur le même véhicule) ; la NMS par famille les réduit. L'argmax serait plus simple, mais il
  modifierait les personnes de S1.
- **Familles contre traqueur unique** : les familles évitent les fusions entre une personne et une voiture, au prix
  d'un traqueur par famille et d'un identifiant calculé. Un traqueur unique serait plus simple, mais laisserait des
  pistes changer de classe.
- **Identifiant entrelacé** : il évite de toucher les six modules qui utilisent `piste` comme entier ; en contrepartie,
  les identifiants ne sont plus consécutifs quand il y a plusieurs familles.
- **Format v2** : c'est le seul changement de sortie. Il est repoussé à l'étape 5, et vérifié en projection.
- **Justesse inconnue** : YOLOX-S n'a été évalué sur aucune classe dans nos scènes, pas même sur les personnes. Les
  véhicules lointains, la nuit et les classes portuaires absentes de COCO (conteneurs, engins) exigeront des mesures,
  peut-être un autre modèle, et un statut de licence des poids qui reste à établir (D-022).
- **Référence humaine** : l'évaluation par classe exige un protocole d'annotation avec classe, qui n'existe pas.
