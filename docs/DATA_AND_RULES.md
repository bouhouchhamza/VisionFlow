# Données et règles

> Statuts : **[Confirmé]** · **[Proposition]** · **[Hypothèse]** · **[Ouvert]** (voir `VISION.md`).
> Sauf mention contraire, tout ce document est **[Proposition]** : c'est le modèle cible de la V1, à valider
> lors des tâches T1.2 à T1.4 de `IMPLEMENTATION_PLAN.md`.

Dernière mise à jour : 2026-11-03.

## 1. Trois couches qui ne se mélangent pas

| Couche | Produite par | Modifiable ? | Exemples |
|---|---|---|---|
| **Observé (brut)** | Machine, au sein d'un run | Jamais | Franchissement à 00:03:12.480, sens entrée, confiance 0,71 |
| **Revu (corrections)** | Humain | Ajout seulement ; la dernière décision s'applique, l'historique reste | « Rejeté : reflet dans la vitrine » ; « Ajouté : passage manqué à 00:05:01.000 » |
| **Calculé (indicateurs)** | Fonction déterministe des deux couches précédentes | Recalculé, jamais saisi | 42 entrées entre 10:00 et 10:15 (après revue) |

Une quatrième catégorie est **séparée des trois autres** : les **annotations de référence** (vérité terrain),
saisies selon un protocole pour mesurer les erreurs. Elles appartiennent à une vidéo, pas à un run, et ne
corrigent jamais un run. Revoir un run et annoter une vidéo sont deux activités distinctes.

**[Ouvert]** Promouvoir une revue exhaustive en annotation de référence (D-015). Proposition : interdit en V1,
car la revue est influencée par ce que la machine propose (biais d'ancrage) et sous-estimerait les passages manqués.

## 2. Entités

Champs principaux ; les types exacts seront fixés par le schéma SQLite (T1.2).

**VideoAsset** — `asset_id`, `sha256`, `chemin`, `origine` (`reelle_autorisee` | `publique` | `mise_en_scene`),
`reference_autorisation` (obligatoire : document d'autorisation, ou pour une source publique `url_source`, `licence`,
`attribution`, `date_consultation`, `usages_permis` parmi essais internes / démonstration / redistribution),
`role_echantillon` (`reglage` | `reserve` | nul), `sha256_normalise` et `methode_normalisation` (nuls si aucune
normalisation, D-019), `duree_ms`, `cadence_nominale`, `cadence_variable` (bool), `largeur`,
`hauteur`, `codec`, `debut_declare` (nullable), `source_debut` (`metadonnee` | `nom_fichier` | `manuel` | `capture`),
`source_type` (`fichier` | `camera`), `camera_id` (nullable), `point_de_vue_id`.

**PointDeVue** — `point_de_vue_id`, `site`, `libelle`, géométries (lignes, zones) en coordonnées normalisées [0, 1].

**AnalysisConfig** — contenu YAML, `version_schema`, `empreinte` (SHA-256 du contenu canonique), `scenario`.

**Run** — `run_id`, `asset_id`, `config_empreinte`, `version_code` (commit git), `modele_id`, `modele_empreinte`,
`parametres`, `etat` (`en_attente` | `en_cours` | `reussi` | `echoue` | `annule`), `parent_run_id`,
`debut_traitement`, `fin_traitement` (horloge système), `message_erreur`.

**Observation** — `obs_id`, `run_id` (non nul), `type` (`franchissement_ligne`), `t_ms` (temps vidéo),
`num_image`, `sens` (`entree` | `sortie`), `confiance`, `piste_id` (local au run), `ligne_id`,
`boite` (au moment du franchissement).

**Preuve** — `preuve_id`, `run_id`, `obs_id`, `nature` (`vignette` | `extrait`), `t_debut_ms`, `t_fin_ms`,
`chemin`, `sha256`.

**Correction** — `correction_id`, `run_id` (non nul), `obs_id` (nul pour un ajout), `action`
(`confirmer` | `rejeter` | `modifier_instant` | `modifier_sens` | `ajouter` | `commenter`), `nouvelles_valeurs`,
`motif`, `auteur`, `cree_le` (horloge système).

**PlageRevue** — `run_id`, `t_debut_ms`, `t_fin_ms`, `auteur` : intervalle que le réviseur déclare avoir entièrement
parcouru (permet de distinguer « aucun passage manqué ajouté » de « pas regardé »).

**AnnotationReference** — `annotation_id`, `asset_id`, `protocole_version`, `annotateur`, `plages_couvertes`,
événements (`t_ms`, `sens`, `ligne_id`, `incertain` bool).

**Evaluation** — `evaluation_id`, `run_id`, `annotation_id`, `tolerance_ms`, métriques, `niveau_validation`.

**Rapport** — `rapport_id`, `genere_le`, `runs` (liste), `coupure_corrections` (dernier `correction_id` pris en compte),
`jeu_ventes_id` (nullable), `contient_synthetique` (bool), `niveau_validation`, `sha256` du fichier.

**JeuVentes (V2)** — `jeu_id`, `origine` (`synthetique` | `reelle`), `generateur_version`, `graine`, lignes
(`ticket_id`, `horodatage`, `montant`, `nb_articles`).

**Ecart (V2)** — `ecart_id`, `regle_id`, `intervalle`, valeurs comparées, `statut` (`ouvert` | `explique` | `ecarte`),
`justification`, `rapport_id`.

## 3. Règles de temps

- **R-T1** Un événement observé est daté par son **temps vidéo** `t_ms` (PTS ramené au début du flux).
- **R-T2** `num_image` est conservé mais ne sert jamais seul à calculer un temps.
- **R-T3** L'heure murale affichée = `debut_declare + t_ms`, accompagnée de `source_debut`. Sans début déclaré,
  le rapport affiche le temps vidéo (`hh:mm:ss.mmm` depuis le début).
- **R-T4** L'horloge système n'est jamais utilisée pour dater un événement observé.
- **R-T5** Une correction d'instant porte sur `t_ms` (temps vidéo), jamais sur l'heure murale.
- **R-T6** Les tranches d'agrégation (15 min par défaut) sont alignées sur l'heure murale si elle existe,
  sinon sur le temps vidéo depuis 0.

## 4. Règles d'isolement des runs

- **R-R1** Toute observation, preuve, correction et plage de revue porte un `run_id` non nul.
- **R-R2** Un run n'est visible des indicateurs que s'il est `reussi`.
- **R-R3** Un run `reussi` est immuable ; retraiter crée un nouveau run (`parent_run_id`).
- **R-R4** Toute requête d'indicateur reçoit un ensemble explicite de runs ; aucune requête « toutes observations ».
- **R-R5** Un rapport contient au plus un run par couple (vidéo, scénario) ; sinon il est refusé.
- **R-R6** Le run actif d'un couple (vidéo, scénario) est un choix explicite et journalisé.
- **R-R7** Deux runs se comparent uniquement via l'évaluation (même annotation de référence) ou une vue
  « comparaison » dédiée, jamais en additionnant leurs observations.
- **R-R8** Supprimer un run supprime ses preuves et corrections ; les annotations de référence ne sont pas touchées.

## 5. Règles de revue

- **R-V1** État effectif d'une observation = dernière correction `confirmer` / `rejeter` / `modifier_*` ; sans correction,
  elle est « non revue ».
- **R-V2** Comptage « après revue » = observations non rejetées (modifications appliquées) + ajouts.
- **R-V3** Les observations non revues sont comptées dans le chiffre « après revue » mais signalées : le rapport
  affiche la part revue et les plages revues.
- **R-V4** Une correction est datée et attribuée ; elle n'est jamais supprimée, seulement suivie d'une autre.

## 6. Scénario A : règle de franchissement

Paramètres de configuration (valeurs initiales **[Hypothèse]**, à régler avec E2) :

| Paramètre | Rôle | Valeur initiale |
|---|---|---|
| `classes` | Classes de détection retenues | `personne` |
| `cadence_analyse` | Images analysées par seconde de vidéo | 10 |
| `seuil_confiance` | Confiance minimale d'une détection | 0,4 |
| `point_ancrage` | Point de la boîte qui doit franchir la ligne | bas-centre |
| `longueur_min_piste` | Nombre minimal d'images suivies avant de compter | 5 |
| `delai_anti_rebond_ms` | Délai avant qu'une même piste puisse recompter | 2000 |

Un franchissement est émis quand le point d'ancrage d'une piste passe d'un côté à l'autre de la ligne ;
le sens découle du côté de départ ; `t_ms` est le temps de la première image où le point est du nouveau côté.

Exemple de configuration (format proposé, non figé) :

```yaml
version_schema: 1
scenario: comptage_passages
point_de_vue: entree_principale
lignes:
  - id: porte
    p1: [0.32, 0.78]
    p2: [0.71, 0.80]
    sens_entree: vers_bas
analyse:
  cadence_analyse: 10
  seuil_confiance: 0.4
  point_ancrage: bas_centre
  longueur_min_piste: 5
  delai_anti_rebond_ms: 2000
preuves:
  avant_ms: 3000
  apres_ms: 3000
indicateurs:
  tranche_min: 15
```

## 7. Indicateurs initiaux (scénario A)

Chaque indicateur existe en version **brute** et **après revue**, et cite sa provenance.

| Indicateur | Définition |
|---|---|
| Entrées / sorties par tranche | Nombre de franchissements par sens dans chaque tranche |
| Total entrées / sorties | Somme sur l'intervalle du rapport |
| Tranche de pointe | Tranche au plus grand nombre d'entrées (égalités listées) |
| Solde | Entrées − sorties cumulées ; une valeur négative signale un problème de détection ou de sens |
| Part revue | Observations revues / observations ; et durée des plages revues / durée analysée |

## 8. Mesure des erreurs et niveaux de validation

**Appariement** : un événement détecté et un événement de référence s'apparient s'ils ont le même sens et
`|Δt| ≤ tolerance_ms` (valeur initiale 1000 ms **[Hypothèse]**), en appariement un-à-un. Seules les plages
couvertes par l'annotation sont évaluées.

**Métriques** : précision, rappel, F1 ; erreur de comptage absolue et relative par tranche ; justesse du sens ;
écart temporel médian des paires appariées. Les événements de référence marqués `incertain` sont rapportés à part.

**Niveaux de validation** — tout résultat chiffré affiche son niveau :

| Niveau | Données | Ce que le résultat permet de dire |
|---|---|---|
| N0 | Tests unitaires, données synthétiques | La logique fait ce qui est prévu ; rien sur la performance réelle |
| N1 | Vidéos autorisées ou publiques annotées | Performance sur ces vidéos, dans ces conditions |
| N2 | Vidéos d'un client réel annotées | Performance attendue chez ce client, sur ce point de vue |
| N3 | Pilote en conditions d'exploitation | Performance et utilité en usage réel |

**[Confirmé]** Une simulation n'est jamais présentée comme une validation sur données réelles : un résultat N0
ne s'écrit pas comme un résultat N1, et un résultat N1 ne promet rien pour un client donné.

## 9. Données synthétiques

- **R-S1** L'origine `synthetique` est portée au niveau du jeu de données, obligatoire à l'import.
- **R-S2** Tout indicateur, écart ou rapport qui utilise un élément synthétique hérite de `contient_synthetique = vrai`.
- **R-S3** Un rapport `contient_synthetique` affiche un bandeau en tête et sur chaque page imprimée.
- **R-S4** Le générateur est reproductible (version + graine) et peut injecter des écarts connus pour tester les règles
  de rapprochement : ces tests sont de niveau N0.
- **R-S5** Les vidéos mises en scène (`origine = mise_en_scene`) sont des données réelles mais non représentatives ;
  le rapport le mentionne.

## 10. Rapprochement avec les ventes (V2)

Règle initiale proposée, la plus simple qui soit utile :

- **RC-1** Par tranche, comparer les entrées (après revue) et le nombre de tickets. Signaler un **écart à examiner**
  quand le rapport tickets / entrées sort d'une plage configurée, ou quand il y a des tickets sans aucune entrée
  observée (ou l'inverse) sur une tranche suffisamment longue.

Chaque écart affiche : les valeurs comparées, la règle, les causes non suspectes possibles (passages hors champ,
plusieurs personnes pour un ticket, salariés comptés, erreurs de détection, décalage d'horloge entre caisse et
vidéo), et les preuves des événements de la tranche.

**[Hypothèse]** L'alignement temporel entre caisse et vidéo dépend du début d'enregistrement déclaré ; un décalage
de quelques minutes fausse les écarts par tranche. À traiter avant toute donnée de vente réelle.

## 11. Vocabulaire des textes générés

- Autorisé : « événement observé », « passage détecté », « écart à examiner », « à vérifier », « estimation ».
- Interdit dans tout texte généré automatiquement : « vol », « fraude », « suspect », « coupable », « preuve de vente »,
  « preuve de paiement ».
- Le mot « preuve » désigne uniquement un **élément visuel** (vignette, extrait) attaché à un événement observé.
- Chaque rapport rappelle : « Les chiffres sont des estimations issues de l'analyse vidéo. Une observation vidéo
  ne prouve ni une vente, ni un paiement, ni une fraude. »
