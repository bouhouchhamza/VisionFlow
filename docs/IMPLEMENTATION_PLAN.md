# Plan d'implémentation

> Statuts : **[Confirmé]** · **[Proposition]** · **[Hypothèse]** · **[Ouvert]** (voir `VISION.md`).
> Ce plan entier est **[Proposition]**. Aucune tâche n'est commencée. Aucun délai n'est estimé avant la porte G0 :
> la vitesse réelle sera mesurée sur la phase 1.

Dernière mise à jour : 2026-11-03.

## 0. État constaté (2026-11-03)

Constaté par inspection, sans modification :

- `C:\Users\pc\Videos\camera_gestionnaire` était **vide** (0 fichier, 0 dossier) avant la création de `docs/`
  et `AGENTS.md`. Aucun code, aucune vidéo, aucune configuration.
- Aucun dépôt git propre au projet. Le dossier se trouve dans un dépôt git **initialisé à la racine `C:\`**,
  sur la branche `master`, **sans aucun commit**. Ce dépôt voit tout le disque comme non suivi : une commande
  `git add -A` lancée depuis le projet pourrait tenter d'ajouter des fichiers système. Voir D-010.
- Outils présents : Python 3.14.0 (défaut) et 3.11 (via `py`), Node v24.15.0, ffmpeg 8.1.2.
- Matériel : Intel Core i7-1255U, 15,7 Go de RAM, Intel Iris Xe, aucun GPU NVIDIA (`nvidia-smi` absent).
- Aucune dépendance installée pour ce projet.

Mise à jour du 2026-11-03 (après autorisation des préparatifs et d'E0, E1 et E3) :

- Dépôt git indépendant créé dans le projet (branche `main`, aucun commit, aucun remote) ; `.gitignore` en place ;
  le dépôt de `C:\` est inchangé (empreinte vérifiée avant et après). Voir D-010.
- E0 : aucune vidéo propre au projet ; sources publiques vérifiées et échantillon proposé
  (`experiments/E0/INVENTAIRE.md`) ; un clip CAVIAR téléchargé dans `data/` (non versionné).
- E1 : protocole v1 rédigé (`experiments/E1/PROTOCOLE.md`), pas encore appliqué.
- E3 : script de contrôle écrit et exécuté sur 3 mires synthétiques et sur 1 fichier réel ; premiers constats dans
  `experiments/E3/PROTOCOLE.md`. L'échantillon principal n'est pas encore traité.
- Aucune dépendance installée ; aucun code applicatif. Le scénario A et la stack restent des propositions.

Mise à jour du 2026-11-03 (premier prototype mesurable, demandé par le porteur) :

- Scénario A et socle Python retenus **pour le prototype uniquement** (D-005, D-006) ; la vision produit reste
  multisectorielle. Tableau de bord, caisse, WhatsApp et stock exclus de cette étape.
- Extrait de réglage unique : **S1** (MEVA G420). R1 et R2 non téléchargés, non regardés.
- E3 terminé sur S1 : temps reconstruit par rang d'affichage, preuves exactes par vignette ou extrait réencodé
  (`experiments/E3/PROTOCOLE.md` §4.3, D-023).
- E1 : protocole v2, ligne de S1 fixée, outil d'annotation écrit et contrôlé ; **annotation humaine à faire**.
- Environnement `.venv` (Python 3.11.9) et dépendances figées (D-013, D-022) ; paquet `passages/` (prototype, pas du code
  produit) ; résultats et commandes : `experiments/E2/RESULTATS_S1.md`.

## 1. Expériences avant tout engagement

Aucune promesse de **précision**, de **matériel** ou de **délai** n'est faite avant les expériences ci-dessous.
Le code d'expérience vit dans `experiments/` et n'est pas du code produit.

| Engagement | Expériences requises | Condition minimale |
|---|---|---|
| Précision de comptage | E1 + E2 | Mesure N1 sur au moins 3 extraits annotés aux conditions différentes |
| Matériel (poste, GPU, machine client) | E2 (+ E6 si caméra) | Débit mesuré sur le poste actuel, à résolution et cadence fixées |
| Délai de livraison | Phase 1 | Vitesse observée sur T1.1 à T1.8 |
| Scénario B | E4 | Porte G2 |
| Rapprochement ventes réelles | E5 + données réelles | Hors périmètre actuel |

### E0 — Inventaire des vidéos
- **Question** : quelles vidéos autorisées avons-nous, et permettent-elles le scénario A (et B) ?
- **Protocole** : pour chaque fichier, noter la référence d'autorisation, `ffprobe` (codec, durée, cadence, cadence
  variable, résolution, `start_time`), le point de vue, la présence d'un passage et/ou d'une zone de transfert,
  la densité de personnes, l'éclairage. Choisir un petit échantillon aux conditions variées (durée libre),
  et fixer par règle, avant tout réglage, au moins un extrait **réservé à l'évaluation**.
  Sans vidéo propre : sources publiques dont l'URL, la licence, l'attribution et les restrictions sont vérifiables,
  en séparant essais internes, démonstration et redistribution.
- **Résultat** : `experiments/E0/INVENTAIRE.md` + manifeste (empreintes SHA-256).
- **Décision permise** : confirmer A comme premier scénario (D-005) ou le reconsidérer.

### E1 — Protocole et coût d'annotation (scénario A)
- **Question** : peut-on produire une vérité terrain fiable, et à quel coût ?
- **Protocole** : rédiger le protocole (quoi compte comme passage, groupes, poussettes, demi-tours, cas incertains).
  Annoter 2 extraits ; ré-annoter l'un d'eux à au moins un jour d'intervalle.
- **Mesures** : minutes d'annotation par minute de vidéo ; accord entre les deux passes (appariement à 1000 ms).
- **Décision permise** : taille réaliste du jeu d'évaluation ; tolérance temporelle retenue.

### E2 — Détection et suivi sur CPU
- **Question** : un détecteur pré-entraîné + un suivi donnent-ils un comptage exploitable, à un débit acceptable,
  sur ce poste ?
- **Protocole** : 1 à 2 détecteurs candidats à licence vérifiée (D-008), Python 3.11 et test d'installation sous 3.14 ;
  résolution d'inférence et cadence d'analyse fixées et notées ; script jetable de franchissement de ligne.
- **Mesures** : secondes de vidéo traitées par seconde de calcul ; précision, rappel, erreur de comptage par tranche
  sur les extraits annotés ; mémoire maximale.
- **Décision permise** : détecteur, version de Python, stack (D-006, D-008, D-013) ; valeurs initiales des paramètres.
- **Arrêt** : si le rappel reste faible sur un extrait malgré les réglages, documenter la cause (angle, occultation,
  densité) plutôt que forcer ; c'est une limite à afficher, pas un échec caché.

### E3 — Fiabilité du temps et des preuves
- **Question** : les temps des événements et les extraits de preuve tombent-ils au bon instant ?
- **Protocole** : sur un extrait à cadence fixe et, si disponible, un à cadence variable : comparer PTS lus par la
  bibliothèque de décodage, numéro d'image × durée d'image, et image extraite par ffmpeg à un instant donné.
- **Mesures** : écart maximal en ms entre l'instant demandé et l'image obtenue.
- **Décision permise** : méthode de décodage et d'extraction ; précision temporelle annoncée dans le rapport.

### E4 — Faisabilité du scénario B (après la phase 3)
- **Question** : peut-on observer des objets traversant une zone de transfert avec un effort raisonnable ?
- **Protocole** : 1 à 2 vidéos autorisées montrant un comptoir ou un quai ; annoter 50 à 100 transferts ;
  essayer (a) un détecteur générique, (b) la détection d'activité dans la zone sans identifier le produit.
- **Décision permise** : porte G2.

### E5 — Rapprochement sur ventes synthétiques (phase 4)
- **Question** : la règle RC-1 retrouve-t-elle des écarts injectés, et combien d'écarts produit-elle sans injection ?
- **Niveau** : N0. Ne dit rien de la performance sur des ventes réelles.

### E6 — Source caméra (non planifiée)
- Seulement si une caméra et un besoin concret existent : enregistrement en segments, dérive d'horloge, coupures.

## 2. Portes de décision

- **G0 (après E0–E3)** : scénario A confirmé, stack, détecteur, version de Python, tolérance temporelle → `DECISIONS.md`.
- **G1 (après phase 3)** : parcours P1 complet démontré ; erreurs mesurées en N1 ; décider entre phase 4 et E4.
- **G2 (après E4)** : engager B, le réduire à la détection d'activité, ou le reporter.

## 3. Tâches

Format : objectif · dépendances · critères d'acceptation · vérification. Chaque tâche doit tenir en une à deux
sessions de travail ; sinon la redécouper.

### Phase 0 — Préalables

**T0.1 Isoler le dépôt git du projet** — **fait le 2026-11-03** (vérifications dans D-010).
- Dépend de : décision D-010.
- Acceptation : `git rev-parse --show-toplevel` lancé dans le projet renvoie le dossier du projet ; un `.gitignore`
  exclut vidéos, `data/`, `runs/`, environnements virtuels.
- Vérification : la commande ci-dessus ; `git status` ne liste que les fichiers du projet.

**T0.2 Inventaire des vidéos (E0)** — Dépend de : T0.1. **En cours** : sources et échantillon proposés, téléchargements à faire.
- Acceptation : chaque vidéo a une empreinte, une référence d'autorisation (URL, licence, attribution, date de consultation)
  et ses métadonnées ; échantillon varié choisi ; réserve d'évaluation fixée par règle avant tout réglage.
- Vérification : aucune ligne du manifeste sans référence d'autorisation.

**T0.3 Protocole d'annotation et premières annotations (E1)** — Dépend de : T0.2, contrôle de l'outil de lecture par T0.4.
Protocole v2 rédigé, outil d'annotation contrôlé (E3 §4.3) ; annotation de S1 à faire par le porteur.
- Acceptation : protocole v1 écrit ; 2 extraits annotés avec plages couvertes ; coût et accord mesurés.
- Vérification : fichiers d'annotation relisibles ; chiffres d'E1 consignés avec leur méthode.

**T0.4 Expérience temps et preuves (E3)** — Dépend de : T0.2. **Fait pour S1** ; S2 à S4 restent à traiter.
- Acceptation : écarts mesurés sur chaque fichier de l'échantillon (hors réserve), méthode d'extraction retenue
  donnant l'image exacte sur les instants calés, règle de normalisation décidée (D-019), outil de lecture d'E1 contrôlé.
- Vérification : `experiments/E3/out/<fichier>/resume.txt` pour chaque fichier ; synthèse dans `experiments/E3/PROTOCOLE.md`.

**T0.5 Expérience détection et suivi (E2)** — Dépend de : T0.3, licence vérifiée (D-008). **En cours** : pipeline
exécuté sur S1 et débit mesuré ; métriques d'erreur en attente de l'annotation humaine.
- Acceptation : débit et métriques mesurés par extrait, avec configuration exacte.
- Vérification : résultats reproduits une seconde fois avec le même script et la même configuration.

**G0** — Dépend de : T0.2 à T0.5. Mise à jour de `DECISIONS.md`.

### Phase 1 — Socle et analyse de bout en bout (scénario A)

**T1.1 Squelette du projet** — Dépend de : G0.
- Acceptation : structure des modules (`ARCHITECTURE.md` §3), outil de tests, linter, ligne de commande vide.
- Vérification : la suite de tests (vide) et le linter passent.

**T1.2 Schéma de données** — Dépend de : T1.1.
- Acceptation : tables du `DATA_AND_RULES.md` §2 ; `run_id` non nul sur observations, preuves, corrections ;
  corrections en ajout seul.
- Vérification : tests : insertion d'une observation sans `run_id` refusée ; une correction ne modifie pas l'observation.

**T1.3 Enregistrement d'une vidéo** — Dépend de : T1.2.
- Acceptation : EF-01 à EF-03 ; refus sans référence d'autorisation ; doublon détecté par empreinte.
- Vérification : tests sur un court fichier de test généré (mire ffmpeg, niveau N0) ; essai sur un extrait réel.

**T1.4 Configuration validée** — Dépend de : T1.1.
- Acceptation : schéma validé, erreurs lisibles, empreinte stable pour un contenu équivalent.
- Vérification : tests : même contenu reformaté → même empreinte ; paramètre invalide → erreur explicite.

**T1.5 Source d'images fichier** — Dépend de : T1.1, T0.4.
- Acceptation : `FrameSource` fournit (`t_ms` issu du PTS, `num_image`, image) à la cadence d'analyse demandée.
- Vérification : tests sur mire avec horodatage incrusté : `t_ms` lu = temps incrusté, à la précision mesurée en E3.

**T1.6 Cycle de vie d'un run** — Dépend de : T1.2, T1.4.
- Acceptation : création, exécution, finalisation atomique, états `echoue` / `annule` ; manifeste écrit.
- Vérification : test : un run interrompu ne laisse aucune donnée visible des indicateurs ; deux runs sur la même
  vidéo coexistent sans interférence.

**T1.7 Détection et suivi** — Dépend de : T1.5, G0.
- Acceptation : adaptateur du détecteur retenu ; pistes avec identifiant local au run.
- Vérification : sur un extrait annoté, résultats cohérents avec E2 (mêmes paramètres).

**T1.8 Règle de franchissement** — Dépend de : T1.6, T1.7.
- Acceptation : `DATA_AND_RULES.md` §6 ; observations en base avec sens et `t_ms`.
- Vérification : tests unitaires sur pistes synthétiques (franchissement, demi-tour, rebond) ; essai sur extrait réel.

**T1.9 Extraction des preuves** — Dépend de : T1.8, T0.4.
- Acceptation : vignette + extrait par observation, rattachés au run.
- Vérification : pour 10 observations tirées au hasard, la vignette montre bien le franchissement (contrôle visuel noté).

**T1.10 Évaluation** — Dépend de : T1.8, T0.3.
- Acceptation : EF-60, EF-61 ; appariement un-à-un ; métriques et niveau de validation stockés.
- Vérification : tests N0 sur cas construits (paires exactes, hors tolérance, mauvais sens) ; résultat N1 sur les extraits annotés.

### Phase 2 — Revue humaine

**T2.1 Liste des observations d'un run** — Dépend de : T1.8, T1.9.
- Acceptation : interface locale ; filtre par état de revue ; affichage du temps vidéo et de l'heure déclarée.
- Vérification : parcours manuel sur un run réel ; observations affichées = observations en base.

**T2.2 Actions de revue** — Dépend de : T2.1.
- Acceptation : EF-30, EF-31 ; ajout d'un passage manqué depuis le lecteur au temps courant.
- Vérification : tests : rejeter puis confirmer → état final confirmé, historique de deux corrections ; observation brute inchangée.

**T2.3 Plages et couverture de revue** — Dépend de : T2.2.
- Acceptation : EF-32 ; plages revues déclarées et affichées.
- Vérification : test de calcul de la part revue sur un cas construit.

### Phase 3 — Indicateurs et rapport

**T3.1 Indicateurs** — Dépend de : T2.2.
- Acceptation : `DATA_AND_RULES.md` §7, bruts et après revue, avec provenance.
- Vérification : tests N0 sur observations et corrections construites, résultats calculés à la main.

**T3.2 Garde-fous d'isolement** — Dépend de : T3.1.
- Acceptation : R-R4 à R-R6 ; run actif explicite.
- Vérification : test : demander un rapport avec deux runs de la même vidéo → refus explicite.

**T3.3 Rapport HTML et export CSV** — Dépend de : T3.2.
- Acceptation : EF-42, EF-43 ; mention obligatoire (§11 de `DATA_AND_RULES.md`) ; niveau de validation affiché.
- Vérification : rapport généré sur un run réel revu ; contrôle que chaque chiffre renvoie aux événements et chaque
  événement à sa preuve ; recherche automatique des mots interdits dans le HTML produit.

**G1** — Démonstration du parcours P1 complet sur au moins une vidéo autorisée ; métriques N1 consignées.

### Phase 4 — Ventes synthétiques et rapprochement (V2)

**T4.1 Import de ventes** — Dépend de : G1. Acceptation : EF-50, origine obligatoire.
Vérification : import refusé sans origine.

**T4.2 Générateur synthétique** — Dépend de : T4.1. Acceptation : EF-51, R-S4.
Vérification : même graine → même jeu ; écarts injectés listés dans un fichier de contrôle.

**T4.3 Règle RC-1 et écarts** — Dépend de : T4.2, T3.1. Acceptation : EF-52, vocabulaire du §11.
Vérification : E5 (N0) : écarts injectés retrouvés ; nombre d'écarts sans injection consigné.

**T4.4 Bandeau synthétique** — Dépend de : T4.3, T3.3. Acceptation : EF-53, R-S2, R-S3.
Vérification : test : un rapport avec un jeu synthétique sans bandeau fait échouer le test.

### Phase 5 — Scénario B (exploration)

**T5.1 Expérience E4** — Dépend de : G1. Acceptation et vérification : voir E4 ; décision G2 consignée.

### Phase 6 — Source caméra (non engagée)

**T6.1 Adaptateur de segments caméra** — Dépend de : besoin concret, caméra disponible, E6.
Acceptation : un segment fermé est enregistré comme vidéo (`source_type = camera`) et analysé par le même exécuteur.

## 4. Chemin critique

T0.1 → T0.2 → T0.3 → T0.5 → G0 → T1.1 → T1.2 → T1.6 → T1.8 → T1.9 → T2.1 → T2.2 → T3.1 → T3.2 → T3.3 → G1.
T0.4 se fait en parallèle de T0.3 ; T1.4, T1.5 et T1.10 en parallèle de la chaîne principale.
