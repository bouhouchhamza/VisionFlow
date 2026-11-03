# Vision produit

> Statuts utilisés dans toute la documentation : **[Confirmé]** fait établi par le porteur du projet ·
> **[Proposition]** recommandation à valider · **[Hypothèse]** à vérifier par une expérience ·
> **[Ouvert]** décision non prise. Le journal des décisions est dans `DECISIONS.md`.

Dernière mise à jour : 2026-11-03.

## 1. Problème

**[Confirmé]** Les responsables d'entreprises physiques (commerces, cafés, boulangeries, entrepôts…)
ont peu de moyens simples pour comprendre ce qui se passe réellement dans leurs locaux :
affluence, rythme d'activité, moments à examiner, cohérence entre l'activité observée et les ventes.

**[Hypothèse]** Ces responsables préfèrent un rapport périodique court, avec des écarts à examiner
et les preuves associées, plutôt qu'un flux vidéo à regarder. À vérifier auprès d'utilisateurs
potentiels dès qu'un premier rapport démontrable existe (voir `IMPLEMENTATION_PLAN.md`).

## 2. Ce que fait le produit

**[Confirmé]** Le produit aide un responsable à comprendre l'activité de son entreprise à travers :

1. des **événements observés** dans la vidéo, horodatés et accompagnés de preuves visuelles ;
2. des **indicateurs** calculés à partir de ces événements ;
3. des **écarts à examiner** (par exemple entre activité observée et ventes) ;
4. des **rapports** lisibles par un non-spécialiste.

**[Confirmé]** L'IA observe et propose ; un humain revoit. Une observation vidéo ne prouve
ni une vente, ni un paiement, ni une fraude. Le produit produit des *signaux à examiner*,
jamais des conclusions sur des personnes.

## 3. Ce que le produit n'est pas

- **[Confirmé]** Pas un outil de preuve de vente, de paiement ou de fraude.
- **[Proposition]** Pas d'identification de personnes : pas de reconnaissance faciale,
  pas de ré-identification d'une personne entre vidéos ou entre journées. Les identifiants de suivi
  sont locaux à une analyse et n'ont aucune signification hors de celle-ci.
- **[Proposition]** Pas un outil de surveillance individuelle des salariés. Les indicateurs portent
  sur des flux et des zones, pas sur des individus.
- **[Proposition]** Pas de vidéo en direct dans la première version : traitement de vidéos enregistrées.

## 4. Utilisateurs

| Rôle | Besoin principal | Statut |
|---|---|---|
| Responsable d'établissement | Lire un rapport, comprendre les écarts, consulter les preuves | [Confirmé] cible |
| Réviseur (souvent le même responsable, ou nous au début) | Confirmer, rejeter ou corriger des événements | [Proposition] |
| Intégrateur (le développeur, seul pour l'instant) | Configurer zones, règles et analyses par client | [Confirmé] |

## 5. Modèle de déploiement

- **[Confirmé]** Chaque entreprise possède un déploiement indépendant et ses propres données.
  Il n'y a pas de base partagée entre clients ; la plateforme n'est donc pas « multi-tenant ».
- **[Confirmé]** Le socle logiciel est réutilisable ; les analyses et règles sont configurées
  selon les besoins du client.
- **[Proposition]** La différence entre deux clients doit tenir dans des fichiers de configuration
  versionnés (zones, règles, indicateurs, vocabulaire du rapport), pas dans des branches de code.

## 6. Point de départ

- **[Confirmé]** On démarre avec des vidéos enregistrées dont l'usage est autorisé.
  Aucune caméra réelle ni entreprise pilote n'est nécessaire pour démarrer.
- **[Confirmé]** Les ventes font partie de la vision. Des données synthétiques, clairement
  identifiées comme telles, serviront à tester les rapprochements.
- **[Proposition]** Premier scénario : comptage de passages (voir la comparaison dans
  `REQUIREMENTS.md` §2). L'observation de produits en zone de transfert vient ensuite,
  après une expérience de faisabilité dédiée.
- **[Proposition]** Une source caméra est prévue dans l'architecture (`ARCHITECTURE.md` §7)
  mais n'est pas réalisée tant qu'aucun besoin concret ni matériel n'existe.

## 7. Principes

1. **Le temps de la vidéo fait foi** pour dater un événement observé. L'heure murale n'est qu'une
   correspondance déclarée (début d'enregistrement), affichée comme telle.
2. **Trois couches séparées** : observations brutes (machine), corrections humaines, indicateurs
   calculés. On ne réécrit jamais une observation brute.
3. **Chaque résultat appartient à une analyse (run) identifiée.** Retraiter une vidéo crée une
   nouvelle analyse ; deux analyses ne se mélangent jamais par accident.
4. **Les erreurs se mesurent.** Toute affirmation de précision cite le jeu de vidéos annotées,
   le niveau de validation (`DATA_AND_RULES.md` §8) et la méthode de mesure.
5. **Une simulation n'est pas une validation.** Les données synthétiques sont marquées à la source
   et ce marquage se propage jusqu'au rapport.
6. **Vocabulaire prudent** : « écart à examiner », « événement observé », jamais « vol » ou
   « fraude » dans un texte généré.
7. **Simplicité adaptée à un développeur seul** : peu de composants, une seule base, une seule
   langue de développement si possible.

## 8. Critères de réussite de la première phase

**[Proposition]** La première phase est réussie lorsque, sur des vidéos autorisées :

- le parcours complet vidéo → configuration → analyse → événements horodatés → preuves →
  revue humaine → rapport fonctionne de bout en bout ;
- l'erreur de comptage est **mesurée** (pas promise) sur au moins trois extraits annotés
  aux conditions différentes ;
- un rapport distingue clairement chiffres bruts, chiffres après revue et part des événements revus ;
- un retraitement avec une autre configuration produit une analyse distincte, comparable à la première,
  sans contamination de l'une par l'autre.

Aucun objectif chiffré de précision, de matériel ou de délai n'est fixé avant les expériences
E1 à E3 décrites dans `IMPLEMENTATION_PLAN.md`.
