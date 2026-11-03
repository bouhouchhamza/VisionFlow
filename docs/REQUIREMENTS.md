# Exigences

> Statuts : **[Confirmé]** · **[Proposition]** · **[Hypothèse]** · **[Ouvert]** (voir `VISION.md`).
> Identifiants : `EF-` exigence fonctionnelle, `ENF-` exigence non fonctionnelle, `P-` parcours.
> Priorité : **V1** = premier parcours complet ; **V2** = après validation de V1 ; **Plus tard** = non engagé.

Dernière mise à jour : 2026-11-03.

## 1. Périmètre de la V1

**[Proposition]** La V1 couvre un seul scénario (comptage de passages), une seule source
(fichiers vidéo enregistrés et autorisés), un seul déploiement de démonstration, et le parcours
complet jusqu'au rapport. Le rapprochement avec des ventes synthétiques est la première extension (V2).

## 2. Choix du premier scénario

### 2.1 Les deux candidats

**A. Comptage de passages.** Compter les personnes qui franchissent une ligne virtuelle
(entrée de magasin, porte, allée), avec le sens du passage et l'instant du franchissement.

**B. Produits traversant une zone de transfert.** Observer des objets passant d'un côté à l'autre
d'une zone (comptoir de boulangerie, caisse, quai de chargement), pour les rapprocher ensuite des ventes
ou des mouvements de stock.

### 2.2 Comparaison

| Critère | A. Passages | B. Produits en zone de transfert |
|---|---|---|
| Valeur pour le client | Moyenne : affluence, heures de pointe, taux de transformation si ventes | Élevée : plus proche des ventes et du stock |
| Lien avec les ventes | Indirect (entrées par tranche horaire vs tickets) | Direct (objets remis vs articles vendus) |
| Données disponibles | Vues de porte ou d'allée fréquentes ; détecteurs pré-entraînés pour « personne » | Dépend de vues de comptoir rares ; produits spécifiques à chaque client |
| Modèle nécessaire | Pré-entraîné générique, probablement suffisant **[Hypothèse]** | Probablement entraînement spécifique (petits objets, mains, sacs) **[Hypothèse]** |
| Effort | Faible à moyen | Élevé (annotation, entraînement, réglage par client) |
| Mesure des erreurs | Simple : un clic par passage pour annoter, appariement temporel | Difficile : vérité ambiguë (un sac de 6 croissants = 1 ou 6 ?), occultations |
| Réutilisabilité entre secteurs | Forte (tous les secteurs ont des entrées) | Faible (catalogue propre à chaque client) |
| Risque d'interprétation abusive | Modéré (données personnelles : personnes filmées) | Élevé (tentation de lire un écart comme une fraude) |

### 2.3 Recommandation

**[Proposition]** Commencer par **A**. Ce scénario permet de construire et de valider tout le
parcours (analyse, horodatage, preuves, revue, rapport, retraitement, évaluation) avec un coût
d'annotation faible et une erreur mesurable. Ces briques serviront telles quelles à B.

**[Proposition]** Préparer B par une expérience de faisabilité séparée (E4) avant tout engagement.
Une étape intermédiaire peu coûteuse est possible : détecter une **activité** dans la zone de transfert
(présence de mains ou d'objets, sans identifier le produit) et la rapprocher des tickets par fenêtre
temporelle.

**[Ouvert]** Cette recommandation suppose que les vidéos disponibles contiennent des vues de passage
exploitables. L'inventaire E0 le confirme ou l'infirme ; si seules des vues de comptoir existent,
la décision est à reprendre.

## 3. Parcours P1 : vidéo → rapport

**[Proposition]** Parcours de référence de la V1. Chaque étape a un résultat vérifiable.

| # | Étape | Acteur | Résultat attendu |
|---|---|---|---|
| 1 | Enregistrer une vidéo | Intégrateur | Fiche vidéo : empreinte SHA-256, durée, cadence, résolution, référence d'autorisation, début d'enregistrement déclaré (facultatif) |
| 2 | Configurer la vue | Intégrateur | Ligne de passage et sens « entrée » dessinés sur une image de la vidéo ; configuration validée et versionnée (empreinte) |
| 3 | Lancer une analyse | Intégrateur | Un run identifié, lié à la vidéo, à la configuration, à la version du code et du modèle |
| 4 | Produire des événements horodatés | Système | Liste de franchissements avec temps vidéo (ms), sens, confiance, identifiant de suivi local |
| 5 | Extraire les preuves | Système | Pour chaque événement : une vignette et un court extrait autour de l'instant |
| 6 | Revoir | Réviseur | Chaque événement confirmé, rejeté ou corrigé ; passages manqués ajoutés ; historique conservé |
| 7 | Produire le rapport | Intégrateur ou responsable | Rapport HTML : indicateurs bruts et après revue, part revue, provenance, niveau de validation, limites |

Critère d'acceptation global : sur une vidéo autorisée de quelques minutes, les sept étapes
s'enchaînent sans intervention manuelle hors interface prévue, et le rapport permet de remonter
de chaque chiffre aux événements et de chaque événement à sa preuve.

## 4. Exigences fonctionnelles

### Vidéos et configuration

- **EF-01 (V1)** Enregistrer une vidéo avec empreinte SHA-256, métadonnées techniques (durée,
  cadence nominale,   cadence variable ou non, résolution, codec) et **référence d'autorisation obligatoire**.
  Pour une source publique, cette référence contient l'URL, la licence, l'attribution, la date de consultation et les usages permis.
  Une vidéo sans référence d'autorisation est refusée. Les horodatages sont contrôlés à l'enregistrement : PTS absents,
  non croissants, ou durée annoncée incohérente avec le nombre d'images (constats E3).
- **EF-02 (V1)** Déclarer facultativement un début d'enregistrement en heure murale, avec sa source
  (métadonnée du fichier, nom de fichier, saisie manuelle). Cette heure reste « déclarée ».
- **EF-03 (V1)** Marquer l'origine de chaque vidéo : `reelle_autorisee`, `publique`, `mise_en_scene`.
- **EF-04 (V1)** Définir une vue : géométrie (lignes, zones) en coordonnées normalisées, liée à la vidéo
  ou à un point de vue de caméra.
- **EF-05 (V1)** Configurer une analyse par fichier versionné et validé ; toute configuration a une empreinte.

### Analyse et événements

- **EF-10 (V1)** Lancer une analyse sur une vidéo et une configuration ; elle produit un run unique et immuable.
- **EF-11 (V1)** Détecter les franchissements de ligne avec sens, temps vidéo, numéro d'image, confiance.
- **EF-12 (V1)** Un run échoué ou interrompu n'alimente jamais un indicateur ni un rapport.
- **EF-13 (V1)** Relancer une analyse (autre configuration, autre modèle) crée un nouveau run lié au précédent.
- **EF-14 (V1)** Désigner explicitement le run actif d'une vidéo pour un scénario ; jamais « le plus récent » implicitement.

### Preuves

- **EF-20 (V1)** Pour chaque événement : vignette à l'instant du franchissement et extrait court
  (durées configurables, valeur initiale proposée : 3 s avant, 3 s après). La vignette montre **l'image exacte**
  de l'événement ; la méthode d'extraction est celle validée par E3, pas la recherche rapide par défaut.
- **EF-21 (V1)** Les preuves sont rattachées au run et à l'événement ; elles sont supprimées avec le run.
- **EF-22 (Plus tard)** **[Ouvert]** Floutage des visages dans les preuves.

### Revue humaine

- **EF-30 (V1)** Confirmer, rejeter, corriger (instant, sens) un événement ; ajouter un passage manqué.
- **EF-31 (V1)** Les corrections sont ajoutées, jamais substituées : l'observation brute reste intacte
  et l'historique des décisions est conservé.
- **EF-32 (V1)** Afficher la couverture de revue : nombre et part d'événements revus, intervalles revus.

### Indicateurs et rapports

- **EF-40 (V1)** Calculer les indicateurs en deux versions : **brut** (machine seule) et **après revue**.
- **EF-41 (V1)** Indicateurs initiaux : entrées et sorties par tranche (15 min par défaut), total,
  tranche de pointe, solde entrées − sorties.
- **EF-42 (V1)** Rapport HTML autonome : indicateurs, provenance (run, configuration, version du code
  et du modèle, date de coupure des corrections), niveau de validation, limites, liens vers les preuves.
- **EF-43 (V1)** Export CSV des événements (bruts et corrigés, colonnes distinctes).
- **EF-44 (V1)** Un rapport refuse de combiner deux runs d'une même vidéo pour un même scénario.

### Ventes et rapprochement

- **EF-50 (V2)** Importer des ventes (CSV) avec origine obligatoire : `synthetique` ou `reelle`.
- **EF-51 (V2)** Générer des ventes synthétiques reproductibles (graine, version du générateur).
- **EF-52 (V2)** Règles de rapprochement configurables produisant des « écarts à examiner »
  avec statut (ouvert, expliqué, écarté) et justification.
- **EF-53 (V2)** Tout rapport utilisant des ventes synthétiques porte un bandeau visible
  « Données de ventes synthétiques — ne reflètent aucune activité réelle ».

### Évaluation

- **EF-60 (V1)** Saisir des annotations de référence (vérité terrain) par vidéo, avec intervalles couverts,
  indépendantes de tout run.
- **EF-61 (V1)** Évaluer un run contre les annotations : précision, rappel, erreur de comptage par tranche,
  justesse du sens ; résultat stocké avec le niveau de validation.

## 5. Exigences non fonctionnelles

- **ENF-01 [Confirmé]** Un déploiement par entreprise ; aucune donnée partagée entre déploiements.
- **ENF-02 [Proposition]** Fonctionnement entièrement local et hors ligne ; aucune vidéo envoyée à un service externe.
- **ENF-03 [Hypothèse]** Le poste de développement (i7-1255U, 16 Go, sans GPU NVIDIA) suffit pour analyser
  hors temps réel des vidéos de démonstration. Mesuré par E2 (secondes de vidéo traitées par seconde de calcul).
- **ENF-04 [Proposition]** Traçabilité : tout chiffre affiché remonte à un run, une configuration, une version
  de code et de modèle, et à l'ensemble de corrections pris en compte.
- **ENF-05 [Hypothèse]** Reproductibilité : mêmes entrées, configuration, code et modèle donnent les mêmes
  événements sur la même machine. Des écarts numériques entre machines sont possibles ; à mesurer.
- **ENF-06 [Proposition]** Les vidéos et résultats ne sont jamais versionnés dans git.
- **ENF-07 [Proposition]** Durée de conservation des preuves configurable par déploiement.
- **ENF-08 [Proposition]** L'interface de revue est accessible uniquement en local dans la V1 (pas d'authentification
  multi-utilisateur à construire). **[Ouvert]** pour un déploiement client réel.

## 6. Hors périmètre de la V1

- Flux caméra en direct (architecture prévue, réalisation non engagée).
- Scénario B au-delà de l'expérience de faisabilité E4.
- Identification ou ré-identification de personnes.
- Distinction automatique client / employé.
- Comptes utilisateurs, droits, hébergement distant.
- Conclusions automatiques sur des personnes ; tout vocabulaire de fraude.

## 7. Contraintes réglementaires à clarifier

**[Ouvert]** Les personnes filmées sont des données personnelles. Avant tout déploiement chez un client
réel (hors vidéos de démonstration autorisées) : base légale, information des personnes, durée de conservation,
règles propres à la vidéo sur le lieu de travail. Ce document ne constitue pas un avis juridique ;
une vérification par une personne compétente est nécessaire avant le premier pilote.
