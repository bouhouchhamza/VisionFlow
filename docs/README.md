# Navigation dans la documentation

Point d'entrée en anglais : `README.md` à la racine. Les documents ci-dessous sont en français et gardent leur
historique : un document daté décrit l'état à sa date, il n'est pas réécrit après coup. En cas de doute, le code,
`DECISIONS.md` et `experiments/E2/RESULTATS_S1.md` font foi.

## État au 2026-11-11

| Catégorie | Contenu |
|---|---|
| **Implémenté** (paquet `passages/`) | Détection de personnes YOLOX-S (ONNX, CPU) derrière l'interface `Detector` ; suivi ByteTrack ; franchissement de ligne orienté et règle de maintien ; temps vidéo (`pts`, `rang_cadence_nominale`) ; runs immuables et manifestes ; vidéo annotée ; outil d'annotation ; comparaison à une référence humaine ; examen des paires ; comparateur de runs |
| **Exécuté sur données réelles** | S1 seulement : run `20261103T172241Z-b3b507` et rejouées de non-régression IDENTIQUES. Aucune mesure d'erreur : S1 n'est pas annotée |
| **Proposé, non implémenté** | Multi-classe (étapes 2 à 7), revue humaine, indicateurs et rapports, SQLite, segments de caméra |

## Documents

| Document | Rôle | Statut |
|---|---|---|
| `VISION.md` | Problème, périmètre, principes | Cadrage du 2026-11-03, statut indiqué par section |
| `REQUIREMENTS.md` | Exigences et comparaison des scénarios | Cadrage du 2026-11-03, statut indiqué par exigence |
| `ARCHITECTURE.md` | Architecture cible, options de stack, licences code / poids / données | Cadrage du 2026-11-03 ; son en-tête « Rien n'est encore implémenté » date d'avant le prototype |
| `DATA_AND_RULES.md` | Modèle de données cible, vocabulaire contrôlé | Proposition |
| `IMPLEMENTATION_PLAN.md` | Expériences E0 à E6, phases, portes de décision | Proposition |
| `DECISIONS.md` | Journal des décisions D-001 à D-026 | Référence ; à lire avant toute proposition technique |
| `AUDIT_ARCHITECTURE.md` | Audit du prototype et évolution possible | Proposition |
| `PLAN_DECOUPLAGE_DETECTEUR.md` | Interface `Detector` | Exécuté (D-025) |
| `CONCEPTION_MULTICLASSE.md` | Plan multi-classe en sept étapes | Proposition ; étapes 1 et 2 exécutées, production toujours en mode `person` |
| `ETAPE2_DECODAGE_MULTICLASSE.md` | Décodage multi-classe de YOLOX | Exécutée avec corrections (D-026, Proposition) ; multi-classe non activé |

## Expériences

| Dossier | Contenu | Statut |
|---|---|---|
| `experiments/E0/INVENTAIRE.md` | Sources vidéo, licences lues, échantillon S1 à S4, réserve R1 / R2 | En cours ; R1 et R2 jamais téléchargées ni regardées |
| `experiments/E1/PROTOCOLE.md` | Protocole d'annotation de référence (v2) | Prêt, pas encore appliqué |
| `experiments/E2/RESULTATS_S1.md` | Commandes, run S1, débit mesuré, non-régression | Résultats techniques, aucune mesure d'erreur |
| `experiments/E3/PROTOCOLE.md` | Contrôle du temps vidéo et des extraits | Terminé pour S1 |

Les sorties d'expériences (`experiments/**/out/`), les données, les modèles et les runs restent hors de git.
