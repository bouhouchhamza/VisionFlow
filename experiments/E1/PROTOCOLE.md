# E1 — Protocole d'annotation de référence (scénario A : passages)

Version du protocole : **2** (2026-11-03), remplace la v1. Toute modification incrémente la version ; une annotation
indique toujours la version utilisée. Statut : **prêt pour S1**, pas encore appliqué.

Objectif : produire une vérité terrain **humaine et indépendante** de l'analyse automatique, pour mesurer les erreurs
du prototype (`docs/DATA_AND_RULES.md` §8). Aucun objectif de précision n'est fixé ici.

Changements par rapport à la v1 :
- on annote des **faits observés** (franchissements, demi-tours, intervalles non observables) et non plus des
  « passages » déjà filtrés par la règle des 1 s ;
- la durée de maintien devient un **paramètre d'évaluation**, appliqué de la même façon à la référence et à la machine.

## 1. Indépendance de la référence

- L'outil d'annotation n'affiche **aucune** détection, piste ni compteur de l'analyse : vidéo, ligne et saisies
  de l'annotateur seulement (`"detecteur_affiche": false` dans le fichier).
- Ne pas regarder la vidéo annotée d'un run (`runs/<id>/rendus/`) ni ses événements **avant** d'avoir terminé la passe.
  Si cela arrive, le noter dans `remarque` et le signaler : la passe n'est plus une référence indépendante.
- La référence n'est jamais générée, pré-remplie ni corrigée à partir des sorties du détecteur évalué.

## 2. Ligne de S1

Ligne `portes`, de `p1 = (0,44 ; 0,64)` à `p2 = (0,74 ; 0,81)` en coordonnées normalisées : elle suit le **bas des deux
doubles portes**, au niveau du sol. Côté G (en haut de l'image) : extérieur, on y arrive par une **sortie**. Côté D
(hall, paillassons) : intérieur, on y arrive par une **entrée**.

Vue de contrôle : `experiments/E1/out/s1_vue_ligne_t15.png` (non versionnée, régénérable) :

```powershell
.\.venv\Scripts\python -m passages vue-ligne --config configs/s1_g420.yaml --t 15 --sortie experiments/E1/out/s1_vue_ligne_t15.png
```

La ligne est fixée **avant** toute annotation et toute analyse complète ; elle ne doit plus bouger pendant E1. La modifier
crée une nouvelle configuration et rend les annotations existantes non comparables.

## 3. Ce que l'on annote

**Point de contact au sol** : milieu entre les deux pieds. Pieds cachés : point estimé sous le centre du corps, et
marquer `incertain`.

**Instant** : la **première image** où le point de contact est du nouveau côté (avancer image par image autour du
franchissement). Le temps est celui affiché par l'outil, calculé comme l'analyse (`experiments/E3/PROTOCOLE.md` §4.3),
jamais lu sur une horloge incrustée.

| Type | Touche | Quand l'utiliser |
|---|---|---|
| **Franchissement** `entree` / `sortie` | `e` / `x` | Le point de contact passe d'un côté à l'autre **à travers le segment** de la ligne. Une touche **par personne** : trois personnes ensemble = trois saisies. |
| **Retour** (lien) | `r` juste après la saisie | La personne qui vient de franchir avait déjà franchi la ligne dans l'autre sens : `r` lie la saisie au franchissement antérieur de sens opposé le plus récent ; `r` à nouveau passe au candidat plus ancien, puis retire le lien. Vérifier l'identifiant affiché. |
| **Demi-tour sans franchissement** | `t` | Une personne s'approche jusqu'à la ligne (pied sur ou tout contre la ligne), puis repart **du même côté sans l'avoir traversée**. Instant : l'image du demi-tour. N'entre pas dans les comptes ; sert à expliquer des erreurs de la machine. |
| **Non observable** | `n` au début, `n` à la fin | On ne peut pas dire si quelqu'un a franchi : porte masquée, foule compacte, image dégradée, personne cachée par une autre. Les deux côtés (référence et machine) sont exclus de l'évaluation sur cet intervalle. |

Marques complémentaires sur la dernière saisie : `i` incertain (instant ou décompte douteux), `c` horloge incrustée
illisible (sans objet pour S1).

### Cas ambigus

| Cas | Ce que l'on saisit |
|---|---|
| Franchit puis revient (même rapidement) | Deux franchissements, le second lié par `r`. La règle de maintien décidera à l'évaluation. |
| Hésite sur la ligne sans traverser | `t` (demi-tour). |
| Immobile sur la ligne | Rien tant que le point de contact n'a pas changé de côté ; le franchissement est saisi à l'image où il passe. |
| Groupe compact | Un franchissement par personne distinguable ; si le nombre est douteux, meilleure estimation + `i`, ou `n` si l'on ne peut rien dire. |
| Enfant porté | Ne compte pas. Enfant qui marche : compte. |
| Poussette, chariot, fauteuil | Seule la personne compte. |
| Passage en dehors du segment (contourne l'extrémité de la ligne) | Rien. |
| Personne coupée par le bord de l'image | Franchissement si déductible des images avant et après, sinon `n`. |
| Occultation pendant le franchissement | Franchissement si vue d'un côté puis de l'autre sans autre chemin possible, instant estimé + `i` ; sinon `n`. |
| Reflet (vitres des portes), affiche | Rien. |
| Déjà de l'autre côté au début de la vidéo | Rien. |
| Personnel ou visiteur | Pas de distinction (D-016). |

## 4. Règle de maintien : une hypothèse

« Un passage est un franchissement suivi d'au moins **H** de temps vidéo du nouveau côté » reste une **hypothèse**
(H = 1 000 ms au départ, `configs/s1_g420.yaml`). Ce n'est pas une vérité terrain. À l'évaluation (`passages comparer`) :
- deux franchissements consécutifs d'une même chaîne de retours, séparés de moins de H, s'annulent ;
- la même règle s'applique à la machine (même piste) ;
- le rapport donne les résultats pour H = 0, 500, 1 000 et 2 000 ms, afin de voir l'effet de l'hypothèse.

## 5. Plages couvertes

L'outil enregistre comme couvertes les images **vues à la suite** (lecture ou image par image). Un saut (`l`, `PgDn`)
laisse un trou non couvert, qui n'est pas « sans passage » mais « non annoté ». Pour une passe complète : lire toute
la vidéo sans sauter en avant (les retours en arrière sont libres).

## 6. Mode d'emploi de l'outil

Prérequis : `.venv` installé (`requirements.txt`), vidéo S1 présente avec la bonne empreinte.

```powershell
.\.venv\Scripts\python -m passages annoter --config configs/s1_g420.yaml --annotateur <nom> --passe 1 --echantillon S1
# reprendre une passe interrompue
.\.venv\Scripts\python -m passages annoter --config configs/s1_g420.yaml --annotateur <nom> --passe 1 --echantillon S1 --reprendre
```

À la première ouverture, l'outil relève le temps des 9 000 images (environ 30 s, mis en cache dans `data/cache/`).

| Touche | Action |
|---|---|
| `espace` | lecture / pause (la lecture s'arrête à chaque saisie) |
| `←` `→` ou `a` `d` | image précédente / suivante |
| `j` / `l` | −1 s / +1 s |
| `PgUp` / `PgDn` | −10 s / +10 s |
| `+` / `-` | vitesse de lecture ×0,25 à ×2 |
| `e` `x` `r` `t` `n` | saisies (§3) |
| `i` / `c` | incertain / horloge illisible sur la dernière saisie |
| `u` | annuler la dernière saisie de la session |
| `s` | sauvegarder (sauvegarde automatique chaque minute) |
| `q` / `Échap` | sauvegarder et quitter |
| `h` | afficher / masquer l'aide |

Méthode conseillée : lecture à ×1 ; à l'approche d'un franchissement, pause, revenir avec `←` jusqu'à la dernière
image de l'ancien côté, avancer d'une image, saisir. Noter à part le temps passé (début, fin, pauses).

Fichier produit : `data/annotations/<16 premiers caractères du sha256>/<nom>_passe<k>.json` (hors git).

## 7. Format (version_format 2)

Champs principaux, écrits par l'outil :

```json
{
  "format": "annotation_passages", "version_format": 2, "version_protocole": 2,
  "nature": "verite_terrain_humaine", "detecteur_affiche": false,
  "video": {"id_echantillon": "S1", "sha256": "…", "nom_fichier": "…", "images": 9000, "duree_ms": 299967,
            "mode_temps": "rang_cadence_nominale"},
  "annotateur": "…", "passe": 1, "outil": "passages.annotate 0.1.0",
  "lignes": [{"id": "portes", "p1": [0.44, 0.64], "p2": [0.74, 0.81], "sens": {"gauche_vers_droite": "entree", "droite_vers_gauche": "sortie"}}],
  "plages_couvertes": [{"debut_image": 0, "fin_image": 8999, "debut_ms": 0, "fin_ms": 299967}],
  "franchissements": [{"id": "f0001", "ligne": "portes", "direction": "entree", "t_ms": 15233, "num_image": 457,
                       "retour_de": null, "incertain": false, "horloge_incrustee_illisible": false, "remarque": ""}],
  "demi_tours": [{"id": "d0002", "ligne": "portes", "t_ms": 40100, "num_image": 1203, "incertain": false, "remarque": ""}],
  "non_observables": [{"id": "n0003", "debut_image": 2000, "fin_image": 2100, "debut_ms": 66667, "fin_ms": 70000, "remarque": ""}]
}
```

Les valeurs ci-dessus sont un exemple de forme, pas des observations. Le champ `remarque` peut être complété à la main
dans le fichier après la passe.

## 8. Déroulement de l'expérience E1

1. Ligne de S1 fixée (§2) — fait le 2026-11-03.
2. Passe 1 sur S1 entière ; noter le temps passé.
3. Comparer au run : `python -m passages comparer --run runs/<id> --reference data/annotations/…/<nom>_passe1.json`.
4. Au moins un jour plus tard, passe 2 sur S1 **sans regarder la passe 1 ni le rendu du run**, puis comparer les deux
   passes (même appariement, tolérance 1 000 ms au départ) pour estimer le désaccord humain. La comparaison passe
   contre passe n'est pas encore écrite : `passages comparer` ne compare qu'un run à une annotation.
5. S2 ensuite ; R1 et R2 seulement quand la configuration est gelée (`experiments/E0/INVENTAIRE.md`). L'outil refuse
   d'annoter une configuration marquée `role_echantillon: reserve`.

## 9. Mesures attendues (sans objectif fixé à l'avance)

- Minutes d'annotation par minute de vidéo.
- Accord entre passes : appariés, non appariés de chaque côté, écart temporel, désaccords de sens.
- Cas ambigus non couverts par le §3 → version 3 du protocole.
